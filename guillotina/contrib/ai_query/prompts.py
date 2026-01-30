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
        request_context_desc = PromptBuilder._format_request_context(schema_info)

        system_prompt = """You are a query translation assistant for Guillotina, a content management system.
Your task is to translate natural language queries into structured JSON queries that match Guillotina's search syntax.

Current request context (the resource where the query is being run):
{request_context}

Use this context when the user refers to "this" container, "here", or the current resource: set `path__starts` to request_context.path or `id__eq` to request_context.id so the search is scoped to the current context.
When the user refers to something by name or slug, resolve it via the schema: use the appropriate content type and filter by `title__in` or `title__eq` for names/titles, or `id__eq` for ids.

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
  - `path__starts`: filter by path prefix (use request_context.path for current container)
- Use `_metadata` to specify which fields to return (comma-separated)
- Use `_size` to limit results (max 50)
- Use `_from` for pagination
- Use `_sort_asc` or `_sort_des` for sorting
- For aggregations (sum, count, average) that must consider ALL matching items, set `_collect_all`: true so the system will paginate and aggregate over the full result set.

Date handling:
- Relative dates: convert to current week/month and then to ISO format "YYYY-MM-DDTHH:MM:SSZ"

Return ONLY valid JSON. Either a single query object, or a multi-step plan:

Single query (use when one search is enough):
{{
    "type_name": "ContentTypeName",
    "field_name__operator": "value",
    "_metadata": "field1,field2",
    "_size": 20
}}

Multi-step (use when you must first resolve a resource by name/title, then run another query using its path or id):
{{
    "query": {{ "type_name": "...", "title__in": "name to resolve", "_size": 1, "_metadata": "path,id,title" }},
    "_next": true
}}
The system will run the query, then ask you for the next step with the result. You will then return either the next {{ "query": {{ ... }}, "_next": true }} (use path or id from the first item of the previous result to set path__starts or a filter) or {{ "_action": "answer" }} when you have enough to answer.

If the query asks for aggregations (sum, count, average), include an "aggregation" field and set "_collect_all": true so all matching items are fetched before aggregating:
{{
    "type_name": "ContentTypeName",
    "field_name__operator": "value",
    "_metadata": "field1,field2",
    "_collect_all": true,
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
                [f"{msg['role']}: {msg['content']}" for msg in conversation_history[-5:]]
            )
            user_prompt_template = f"""Previous conversation:
{history_text}

{user_prompt_template}"""

        system_prompt_formatted = system_prompt.format(
            request_context=request_context_desc,
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
    def build_next_step_prompt(
        schema_info: Dict,
        step_results: List[Dict],
        conversation_history: Optional[List[Dict]] = None,
    ) -> tuple:
        """
        Build prompt for the next step in a multi-step plan: given previous
        step results, return either the next query or _action answer.
        """
        content_types_desc = PromptBuilder._format_content_types(schema_info)

        system_prompt = """You are the next-step planner for a multi-step query in Guillotina.
The user asked a question that required running one or more searches. Previous step(s) have been run; below are their results.

Available content types and indexed fields:
{content_types}

Your response must be exactly one of:

1) Next query to run (use path, id, or other fields from the previous step result to scope the search):
{{ "query": {{ "type_name": "...", "path__starts": "<path from previous result>", ... }}, "_next": true }}

2) Enough data to answer (no more queries):
{{ "_action": "answer" }}

Use the first item from the previous step result (e.g. its "path" or "id") to set path__starts or filters for the next query. Return only valid JSON."""

        user_prompt_template = """User question: {query}

Previous step(s) results:
{step_results}

Return either the next query JSON with "_next": true, or {{ "_action": "answer" }}. No other text."""

        if conversation_history:
            history_text = "\n".join(f"{m['role']}: {m['content']}" for m in conversation_history[-3:])
            user_prompt_template = f"Previous conversation:\n{history_text}\n\n{user_prompt_template}"

        system_formatted = system_prompt.format(content_types=content_types_desc)
        return system_formatted, user_prompt_template

    @staticmethod
    def build_retry_on_empty_prompt(
        schema_info: Dict,
        user_query: str,
        last_query: Dict,
        conversation_history: Optional[List[Dict]] = None,
    ) -> Tuple[str, str]:
        """
        Build prompt for retry when the last query returned 0 results: suggest
        one alternative query or confirm no results.
        """
        content_types_desc = PromptBuilder._format_content_types(schema_info)
        request_context_desc = PromptBuilder._format_request_context(schema_info)

        system_prompt = """You are a query assistant for Guillotina. The last catalog query returned zero results.
Either the data does not exist, or the query was too strict (wrong type, field, or operator).

Current request context:
{request_context}

Available content types and indexed fields:
{content_types}

You must return exactly one of:

1) One alternative query to try (e.g. different type_name, use title__wildcard instead of title__in, or id__eq instead of title, or looser path):
{{ "query": {{ "type_name": "...", ... }}, "_next": true }}

2) Confirm there are no results (do not retry):
{{ "_action": "answer" }}

Return only valid JSON. No other text."""

        user_prompt_template = """User question: {user_query}

Last query (returned 0 results):
{last_query}

Return either one alternative query with "_next": true, or {{ "_action": "answer" }}."""

        if conversation_history:
            history_text = "\n".join(f"{m['role']}: {m['content']}" for m in conversation_history[-3:])
            user_prompt_template = f"Previous conversation:\n{history_text}\n\n{user_prompt_template}"

        system_formatted = system_prompt.format(
            request_context=request_context_desc,
            content_types=content_types_desc,
        )
        return system_formatted, user_prompt_template

    @staticmethod
    def format_step_results(step_results: List[Dict]) -> str:
        """Format step results for the next-step prompt."""
        parts = []
        for i, step in enumerate(step_results, 1):
            q = step.get("query", {})
            res = step.get("result", {})
            items = res.get("items", [])
            total = res.get("items_total", len(items))
            parts.append(f"Step {i} query: {q}")
            if total == 0:
                parts.append(f"Step {i} result: no items")
            elif total <= 3:
                parts.append(f"Step {i} result ({total} items): {items}")
            else:
                parts.append(f"Step {i} result ({total} items, first 3): {items[:3]}")
        return "\n".join(parts)

    @staticmethod
    def _format_content_types(schema_info: Dict) -> str:
        """Format content types and fields for prompt."""
        lines = []
        for type_name, fields in schema_info.get("content_types", {}).items():
            field_list = ", ".join([f"{k} ({v})" for k, v in fields.items()])
            lines.append(f"- {type_name}: {field_list}")
        return "\n".join(lines) if lines else "No content types found"

    @staticmethod
    def _format_request_context(schema_info: Dict) -> str:
        """Format request context (path, id, type_name, title) for prompt."""
        ctx = schema_info.get("request_context", {})
        if not ctx:
            return "Not available"
        parts = [f"path: {ctx.get('path', '')}", f"id: {ctx.get('id', '')}"]
        if ctx.get("type_name"):
            parts.append(f"type_name: {ctx['type_name']}")
        if ctx.get("title") is not None:
            parts.append(f"title: {ctx['title']}")
        return ", ".join(parts)

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
        if "items" not in results and any(
            k in results for k in ("count", "total", "average", "overall_average")
        ):
            parts = [f"{k} = {v}" for k, v in results.items() if not k.startswith("by_")]
            by_parts = [f"{k} = {v}" for k, v in results.items() if k.startswith("by_")]
            if by_parts:
                parts.extend(by_parts)
            return "Aggregation result: " + ", ".join(parts)
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
