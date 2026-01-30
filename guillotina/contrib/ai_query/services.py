from guillotina import configure
from guillotina._settings import app_settings
from guillotina.api.service import Service
from guillotina.component import query_utility
from guillotina.contrib.ai_query.handler import AIQueryHandler
from guillotina.contrib.ai_query.llm_logger import LLMInteractionLogger
from guillotina.contrib.ai_query.result_processor import ResultProcessor
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPServiceUnavailable
from guillotina.response import Response
from typing import Dict
from typing import List
from typing import Optional
from uuid import uuid4

import json
import logging
import time


logger = logging.getLogger("guillotina")


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.ai_query.Query",
    name="@ai-query",
    summary="Query data using natural language",
    requestBody={
        "required": True,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language query"},
                        "response_format": {
                            "type": "string",
                            "enum": ["natural", "structured"],
                            "default": "natural",
                        },
                        "conversation_id": {
                            "type": "string",
                            "description": "Optional conversation ID for context",
                        },
                        "context": {
                            "type": "array",
                            "description": "Previous conversation messages",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "role": {"type": "string", "enum": ["user", "assistant"]},
                                    "content": {"type": "string"},
                                },
                            },
                        },
                        "stream": {
                            "type": "boolean",
                            "description": "Stream the answer as Server-Sent Events",
                            "default": False,
                        },
                    },
                    "required": ["query"],
                }
            }
        },
    },
    responses={
        "200": {
            "description": "Query results",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "answer": {"type": "string"},
                            "data": {"type": "object"},
                            "conversation_id": {"type": "string"},
                        },
                    }
                }
            },
        }
    },
)
class AIQueryService(Service):
    async def __call__(self):
        data = await self.get_data()

        query_text = data.get("query")
        if not query_text:
            raise HTTPPreconditionFailed(content={"reason": "query is required"})

        response_format = data.get("response_format", "natural")
        stream = data.get("stream", False)
        conversation_id = data.get("conversation_id") or str(uuid4())
        context = data.get("context", [])

        settings = app_settings.get("ai_query", {})
        if not settings.get("enabled", True):
            raise HTTPServiceUnavailable(content={"reason": "AI query is not enabled"})

        request_id = str(uuid4())
        interaction_logger = None
        if settings.get("log_llm_interactions") and settings.get("log_llm_dir"):
            interaction_logger = LLMInteractionLogger(
                request_id=request_id,
                enabled=True,
                log_dir=settings.get("log_llm_dir"),
            )
            interaction_logger.log_request_start(query_text)

        ai_query_handler = AIQueryHandler()

        try:
            schema_info = await ai_query_handler.get_schema_info(self.context)

            conversation_history = self._prepare_conversation_history(context, settings)

            translated_query = await ai_query_handler.translate_query(
                query_text,
                self.context,
                schema_info,
                conversation_history,
                interaction_logger=interaction_logger,
            )

            if ai_query_handler._is_step_response(translated_query):
                processed_results, _ = await self._run_multi_step(
                    ai_query_handler,
                    query_text,
                    schema_info,
                    conversation_history,
                    translated_query,
                    settings,
                    interaction_logger=interaction_logger,
                )
            else:
                t0 = time.perf_counter()
                search_results = await self._execute_query(translated_query)
                duration = time.perf_counter() - t0
                if interaction_logger:
                    interaction_logger.log_catalog_search(
                        translated_query, search_results, duration_seconds=duration
                    )
                if (
                    search_results.get("items_total", 0) == 0
                    and settings.get("retry_on_empty", True)
                    and not translated_query.get("aggregation")
                ):
                    retry_response = await ai_query_handler.translate_retry_on_empty(
                        query_text,
                        self.context,
                        schema_info,
                        translated_query,
                        conversation_history,
                        interaction_logger=interaction_logger,
                    )
                    if ai_query_handler._is_step_response(retry_response):
                        alt_query = dict(retry_response["query"])
                        t0 = time.perf_counter()
                        search_results = await self._execute_query(alt_query)
                        duration = time.perf_counter() - t0
                        if interaction_logger:
                            interaction_logger.log_catalog_search(
                                alt_query,
                                search_results,
                                duration_seconds=duration,
                            )
                        translated_query = alt_query
                aggregation_config = translated_query.get("aggregation")
                if aggregation_config:
                    processed_results = ResultProcessor.process_results(search_results, aggregation_config)
                else:
                    processed_results = search_results

            if response_format == "natural":
                if stream:
                    return await self._stream_response(
                        ai_query_handler,
                        query_text,
                        processed_results,
                        schema_info,
                        conversation_history,
                        conversation_id,
                        interaction_logger=interaction_logger,
                    )
                answer = await ai_query_handler.generate_response(
                    query_text,
                    processed_results,
                    schema_info,
                    conversation_history,
                    interaction_logger=interaction_logger,
                )
                return {
                    "answer": answer,
                    "data": processed_results,
                    "conversation_id": conversation_id,
                }
            else:
                return processed_results

        except ValueError as e:
            logger.error("Query validation error: %s", e, exc_info=True)
            raise HTTPPreconditionFailed(content={"reason": str(e)})
        except Exception as e:
            logger.error("AI query error: %s", e, exc_info=True)
            raise HTTPServiceUnavailable(content={"reason": f"Query processing failed: {str(e)}"})
        finally:
            if interaction_logger:
                interaction_logger.log_request_end()
                interaction_logger.close()

    async def _execute_query(self, query: dict) -> dict:
        """Execute the translated query using catalog utility."""
        catalog = query_utility(ICatalogUtility)
        if catalog is None:
            raise HTTPServiceUnavailable(content={"reason": "Catalog utility not available"})

        aggregation = query.pop("aggregation", None)
        collect_all = query.pop("_collect_all", False)

        try:
            if collect_all and aggregation:
                page_size = int(app_settings.get("catalog_max_results", 50))
                all_items: List[Dict] = []
                offset = 0
                total_known = None
                while True:
                    q = {**query, "_from": offset, "_size": page_size}
                    batch = await catalog.search(self.context, q)
                    items = batch.get("items", [])
                    all_items.extend(items)
                    total_known = batch.get("items_total")
                    if total_known is not None and len(all_items) >= total_known:
                        break
                    if len(items) < page_size:
                        break
                    offset += len(items)
                if aggregation:
                    query["aggregation"] = aggregation
                return {"items": all_items, "items_total": len(all_items)}
            results = await catalog.search(self.context, query)
            if aggregation:
                query["aggregation"] = aggregation
            return results
        except Exception as e:
            logger.error(f"Query execution error: {e}", exc_info=True)
            raise ValueError(f"Failed to execute query: {str(e)}")

    async def _stream_response(
        self,
        ai_query_handler,
        query_text: str,
        processed_results: dict,
        schema_info: dict,
        conversation_history: Optional[List[Dict]],
        conversation_id: str,
        interaction_logger: Optional[LLMInteractionLogger] = None,
    ) -> Response:
        """Return SSE stream: event chunk with data, then event done with payload."""
        resp = Response(status=200)
        resp.content_type = "text/event-stream"
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Accel-Buffering"] = "no"
        await resp.prepare(self.request)

        try:
            async for chunk in ai_query_handler.generate_response_stream(
                query_text,
                processed_results,
                schema_info,
                conversation_history,
                interaction_logger=interaction_logger,
            ):
                sse_lines = "\n".join(f"data: {line}" for line in chunk.split("\n"))
                await resp.write(f"{sse_lines}\n\n".encode("utf-8"), eof=False)
            done = json.dumps(
                {
                    "data": processed_results,
                    "conversation_id": conversation_id,
                }
            ).decode("utf-8")
            await resp.write(f"event: done\ndata: {done}\n\n".encode("utf-8"), eof=False)
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            err = json.dumps({"error": "Stream error."}).decode("utf-8")
            await resp.write(f"event: error\ndata: {err}\n\n".encode("utf-8"), eof=False)
        await resp.write(b"", eof=True)
        return resp

    async def _run_multi_step(
        self,
        ai_query_handler,
        query_text: str,
        schema_info: dict,
        conversation_history: Optional[List[Dict]],
        first_step_response: dict,
        settings: dict,
        interaction_logger: Optional[LLMInteractionLogger] = None,
    ) -> tuple:
        """
        Execute multi-step agent loop: run first query, then repeatedly
        translate_next_step and execute until _action answer or max_steps.
        Returns (processed_results_for_final_answer, step_results).
        """
        max_steps = int(settings.get("max_steps", 5))
        step_results: List[Dict] = []
        current_query = dict(first_step_response["query"])
        last_processed: Optional[Dict] = None

        for step_index in range(1, max_steps + 1):
            t0 = time.perf_counter()
            search_results = await self._execute_query(current_query)
            duration = time.perf_counter() - t0
            step_results.append({"query": dict(current_query), "result": search_results})
            if interaction_logger:
                interaction_logger.log_catalog_search(
                    dict(current_query),
                    search_results,
                    step_index=step_index,
                    duration_seconds=duration,
                )
            agg = current_query.get("aggregation")
            last_processed = ResultProcessor.process_results(search_results, agg) if agg else search_results

            next_response = await ai_query_handler.translate_next_step(
                query_text,
                self.context,
                schema_info,
                step_results,
                conversation_history,
                interaction_logger=interaction_logger,
                step_index=step_index,
            )
            if next_response.get("_action") == "answer":
                return (last_processed, step_results)
            if ai_query_handler._is_step_response(next_response):
                current_query = dict(next_response["query"])
                continue
            break

        return (last_processed or {}, step_results)

    def _prepare_conversation_history(self, context: List[Dict], settings: dict) -> Optional[List[Dict]]:
        """Prepare conversation history from context."""
        if not settings.get("enable_conversation", True):
            return None

        if not context:
            return None

        max_history = settings.get("max_conversation_history", 10)
        return context[-max_history:] if len(context) > max_history else context
