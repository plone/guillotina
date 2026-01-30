# MCP (Model Context Protocol)

The `guillotina.contrib.mcp` package exposes Guillotina content to [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) clients and provides a chat endpoint where an LLM can query content using the same tools.

**What you get:**

- **@mcp** — MCP-over-HTTP endpoint so IDEs (Cursor, VS Code, etc.) and other MCP clients can discover and call tools against a container.
- **@chat** — REST endpoint to send a message and get an LLM reply; the LLM can call the same tools (search, count, get_content, list_children) in-process. API keys stay on the server.

Both use the same read-only tools and the same permissions.

## Installation

**Requires Python 3.10+** (the `mcp` package does not support older versions).

1. Add dependencies (e.g. in `contrib-requirements.txt` or `requirements.txt`):

   ```
   mcp>=1.0.0; python_version >= "3.10"
   litellm>=1.0.0
   ```

   `litellm` is required only if you use **@chat**.

2. Enable the contrib in your app config:

   ```yaml
   applications:
     - guillotina
     - guillotina.contrib.mcp
   ```

## Configuration

You can override these in your application config:

| Setting | Description |
|--------|-------------|
| `mcp.enabled` | If `false`, `@mcp` returns 404. Default: `true`. |
| `mcp.chat_enabled` | If `false`, `@chat` returns 404. Default: `true`. |
| `mcp.chat_model` | Model for @chat (LiteLLM). Required if you use chat. Examples: `openai/gpt-4o-mini`, `gemini/gemini-1.5-flash`, `anthropic/claude-3-haiku`. |
| `mcp.token_max_duration_days` | Max `duration_days` for `@mcp-token`. Default: `90`. |
| `mcp.token_allowed_durations` | Optional list of allowed values (e.g. `[30, 60, 90]`). If set, only these values are accepted. |
| `mcp.description_extras` | Optional dict: tool name → string appended to that tool’s description (for LLM context). Keys: `search`, `count`, `get_content`, `list_children`. |
| `mcp.extra_tools_module` | Optional dotted path to a module that defines `register_extra_tools(mcp_server, backend)` (and optionally chat extensions). See [Extending](#extending). |

For **@chat**, the LLM API key is read **only from environment variables**: `OPENAI_API_KEY`, `GEMINI_API_KEY` (or `GOOGLE_API_KEY`), or `ANTHROPIC_API_KEY` depending on `mcp.chat_model`. Do not put API keys in config files.

## Using the MCP endpoint (@mcp)

- **URL**: `POST` or `GET` on `/{db}/{container_path}/@mcp` (e.g. `POST /db/guillotina/@mcp`).
- **Auth**: Same as any Guillotina request. Use either:
  - **Basic**: `Authorization: Basic <base64(user:password)>`.
  - **Bearer**: Obtain a token with `POST /{db}/{container}/@login` or `POST /{db}/{container}/@mcp-token`, then `Authorization: Bearer <token>`.
- **Headers**: Clients must send `Accept: application/json, text/event-stream`; otherwise the server returns 406.

The resource you call (e.g. a container) is the context for all tools: search, count, get_content, and list_children are scoped to that resource.

**Obtaining a long-lived token for MCP clients**

- **Endpoint**: `POST /{db}/{container_path}/@mcp-token`
- **Auth**: Required (e.g. Basic or short-lived JWT).
- **Body** (optional): `{"duration_days": 30}`. Default 30; max and allowed values come from config.
- **Response**: `{"token": "<jwt>", "exp": <timestamp>, "duration_days": <number>}`.

Use this token as `Authorization: Bearer <token>` when calling `@mcp` from Cursor, VS Code, or other MCP clients.

**Example (list tools)**

```bash
# With Basic auth
curl -X POST -u root:password "http://localhost:8080/db/guillotina/@mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

MCP clients discover tools via the standard MCP protocol (e.g. `tools/list`, `tools/call`). Configure your IDE/client with the `@mcp` URL and the same auth (Basic or Bearer).

## Using the chat endpoint (@chat)

- **URL**: `POST /{db}/{container_path}/@chat`
- **Auth**: Same as `@mcp` (e.g. Bearer from `@mcp-token` or `@login`).
- **Body**:
  - Single message: `{"message": "user text"}`.
  - Full history (to keep context): `{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}, ...]}`.
- **Response**: `{"content": "assistant reply text"}`.

The server runs an LLM (LiteLLM) and executes the same tools (search, count, get_content, list_children) when the model requests them. To keep conversation context, your client should accumulate all messages and send them in `messages` on each request.

**Example**

```bash
TOKEN=$(curl -s -X POST -u root:password "http://localhost:8080/db/guillotina/@mcp-token" \
  -H "Content-Type: application/json" -d '{"duration_days": 30}' | jq -r .token)

curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8080/db/guillotina/@chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "How many items are in this container?"}' | jq .
```

## Built-in tools

All tools are read-only and scoped to the resource (container) you call @mcp or @chat on:

| Tool | Purpose |
|------|---------|
| `search` | Catalog search (same query keys as Guillotina `@search`: `type_name`, `term`, `_size`, `_from`, `_sort_asc` / `_sort_des`, field filters like `field__eq`, etc.). |
| `count` | Count catalog results with the same query filters (no `_size` / `_from` / sort). |
| `get_content` | Get a resource by path (relative to container) or by UID. |
| `list_children` | List direct children of a path, with optional pagination (`from_index`, `page_size`). |

Parameters and descriptions are exposed via MCP (`tools/list`) and to the LLM in @chat automatically.

## Permissions

- **@mcp** and **@chat** require permission `guillotina.mcp.Use`.
- **@mcp-token** requires `guillotina.mcp.IssueToken`.
- The contrib grants both to `guillotina.Authenticated`. Adjust grants in your app if you need to restrict or extend access.

## Extending

### Richer tool descriptions

Set `mcp.description_extras` to a dict mapping tool name to extra text (appended to the built-in description), or register a utility providing `guillotina.contrib.mcp.interfaces.IMCPDescriptionExtras` that returns such a dict. Useful to describe your content types or project-specific usage.

### Custom tools (MCP and optional @chat)

Set `mcp.extra_tools_module` to a dotted path to a module that defines:

- **`register_extra_tools(mcp_server, backend)`** — Required. Register additional tools with `@mcp_server.tool()`. They are then available on **@mcp** (e.g. to Cursor/VS Code). Use `backend` (InProcessBackend) to call search, get_content, etc. from your tool.

To make the same tools available in **@chat** (so the LLM can call them), the same module can optionally define:

- **`get_extra_chat_tools()`** — Returns a list of tool definitions in the same format as the built-in ones: each item is `{"type": "function", "function": {"name": "...", "description": "...", "parameters": {"type": "object", "properties": {...}}}}`.
- **`execute_extra_tool(backend, name, arguments)`** — Async. Called when the LLM invokes one of your extra tools. Receives `backend`, tool `name`, and a dict of `arguments`; return a JSON-serialisable result.

Tool names must be unique and must not clash with the built-in names: `search`, `count`, `get_content`, `list_children`.

**Example**

```yaml
# config
mcp:
  extra_tools_module: "myapp.mcp_tools"
```

```python
# myapp/mcp_tools.py
def register_extra_tools(mcp_server, backend):
    @mcp_server.tool()
    async def my_tool(container_path: str = None, query: str = "") -> dict:
        """My project tool. Does X with container_path and query."""
        # use backend.search(...), backend.get_content(...), etc.
        return {"result": "..."}

def get_extra_chat_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "my_tool",
                "description": "My project tool. Does X with container_path and query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "container_path": {"type": "string", "description": "Optional path relative to container."},
                        "query": {"type": "string", "description": "Query."},
                    },
                },
            },
        },
    ]

async def execute_extra_tool(backend, name, arguments):
    if name == "my_tool":
        # run same logic as the MCP tool
        return {"result": "..."}
    return {"error": f"Unknown tool: {name}"}
```
