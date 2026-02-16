from guillotina import configure
from guillotina._settings import app_settings
from guillotina.api.service import Service
from guillotina.contrib.mcp.backend import clear_mcp_context
from guillotina.contrib.mcp.backend import get_mcp_context
from guillotina.contrib.mcp.backend import InProcessBackend
from guillotina.contrib.mcp.backend import set_mcp_context
from guillotina.contrib.mcp.tools import _normalize_query
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


def _get_litellm_credentials(model: str):
    api_key = ""
    api_base = None
    if model.startswith("openai/"):
        api_key = os.environ.get("OPENAI_API_KEY") or ""
    elif model.startswith("gemini/"):
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    elif model.startswith("anthropic/"):
        api_key = os.environ.get("ANTHROPIC_API_KEY") or ""
    elif model.startswith("groq/"):
        api_key = os.environ.get("GROQ_API_KEY") or ""
    elif model.startswith("openrouter/"):
        api_key = os.environ.get("OPENROUTER_API_KEY") or ""
        api_base = os.environ.get("OPENROUTER_API_BASE") or None
    elif model.startswith("minimax/"):
        api_key = os.environ.get("MINIMAX_API_KEY") or ""
        api_base = os.environ.get("MINIMAX_API_BASE") or None
    elif model.startswith("mistral/"):
        api_key = os.environ.get("MISTRAL_API_KEY") or ""
    elif model.startswith("deepseek/"):
        api_key = os.environ.get("DEEPSEEK_API_KEY") or ""
    elif model.startswith("cerebras/"):
        api_key = os.environ.get("CEREBRAS_API_KEY") or ""
    return api_key, api_base


def _get_value(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


async def _context_for_path(container_path):
    ctx = get_mcp_context()
    if ctx is None:
        return None
    if container_path:
        from guillotina.utils import navigate_to

        try:
            return await navigate_to(ctx, "/" + container_path.strip("/"))
        except KeyError:
            return None
    return ctx


async def _execute_tool(backend: InProcessBackend, name: str, arguments: dict):
    args = arguments or {}
    container_path = args.get("container_path") or None
    context = await _context_for_path(container_path)
    if name == "search":
        if context is None:
            return {"items": [], "items_total": 0}
        return await backend.search(context, _normalize_query(args.get("query")))
    if name == "count":
        if context is None:
            return 0
        return await backend.count(context, _normalize_query(args.get("query")))
    if name == "get_content":
        if context is None:
            return {}
        return await backend.get_content(context, args.get("path"), args.get("uid"))
    if name == "list_children":
        if context is None:
            return {"items": [], "items_total": 0}
        return await backend.list_children(
            context,
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
    summary="Chat with LLM using MCP tools (OpenAI, Gemini, Anthropic, Groq, OpenRouter, MiniMax, Mistral, Deepseek, Cerebras)",  # noqa: E501
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
        api_key, api_base = _get_litellm_credentials(chat_model)
        backend = InProcessBackend()
        kwargs = {"model": chat_model, "messages": messages, "tools": tools}
        if api_key:
            kwargs["api_key"] = api_key
        if api_base:
            kwargs["api_base"] = api_base
        for _ in range(MAX_TOOL_ROUNDS):
            response = await acompletion(**kwargs)
            choices = _get_value(response, "choices", None) or []
            choice = choices[0] if choices else None
            if not choice:
                raise HTTPPreconditionFailed(content={"reason": "Empty response from LLM"})
            msg = _get_value(choice, "message", None)
            if msg is None:
                raise HTTPPreconditionFailed(content={"reason": "Empty response from LLM"})
            tool_calls = _get_value(msg, "tool_calls", None) or []
            if isinstance(tool_calls, dict):
                tool_calls = [tool_calls]
            elif not isinstance(tool_calls, list):
                tool_calls = []
            if not tool_calls:
                content = _get_value(msg, "content", None) or ""
                return {"content": content}
            assistant_msg = {"role": "assistant", "content": _get_value(msg, "content", None)}
            tool_calls_list = []
            for tc in tool_calls:
                tc_id = _get_value(tc, "id", "") or ""
                fn = _get_value(tc, "function", None) or {}
                name = _get_value(fn, "name", "") or ""
                raw_args = _get_value(fn, "arguments", "{}")
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
                tc_id = _get_value(tc, "id", "") or ""
                fn = _get_value(tc, "function", None) or {}
                name = _get_value(fn, "name", "") or ""
                raw_args = _get_value(fn, "arguments", "{}")
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
