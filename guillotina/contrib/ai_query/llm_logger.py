from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import json
import os


def _duration_line(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    return f"  duration: {round(seconds * 1000)}ms\n"


def _summary(obj: Any, max_items: int = 10) -> str:
    if isinstance(obj, dict):
        if "items" in obj and isinstance(obj["items"], list):
            total = obj.get("items_total", len(obj["items"]))
            n = len(obj["items"])
            return f"items={n}, items_total={total}"
        return json.dumps(obj, indent=2, default=str)
    if isinstance(obj, list):
        if len(obj) > max_items:
            return (
                json.dumps(obj[:max_items], indent=2, default=str) + f"\n... and {len(obj) - max_items} more"
            )
        return json.dumps(obj, indent=2, default=str)
    return str(obj)


def format_result_summary(result: Dict) -> str:
    """One-line summary of a search/aggregation result for step execution log."""
    if not result:
        return "empty"
    if "items" in result:
        n = len(result.get("items", []))
        total = result.get("items_total", n)
        return f"items={n}, items_total={total}"
    if any(k in result for k in ("total", "count", "average", "overall_average")):
        parts = [
            f"{k}={v}" for k, v in result.items() if k in ("total", "count", "average", "overall_average")
        ]
        return ", ".join(parts)
    return _summary(result, max_items=3)


def _format_catalog_result(result: Dict, max_items: int = 50) -> str:
    """Format catalog result for log: full if small, else summary + sample of items."""
    if not result:
        return "empty"
    if "items" in result and isinstance(result.get("items"), list):
        items = result["items"]
        total = result.get("items_total", len(items))
        if len(items) <= max_items:
            return json.dumps(result, indent=2, default=str)
        sample = {"items": items[:max_items], "items_total": total}
        return json.dumps(sample, indent=2, default=str) + f"\n... and {len(items) - max_items} more items"
    return json.dumps(result, indent=2, default=str)


class LLMInteractionLogger:
    """
    Logs all LLM interactions for a single request to a file (one file per request).
    Enable via ai_query.log_llm_interactions and set ai_query.log_llm_dir.
    """

    def __init__(
        self,
        request_id: str,
        enabled: bool,
        log_dir: Optional[str] = None,
    ):
        self.request_id = request_id
        self.enabled = enabled and bool(log_dir)
        self._path: Optional[str] = None
        self._file = None
        if self.enabled and log_dir:
            os.makedirs(log_dir, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            self._path = os.path.join(log_dir, f"{ts}_{request_id[:8]}.log")
            self._file = open(self._path, "w", encoding="utf-8")
            self._write(f"=== LLM interaction log ===\nrequest_id: {request_id}\n")

    def _write(self, text: str) -> None:
        if self._file:
            self._file.write(text)
            self._file.flush()

    def close(self) -> None:
        if self._file:
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None

    def log_request_start(self, query_text: str) -> None:
        if not self.enabled:
            return
        self._write(f"\n--- Request start ---\nquery: {query_text}\n")

    def log_translate_query(
        self,
        messages: List[Dict],
        response_text: str,
        parsed: Dict,
        duration_seconds: Optional[float] = None,
    ) -> None:
        if not self.enabled:
            return
        self._write("\n--- translate_query (natural language -> structured query) ---\n")
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            self._write(f"  [{role}]:\n{content}\n")
        self._write(f"  [LLM response]:\n{response_text}\n")
        self._write(f"  [parsed]:\n{json.dumps(parsed, indent=2, default=str)}\n")
        self._write(_duration_line(duration_seconds))

    def log_translate_next_step(
        self,
        step_index: int,
        messages: List[Dict],
        response_text: str,
        parsed: Dict,
        duration_seconds: Optional[float] = None,
    ) -> None:
        if not self.enabled:
            return
        self._write(f"\n--- translate_next_step (step {step_index}) ---\n")
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            self._write(f"  [{role}]:\n{content}\n")
        self._write(f"  [LLM response]:\n{response_text}\n")
        self._write(f"  [parsed]:\n{json.dumps(parsed, indent=2, default=str)}\n")
        self._write(_duration_line(duration_seconds))

    def log_catalog_search(
        self,
        query: Dict,
        result: Dict,
        step_index: Optional[int] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Log a Guillotina catalog search: query sent and response received."""
        if not self.enabled:
            return
        if step_index is not None:
            self._write(f"\n--- catalog search (step {step_index}) ---\n")
        else:
            self._write("\n--- catalog search ---\n")
        self._write(f"  query:\n{json.dumps(query, indent=2, default=str)}\n")
        self._write(f"  response:\n{_format_catalog_result(result)}\n")
        self._write(_duration_line(duration_seconds))

    def log_step_execution(self, step_index: int, query: Dict, result_summary: str) -> None:
        if not self.enabled:
            return
        self._write(f"\n--- step {step_index} execution ---\n")
        self._write(f"  query: {json.dumps(query, indent=2, default=str)}\n")
        self._write(f"  result summary: {result_summary}\n")

    def log_generate_response(
        self,
        messages: List[Dict],
        response_text: str,
        duration_seconds: Optional[float] = None,
    ) -> None:
        if not self.enabled:
            return
        self._write("\n--- generate_response (results -> natural language) ---\n")
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            self._write(f"  [{role}]:\n{content}\n")
        self._write(f"  [LLM response]:\n{response_text}\n")
        self._write(_duration_line(duration_seconds))

    def log_retry_on_empty(
        self,
        messages: List[Dict],
        response_text: str,
        parsed: Dict,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Log the retry-on-empty LLM call (alternative query or _action answer)."""
        if not self.enabled:
            return
        self._write("\n--- retry_on_empty (0 results, suggest alternative or confirm) ---\n")
        for m in messages:
            role = m.get("role", "")
            content = m.get("content", "")
            self._write(f"  [{role}]:\n{content}\n")
        self._write(f"  [LLM response]:\n{response_text}\n")
        self._write(f"  [parsed]:\n{json.dumps(parsed, indent=2, default=str)}\n")
        self._write(_duration_line(duration_seconds))

    def log_llm_error(
        self,
        step_name: str,
        error: Exception,
        messages: Optional[List[Dict]] = None,
        duration_seconds: Optional[float] = None,
    ) -> None:
        """Log an LLM call failure (e.g. timeout, API error)."""
        if not self.enabled:
            return
        self._write(f"\n--- {step_name} FAILED ---\n")
        self._write(f"  error: {type(error).__name__}: {error}\n")
        self._write(_duration_line(duration_seconds))
        if messages:
            for m in messages:
                role = m.get("role", "")
                content = m.get("content", "")
                self._write(f"  [request {role}]:\n{content}\n")

    def log_request_end(self) -> None:
        if not self.enabled:
            return
        self._write("\n--- Request end ---\n")
