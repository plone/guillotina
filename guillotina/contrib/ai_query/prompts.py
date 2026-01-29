from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple


class PromptBuilder:
    @staticmethod
    def build_query_translation_prompt(
        schema_info: Dict,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Tuple[str, str]:
        """
        Build prompt for translating natural language to structured query.
        """
        content_types_desc = PromptBuilder._format_content_types(schema_info)
        field_types_desc = PromptBuilder._format_field_types(schema_info)

        system_prompt = """You are a query translation assistant for Guillotina, a content management system.
Your task is to translate natural language queries into structured JSON queries that match Guillotina's search syntax.

Available content types and their indexed fields:
{content_types}

Field type categories:
{field_types}

Query syntax rules:
- Use `type_name` to filter by content type (e.g., "type_name": "Document")
- Field filters use format: `field_name__operator` (e.g., "title__in": "search term")
- Available operators:
  - `__eq`: exact match
  - `__in`: contains (for text fields)
  - `__not`: does not contain
  - `__gt`, `__gte`, `__lt`, `__lte`: comparisons (for numeric/date fields)
  - `__wildcard`: wildcard pattern matching
- Use `_metadata` to specify which fields to return (comma-separated)
- Use `_size` to limit results (max 50)
- Use `_from` for pagination
- Use `_sort_asc` or `_sort_des` for sorting

Date handling:
- Relative dates: "aquesta setmana" = current week, "aquest mes" = current month
- Convert to ISO format: "YYYY-MM-DDTHH:MM:SSZ"

Return ONLY valid JSON in this format:
{{
    "type_name": "ContentTypeName",
    "field_name__operator": "value",
    "_metadata": "field1,field2",
    "_size": 20
}}

If the query asks for aggregations (sum, count, average), include an "aggregation" field.
This is processed by the AI query layer in memory over search results (not by Guillotina's catalog):
{{
    "type_name": "ContentTypeName",
    "field_name__operator": "value",
    "_metadata": "field1,field2",
    "aggregation": {{
        "operation": "sum|count|average",
        "field": "numeric_field_name",
        "group_by": "optional_grouping_field"
    }}
}}
"""

        user_prompt_template = """Translate the following natural language query to a structured JSON query.
Use the discovered schema to map natural language terms to actual field names.
If the query references previous context, use the conversation history to understand what was asked before.

Query: {query}

Return only the JSON query, no additional text."""

        if conversation_history:
            history_text = "\n".join(
                [
                    f"{msg['role']}: {msg['content']}"
                    for msg in conversation_history[-5:]
                ]
            )
            user_prompt_template = f"""Previous conversation:
{history_text}

{user_prompt_template}"""

        system_prompt_formatted = system_prompt.format(
            content_types=content_types_desc,
            field_types=field_types_desc,
        )

        return system_prompt_formatted, user_prompt_template

    @staticmethod
    def build_response_generation_prompt(
        query: str,
        results: Dict,
        schema_info: Dict,
        conversation_history: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """
        Build messages for generating natural language response from results.
        """
        system_prompt = """You are a helpful assistant that answers questions about data in Guillotina.
You receive query results and must provide a clear, natural language response in the same language as the query.

Guidelines:
- Be concise but informative
- Use the actual field names and values from the results
- If aggregations were performed, explain the calculations
- If no results found, explain why
- Maintain conversation context if provided
- Use the same language as the user's query (Catalan, Spanish, English, etc.)
"""

        results_summary = PromptBuilder._format_results(results)

        user_content = f"""Query: {query}

Results:
{results_summary}

Provide a natural language answer based on these results."""

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            for msg in conversation_history[-3:]:
                messages.append(msg)

        messages.append({"role": "user", "content": user_content})

        return messages

    @staticmethod
    def _format_content_types(schema_info: Dict) -> str:
        """Format content types and fields for prompt."""
        lines = []
        for type_name, fields in schema_info.get("content_types", {}).items():
            field_list = ", ".join([f"{k} ({v})" for k, v in fields.items()])
            lines.append(f"- {type_name}: {field_list}")
        return "\n".join(lines) if lines else "No content types found"

    @staticmethod
    def _format_field_types(schema_info: Dict) -> str:
        """Format field type categories for prompt."""
        field_types = schema_info.get("field_types", {})
        lines = []
        for category, fields in field_types.items():
            if fields:
                lines.append(f"- {category}: {', '.join(fields[:10])}")
        return "\n".join(lines) if lines else "No field types found"

    @staticmethod
    def _format_results(results: Dict) -> str:
        """Format query results for response generation."""
        if "items" not in results:
            return "No results found"

        items = results.get("items", [])
        total = results.get("items_total", len(items))

        if total == 0:
            return "No results found matching the query."

        if total <= 5:
            items_text = "\n".join([f"- {item}" for item in items])
            return f"Found {total} result(s):\n{items_text}"
        else:
            sample = "\n".join([f"- {item}" for item in items[:5]])
            return f"Found {total} result(s). Showing first 5:\n{sample}\n... and {total - 5} more"
