from guillotina import app_settings
from guillotina.contrib.ai_query.llm_logger import LLMInteractionLogger
from guillotina.contrib.ai_query.prompts import PromptBuilder
from guillotina.contrib.ai_query.providers import LLMProvider
from guillotina.contrib.ai_query.schema_analyzer import SchemaAnalyzer
from guillotina.interfaces import IResource
from typing import AsyncGenerator
from typing import Dict
from typing import List
from typing import Optional

import json
import logging
import time


logger = logging.getLogger("guillotina")


def _looks_truncated(text: str) -> bool:
    """Heuristic: response likely cut off before completing JSON."""
    if not text or len(text) < 10:
        return True
    stripped = text.strip()
    if stripped.endswith(",") or stripped.endswith(":") or stripped.endswith('"'):
        return True
    open_braces = stripped.count("{") - stripped.count("}")
    open_brackets = stripped.count("[") - stripped.count("]")
    return open_braces > 0 or open_brackets > 0


class AIQueryHandler:
    """
    Handler for translating natural language queries and generating responses.
    """

    def __init__(self):
        self.provider = LLMProvider()

    @property
    def settings(self):
        return app_settings.get("ai_query", {})

    async def get_schema_info(self, context: IResource) -> dict:
        """Get schema information for the context."""
        analyzer = SchemaAnalyzer(context)
        return await analyzer.get_schema_info()

    async def translate_query(
        self,
        natural_language: str,
        context: IResource,
        schema_info: dict,
        conversation_history: Optional[List[Dict]] = None,
        interaction_logger: Optional[LLMInteractionLogger] = None,
    ) -> dict:
        """
        Translate natural language query to structured query format.
        """
        if not self.provider.is_enabled():
            raise ValueError("AI query is not enabled")

        system_prompt, user_prompt_template = PromptBuilder.build_query_translation_prompt(
            schema_info, conversation_history
        )
        user_prompt = user_prompt_template.format(query=natural_language)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        temperature = self.settings.get("temperature", 0.1)
        max_tokens = self.settings.get("query_translation_max_tokens", self.settings.get("max_tokens", 1024))
        timeout = self.settings.get("timeout", 30)

        try:
            t0 = time.perf_counter()
            response_text = await self.provider.completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            duration = time.perf_counter() - t0
            response = self._parse_query_response(response_text)
            if interaction_logger:
                interaction_logger.log_translate_query(
                    messages, response_text, response, duration_seconds=duration
                )
            if self._is_step_response(response):
                self._validate_query(response["query"], schema_info)
                return response
            self._validate_query(response, schema_info)
            return response
        except Exception as e:
            duration = time.perf_counter() - t0
            if interaction_logger:
                interaction_logger.log_llm_error(
                    "translate_query", e, messages=messages, duration_seconds=duration
                )
            logger.error("Query translation failed: %s", e, exc_info=True)
            raise

    async def translate_next_step(
        self,
        natural_language: str,
        context: IResource,
        schema_info: dict,
        step_results: List[Dict],
        conversation_history: Optional[List[Dict]] = None,
        interaction_logger: Optional[LLMInteractionLogger] = None,
        step_index: int = 1,
    ) -> dict:
        """
        Given previous step results, return either the next query to run
        (with _next: true) or _action: answer. Used in multi-step agent loop.
        """
        if not self.provider.is_enabled():
            raise ValueError("AI query is not enabled")

        system_prompt, user_prompt_template = PromptBuilder.build_next_step_prompt(
            schema_info, step_results, conversation_history
        )
        step_results_desc = PromptBuilder.format_step_results(step_results)
        user_prompt = user_prompt_template.format(query=natural_language, step_results=step_results_desc)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        temperature = self.settings.get("temperature", 0.1)
        max_tokens = self.settings.get("query_translation_max_tokens", self.settings.get("max_tokens", 1024))
        timeout = self.settings.get("timeout", 30)

        try:
            t0 = time.perf_counter()
            response_text = await self.provider.completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            duration = time.perf_counter() - t0
            response = self._parse_query_response(response_text)
            if interaction_logger:
                interaction_logger.log_translate_next_step(
                    step_index, messages, response_text, response, duration_seconds=duration
                )
            if response.get("_action") == "answer":
                return response
            if self._is_step_response(response):
                self._validate_query(response["query"], schema_info)
                return response
            raise ValueError("Expected next-step query or _action answer from LLM")
        except Exception as e:
            duration = time.perf_counter() - t0
            if interaction_logger:
                interaction_logger.log_llm_error(
                    f"translate_next_step (step {step_index})",
                    e,
                    messages=messages,
                    duration_seconds=duration,
                )
            logger.error("Next step translation failed: %s", e, exc_info=True)
            raise

    def _is_step_response(self, response: dict) -> bool:
        """True if response is a step (has query and _next)."""
        return isinstance(response.get("query"), dict) and response.get("_next") is True

    async def translate_retry_on_empty(
        self,
        natural_language: str,
        context: IResource,
        schema_info: dict,
        last_query: dict,
        conversation_history: Optional[List[Dict]] = None,
        interaction_logger: Optional[LLMInteractionLogger] = None,
    ) -> dict:
        """
        When the last query returned 0 results, ask the LLM for one alternative
        query or to confirm no results. Returns {"query": {...}, "_next": true}
        or {"_action": "answer"}.
        """
        if not self.provider.is_enabled():
            raise ValueError("AI query is not enabled")

        t0 = time.perf_counter()
        system_prompt, user_prompt_template = PromptBuilder.build_retry_on_empty_prompt(
            schema_info, natural_language, last_query, conversation_history
        )
        user_prompt = user_prompt_template.format(
            user_query=natural_language,
            last_query=json.dumps(last_query, indent=2, default=str),
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        temperature = self.settings.get("temperature", 0.1)
        max_tokens = self.settings.get("query_translation_max_tokens", self.settings.get("max_tokens", 1024))
        timeout = self.settings.get("timeout", 30)

        try:
            response_text = await self.provider.completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            duration = time.perf_counter() - t0
            response = self._parse_query_response(response_text)
            if interaction_logger:
                interaction_logger.log_retry_on_empty(
                    messages, response_text, response, duration_seconds=duration
                )
            if response.get("_action") == "answer":
                return response
            if self._is_step_response(response):
                self._validate_query(response["query"], schema_info)
                return response
            raise ValueError("Expected alternative query or _action answer from LLM")
        except Exception as e:
            duration = time.perf_counter() - t0
            if interaction_logger:
                interaction_logger.log_llm_error(
                    "retry_on_empty", e, messages=messages, duration_seconds=duration
                )
            logger.error("Retry on empty failed: %s", e, exc_info=True)
            raise

    async def generate_response(
        self,
        query: str,
        results: dict,
        schema_info: dict,
        conversation_history: Optional[List[Dict]] = None,
        interaction_logger: Optional[LLMInteractionLogger] = None,
    ) -> str:
        """
        Generate natural language response from query results.
        """
        if not self.provider.is_enabled():
            return "AI query is not enabled"

        messages = PromptBuilder.build_response_generation_prompt(
            query, results, schema_info, conversation_history
        )

        temperature = self.settings.get("response_temperature", 0.7)
        max_tokens = self.settings.get("max_tokens", 500)
        timeout = self.settings.get("timeout", 30)

        try:
            t0 = time.perf_counter()
            response = await self.provider.completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            duration = time.perf_counter() - t0
            if interaction_logger:
                interaction_logger.log_generate_response(messages, response, duration_seconds=duration)
            return response
        except Exception as e:
            duration = time.perf_counter() - t0
            if interaction_logger:
                interaction_logger.log_llm_error(
                    "generate_response", e, messages=messages, duration_seconds=duration
                )
            logger.error("Response generation failed: %s", e, exc_info=True)
            return f"Error generating response: {str(e)}"

    async def generate_response_stream(
        self,
        query: str,
        results: dict,
        schema_info: dict,
        conversation_history: Optional[List[Dict]] = None,
        interaction_logger: Optional[LLMInteractionLogger] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate natural language response from query results; yields content chunks.
        """
        if not self.provider.is_enabled():
            yield "AI query is not enabled"
            return

        messages = PromptBuilder.build_response_generation_prompt(
            query, results, schema_info, conversation_history
        )

        temperature = self.settings.get("response_temperature", 0.7)
        max_tokens = self.settings.get("max_tokens", 500)
        timeout = self.settings.get("timeout", 30)

        try:
            t0 = time.perf_counter()
            chunks = []
            async for chunk in self.provider.completion_stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            ):
                chunks.append(chunk)
                yield chunk
            duration = time.perf_counter() - t0
            if interaction_logger and chunks:
                interaction_logger.log_generate_response(messages, "".join(chunks), duration_seconds=duration)
        except Exception as e:
            duration = time.perf_counter() - t0
            if interaction_logger:
                interaction_logger.log_llm_error(
                    "generate_response_stream", e, messages=messages, duration_seconds=duration
                )
            logger.error("Response stream failed: %s", e, exc_info=True)
            yield f"Error generating response: {str(e)}"

    def _parse_query_response(self, response_text: str) -> dict:
        """Parse LLM response text into query dict."""
        response_text = response_text.strip()

        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse query response: {response_text}", exc_info=True)
            if _looks_truncated(response_text):
                raise ValueError(
                    "LLM response was truncated (incomplete JSON). "
                    "Increase ai_query.query_translation_max_tokens in settings."
                ) from e
            raise ValueError(f"Invalid query format: {e}") from e

    def _validate_query(self, query: dict, schema_info: dict):
        """Validate translated query against discovered schema."""
        if not isinstance(query, dict):
            raise ValueError("Query must be a dictionary")

        type_name = query.get("type_name")
        if type_name:
            if type_name not in schema_info.get("content_types", {}):
                raise ValueError(f"Unknown content type: {type_name}")

        content_types = schema_info.get("content_types", {})
        for key, value in query.items():
            if key.startswith("_") or key == "type_name" or key == "aggregation":
                continue

            field_name = key.split("__")[0]
            if type_name and type_name in content_types:
                if field_name not in content_types[type_name]:
                    logger.warning(f"Field {field_name} not found in {type_name}, but allowing query")
