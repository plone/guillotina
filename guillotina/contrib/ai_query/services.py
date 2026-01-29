from guillotina import configure
from guillotina._settings import app_settings
from guillotina.api.service import Service
from guillotina.component import query_utility
from guillotina.contrib.ai_query.result_processor import ResultProcessor
from guillotina.contrib.ai_query.handler import AIQueryHandler
from guillotina.interfaces import ICatalogUtility
from guillotina.interfaces import IResource
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPServiceUnavailable
from guillotina.response import Response
from typing import Dict
from typing import List
from typing import Optional
from uuid import uuid4

import logging
import orjson


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

        ai_query_handler = AIQueryHandler()

        try:
            schema_info = await ai_query_handler.get_schema_info(self.context)

            conversation_history = self._prepare_conversation_history(context, settings)

            translated_query = await ai_query_handler.translate_query(
                query_text, self.context, schema_info, conversation_history
            )
            import pdb; pdb.set_trace()
            search_results = await self._execute_query(translated_query)

            aggregation_config = translated_query.get("aggregation")
            if aggregation_config:
                processed_results = ResultProcessor.process_results(
                    search_results, aggregation_config
                )
            else:
                processed_results = search_results
            import pdb; pdb.set_trace()
            if response_format == "natural":
                if stream:
                    return await self._stream_response(
                        ai_query_handler,
                        query_text,
                        processed_results,
                        schema_info,
                        conversation_history,
                        conversation_id,
                    )
                answer = await ai_query_handler.generate_response(
                    query_text, processed_results, schema_info, conversation_history
                )
                return {
                    "answer": answer,
                    "data": processed_results,
                    "conversation_id": conversation_id,
                }
            else:
                return processed_results

        except ValueError as e:
            logger.error(f"Query validation error: {e}", exc_info=True)
            raise HTTPPreconditionFailed(content={"reason": str(e)})
        except Exception as e:
            logger.error(f"AI query error: {e}", exc_info=True)
            raise HTTPServiceUnavailable(
                content={"reason": f"Query processing failed: {str(e)}"}
            )

    async def _execute_query(self, query: dict) -> dict:
        """Execute the translated query using catalog utility."""
        catalog = query_utility(ICatalogUtility)
        if catalog is None:
            raise HTTPServiceUnavailable(content={"reason": "Catalog utility not available"})

        aggregation = query.pop("aggregation", None)

        try:
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
    ) -> Response:
        """Return SSE stream: event chunk with data, then event done with payload."""
        resp = Response(status=200)
        resp.content_type = "text/event-stream"
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["X-Accel-Buffering"] = "no"
        await resp.prepare(self.request)

        try:
            async for chunk in ai_query_handler.generate_response_stream(
                query_text, processed_results, schema_info, conversation_history
            ):
                sse_lines = "\n".join(f"data: {line}" for line in chunk.split("\n"))
                await resp.write(f"{sse_lines}\n\n".encode("utf-8"), eof=False)
            done = orjson.dumps(
                {
                    "data": processed_results,
                    "conversation_id": conversation_id,
                }
            ).decode("utf-8")
            await resp.write(f"event: done\ndata: {done}\n\n".encode("utf-8"), eof=False)
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            err = orjson.dumps({"error": "Stream error."}).decode("utf-8")
            await resp.write(f"event: error\ndata: {err}\n\n".encode("utf-8"), eof=False)
        await resp.write(b"", eof=True)
        return resp

    def _prepare_conversation_history(
        self, context: List[Dict], settings: dict
    ) -> Optional[List[Dict]]:
        """Prepare conversation history from context."""
        if not settings.get("enable_conversation", True):
            return None

        if not context:
            return None

        max_history = settings.get("max_conversation_history", 10)
        return context[-max_history:] if len(context) > max_history else context
