from guillotina import configure
from guillotina._settings import app_settings
from guillotina.api.service import Service
from guillotina.contrib.mcp.backend import clear_mcp_context
from guillotina.contrib.mcp.backend import InProcessBackend
from guillotina.contrib.mcp.backend import set_mcp_context
from guillotina.contrib.mcp.tools import get_all_chat_tools
from guillotina.contrib.mcp.tools import get_extra_tools_module
from guillotina.interfaces import IResource
from guillotina.response import HTTPNotFound
from guillotina.response import HTTPPreconditionFailed

import json
import logging
import os


logger = logging.getLogger("guillotina")

MAX_TOOL_ROUNDS = 10


def _get_api_key_for_model(model: str) -> str:
    if model.startswith("openai/"):
        return os.environ.get("OPENAI_API_KEY") or ""
    if model.startswith("gemini/"):
        return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    if model.startswith("anthropic/"):
        return os.environ.get("ANTHROPIC_API_KEY") or ""
    return ""


async def _execute_tool(backend: InProcessBackend, name: str, arguments: dict):
    args = arguments or {}
    if name == "search":
        return await backend.search(None, args.get("query") or {})
    if name == "count":
        return await backend.count(None, args.get("query") or {})
    if name == "get_content":
        return await backend.get_content(
            None,
            args.get("path"),
            args.get("uid"),
        )
    if name == "list_children":
        return await backend.list_children(
            None,
            args.get("path") or "",
            args.get("from_index", 0),
            args.get("page_size", 20),
        )
    mod = get_extra_tools_module()
    if mod is not None and hasattr(mod, "execute_extra_tool"):
        return await mod.execute_extra_tool(backend, name, args)
    return {"error": f"Unknown tool: {name}"}


@configure.service(
    context=IResource,
    method="POST",
    permission="guillotina.mcp.Use",
    name="@chat",
    summary="Chat with LLM using MCP tools (OpenAI, Gemini, Anthropic)",
)
class Chat(Service):
    __body_required__ = False

    async def __call__(self):
        mcp_settings = app_settings.get("mcp", {})
        if not mcp_settings.get("chat_enabled", True):
            raise HTTPNotFound(content={"reason": "Chat is disabled"})
        chat_model = mcp_settings.get("chat_model")
        if not chat_model:
            raise HTTPPreconditionFailed(
                content={
                    "reason": "chat_model is not configured",
                    "hint": "Set mcp.chat_model (e.g. openai/gpt-4o)",
                }
            )
        try:
            body = await self.request.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        message = body.get("message")
        messages = body.get("messages")
        if messages is not None:
            if not isinstance(messages, list):
                raise HTTPPreconditionFailed(content={"reason": "messages must be a list"})
        elif message is not None:
            messages = [{"role": "user", "content": str(message)}]
        else:
            raise HTTPPreconditionFailed(content={"reason": "message or messages is required"})

        set_mcp_context(self.context)
        try:
            return await self._run_chat(messages, chat_model, mcp_settings)
        finally:
            clear_mcp_context()

    async def _run_chat(self, messages: list, chat_model: str, mcp_settings: dict):
        litellm = __import__("litellm", fromlist=["acompletion"])
        acompletion = getattr(litellm, "acompletion")
        tools = get_all_chat_tools()
        api_key = _get_api_key_for_model(chat_model)
        backend = InProcessBackend()
        kwargs = {"model": chat_model, "messages": messages, "tools": tools}
        if api_key:
            kwargs["api_key"] = api_key
        for _ in range(MAX_TOOL_ROUNDS):
            response = await acompletion(**kwargs)
            choice = response.choices[0] if response.choices else None
            if not choice:
                raise HTTPPreconditionFailed(content={"reason": "Empty response from LLM"})
            msg = choice.message
            tool_calls = getattr(msg, "tool_calls", None) or []
            if not tool_calls:
                content = getattr(msg, "content", None) or ""
                return {"content": content}
            assistant_msg = {"role": "assistant", "content": getattr(msg, "content", None)}
            tool_calls_list = []
            for tc in tool_calls:
                tc_id = getattr(tc, "id", None) or (tc.get("id") if isinstance(tc, dict) else "")
                fn = getattr(tc, "function", None) or (tc.get("function") if isinstance(tc, dict) else {})
                name = getattr(fn, "name", None) if fn else None
                if name is None and isinstance(fn, dict):
                    name = fn.get("name", "")
                raw_args = getattr(fn, "arguments", None) if fn else None
                if raw_args is None and isinstance(fn, dict):
                    raw_args = fn.get("arguments", "{}")
                tool_calls_list.append(
                    {
                        "id": tc_id,
                        "type": "function",
                        "function": {"name": name or "", "arguments": raw_args or "{}"},
                    }
                )
            assistant_msg["tool_calls"] = tool_calls_list
            messages.append(assistant_msg)
            for tc in tool_calls:
                tc_id = getattr(tc, "id", None) or (tc.get("id") if isinstance(tc, dict) else "")
                fn = getattr(tc, "function", None) or (tc.get("function") if isinstance(tc, dict) else {})
                name = getattr(fn, "name", None) if fn else None
                if name is None and isinstance(fn, dict):
                    name = fn.get("name", "")
                raw_args = getattr(fn, "arguments", None) if fn else None
                if raw_args is None and isinstance(fn, dict):
                    raw_args = fn.get("arguments", "{}")
                name = name or ""
                raw_args = raw_args or "{}"
                try:
                    arguments = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    arguments = {}
                try:
                    result = await _execute_tool(backend, name, arguments)
                except Exception as e:
                    logger.exception("MCP chat tool %s failed", name)
                    result = {"error": str(e)}
                messages.append({"role": "tool", "tool_call_id": tc_id, "content": json.dumps(result)})
            kwargs["messages"] = messages
        raise HTTPPreconditionFailed(content={"reason": f"Max tool rounds ({MAX_TOOL_ROUNDS}) exceeded"})
