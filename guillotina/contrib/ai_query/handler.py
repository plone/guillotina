from guillotina import app_settings
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
        max_tokens = self.settings.get(
            "query_translation_max_tokens", self.settings.get("max_tokens", 1024)
        )
        timeout = self.settings.get("timeout", 30)

        try:
            response_text = await self.provider.completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            query = self._parse_query_response(response_text)
            self._validate_query(query, schema_info)

            return query
        except Exception as e:
            logger.error(f"Query translation failed: {e}", exc_info=True)
            raise

    async def generate_response(
        self,
        query: str,
        results: dict,
        schema_info: dict,
        conversation_history: Optional[List[Dict]] = None,
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
            response = await self.provider.completion(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return response
        except Exception as e:
            logger.error(f"Response generation failed: {e}", exc_info=True)
            return f"Error generating response: {str(e)}"

    async def generate_response_stream(
        self,
        query: str,
        results: dict,
        schema_info: dict,
        conversation_history: Optional[List[Dict]] = None,
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
            async for chunk in self.provider.completion_stream(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            ):
                yield chunk
        except Exception as e:
            logger.error(f"Response stream failed: {e}", exc_info=True)
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
                    logger.warning(
                        f"Field {field_name} not found in {type_name}, but allowing query"
                    )
