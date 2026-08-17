# Guillotina MCP

`guillotina.contrib.mcp` exposes a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for Guillotina. LLM clients (Cursor, VS Code, etc.) connect over **Streamable HTTP** and use JSON-RPC 2.0 to list and call tools, and to read resources.

The integration uses the official `mcp.server.lowlevel` primitives (no FastMCP wrapper). Tools run **in-process** with the same request context, transaction, and security as a normal Guillotina API call.

## Requirements

- **Python 3.10+** (the `mcp` package does not support older versions).
- Install the optional extra: `pip install "guillotina[mcp]"`.

## Installation

1. Install the MCP extra:

   ```bash
   pip install "guillotina[mcp]"
   ```

2. Add the contrib to your application:

   ```yaml
   applications:
     - guillotina
     - guillotina.contrib.mcp
   ```

3. (Optional) Install the `mcp` addon on a container if you use container-level addon registration.

## Configuration

Default settings are provided by the contrib; override them in your app config:

```yaml
mcp:
  enabled: true
  server_name: guillotina-mcp
  default_child_limit: 50
```

| Setting | Description |
|--------|-------------|
| `mcp.enabled` | When `false`, the protocol endpoint is unavailable. Default: `true`. |
| `mcp.server_name` | Name sent in MCP `initialize` (`serverInfo.name`). Default: `guillotina-mcp`. |
| `mcp.default_child_limit` | Default `limit` for `list_children` when not specified. Default: `50`. |

The tool registry is loaded as utility `mcp_tool_registry` (`IMCPToolRegistry`).

## Endpoint and authentication

The MCP protocol is exposed on the **container** (or any resource) that acts as context for tool execution:

- **URL**: `POST /{db}/{container_path}/@mcp/protocol`
- **Example**: `POST http://localhost:8080/db/guillotina/@mcp/protocol`
- **Permission**: `guillotina.MCPExecute` (granted to `guillotina.Manager` by default).
- **Authentication**: Same as the rest of Guillotina (Basic auth or Bearer JWT from `@login`). The authenticated user’s permissions apply to every tool and resource call.

Clients must send:

```http
Content-Type: application/json
Accept: application/json, text/event-stream
```

Without the `Accept` header, the transport may respond with **406 Not Acceptable**.

The endpoint is JSON-only and does not open a GET SSE stream. Per the MCP Streamable HTTP spec, `GET` and `DELETE` on `@mcp/protocol` return **405 Method Not Allowed** with `Allow: POST`, so clients continue with POST/JSON instead of treating a **404** as a dead session.

Example: list tools via JSON-RPC:

```bash
curl -X POST -u root:root \
  "http://localhost:8080/db/guillotina/@mcp/protocol" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

The service delegates to the MCP Streamable HTTP transport, which writes the response directly to the ASGI channel. Guillotina returns a dummy response marked as already sent so no duplicate body is written.

### Cursor / VS Code

Point the MCP client at the protocol URL and pass auth headers, for example in `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "guillotina": {
      "url": "http://localhost:8080/db/guillotina/@mcp/protocol",
      "headers": {
        "Authorization": "Basic cm9vdDpyb290"
      }
    }
  }
}
```

On connect, the client calls `tools/list` and `resources/list` to discover capabilities.

## Built-in tools

All default tools are **read-only**. They do not create, update, or delete content.

Paths are resolved relative to the **MCP service context** (usually the container) unless they start with `/`, in which case they are resolved from the container root.

| Tool | Cacheable | Description |
|------|-----------|-------------|
| `resolve_path` | yes | Resolve a path. Default: minimal metadata (`id`, `@type`, `title`, `path`). Use `include_serialized=true` for full JSON (like `GET`). |
| `list_children` | yes | List direct children of a folder-like resource. Catalog when available, else `async_items()`. Paginate with `page` and `limit` (max 200). |
| `search` | yes | Catalog search. Requires a real catalog utility (not the default in-memory one). |

### Tool parameters (summary)

**`resolve_path`**

- `path` (string, default `"/"`): absolute (`/foo`) or relative (`foo`) path.
- `include_serialized` (boolean, default `false`): when `true`, adds a `serialized` key with full Guillotina JSON (fields, behaviors, etc., per registered serializers). Requires `guillotina.ViewContent` on the resolved resource, like a normal `GET`.

**`list_children`**

- `path` (string, default `"/"`).
- `limit` (integer, 1–200, default from `mcp.default_child_limit`).
- `page` (integer, default `1`): used when falling back to `async_items()`.
- `include_serialized` (boolean, default `false`): full JSON per child in each item. Requires `guillotina.ViewContent` on each serialized child, like a normal `GET`.

**`search`**

- `query` (object, **required**): Guillotina catalog query. Supports `type_name`, `path__starts`, `creators`, date filters, etc. Pagination: `b_start`, `b_size` (max 1000). Limit fields: `_metadata` (e.g. `"id,type_name,title,path"`).

Example `tools/call` (minimal metadata):

```bash
curl -X POST -u root:root \
  "http://localhost:8080/db/guillotina/@mcp/protocol" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 2,
    "params": {
      "name": "resolve_path",
      "arguments": {"path": "/"}
    }
  }'
```

Example with full resource JSON:

```json
{
  "name": "resolve_path",
  "arguments": {"path": "/my-item", "include_serialized": true}
}
```

There is **no** built-in tool to create or modify content. Register custom tools (see below) or use the REST API (`POST` / `PATCH`).

## Built-in MCP resources

Resources are read-only JSON documents exposed via `resources/list` and `resources/read`:

| Name | URI | Description |
|------|-----|-------------|
| `info` | `guillotina://resources/info` | Guillotina version, container id/path, enabled addons. |
| `health` | `guillotina://resources/health` | Database connectivity status. |
| `config` | `guillotina://resources/config` | MCP settings and loaded applications. |
| `users` | `guillotina://resources/users` | List users when `guillotina.contrib.dbusers` is enabled. |
| `catalog` | `guillotina://resources/catalog` | Whether a catalog utility is configured. |
| `summary` | `guillotina://resources/summary` | Summary of a resource; optional query `?path=/some/id` on the URI. |

Example:

```bash
curl -X POST -u root:root \
  "http://localhost:8080/db/guillotina/@mcp/protocol" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "resources/read",
    "id": 3,
    "params": {"uri": "guillotina://resources/summary?path=/"}
  }'
```

## Caching (optional — Redis not required)

**Redis is not required to use MCP.** The protocol endpoint and all built-in tools work without `guillotina.contrib.redis`. If Redis is unavailable, the registry disables tool caching and every call runs directly against the database or catalog.

When `guillotina.contrib.redis` is enabled, cacheable tools (`resolve_path`, `list_children`, `search`) store results in Redis for one hour (including responses with `include_serialized=true`; cache keys differ per argument set, authenticated principal, container, and context).

Subscribers invalidate the cache on `IObjectAddedEvent`, `IObjectModifiedEvent`, and `IBeforeObjectRemovedEvent` so listings and search results stay consistent after content changes.

## Permissions

| Permission | Purpose |
|------------|---------|
| `guillotina.MCPExecute` | Call `@mcp/protocol` and execute tools. |
| `guillotina.MCPView` | Reserved for view-level MCP services (granted to Manager/Owner). |

Adjust role grants in your application if non-managers should use MCP.

Built-in tools also enforce content permissions internally. Minimal metadata from `resolve_path`, `list_children`, and `summary` requires `guillotina.AccessContent`. Full serialized JSON via `include_serialized=true` additionally requires `guillotina.ViewContent` on the serialized resource, matching Guillotina's default `GET` view.

## Adding tools for your project

Register tools on the shared `IMCPToolRegistry` utility. The usual pattern is a subscriber on application startup:

```python
# myapp/mcp_tools.py
from typing import Any, Dict

from guillotina import configure
from guillotina.component import query_utility
from guillotina.contrib.mcp.interfaces import IMCPToolRegistry
from guillotina.interfaces import IApplicationInitializedEvent
from guillotina.utils import navigate_to


async def count_items_tool(context: Any, request: Any, arguments: Dict[str, Any]) -> Dict[str, Any]:
    path = arguments.get("path", "/")
    target = await navigate_to(context, path)
    total = await target.async_len() if hasattr(target, "async_len") else 0
    return {"path": path, "count": total}


@configure.subscriber(for_=IApplicationInitializedEvent)
async def register_project_mcp_tools(event):
    registry = query_utility(IMCPToolRegistry)
    if registry is None:
        return
    registry.register_tool(
        name="count_items",
        description="Count direct children of a folder-like resource at path.",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative Guillotina path",
                    "default": "/",
                }
            },
        },
        handler=count_items_tool,
        cacheable=True,
    )
```

Ensure `configure.scan("myapp.mcp_tools")` runs (or the module is imported from your package `includeme`).

### Tool handler contract

Each handler is an async callable:

```python
async def handler(context, request, arguments: dict) -> dict:
    ...
```

- `context`: the resource the `@mcp` service was invoked on (typically the container).
- `request`: the active Guillotina request (auth, serializers, etc.).
- `arguments`: JSON object from the MCP client (`tools/call` params).
- **Return value**: JSON-serializable `dict` (encoded as text content in the protocol response).

Use `registry.register_tool(...)` with a unique `name`. Avoid clashing with built-in names: `resolve_path`, `list_children`, `search`.

Set `cacheable=True` only if the result is safe to cache and your tool does not perform writes. Use an argument name other than `include_serialized` for heavy optional payloads, or set `cacheable=False`.

### Adding MCP resources

```python
registry.register_resource(
    name="project_info",
    uri="guillotina://resources/project_info",
    description="Project-specific metadata for the LLM.",
    endpoint="@mcp/resources/project_info",
    handler=my_async_handler,  # async def handler(request) -> dict
)
```

Resource handlers receive the HTTP `request` (with URI query params merged into `request.query` when using `?path=` on the URI).

### Alternative: custom registry factory

For many tools, subclass `MCPToolRegistry` and register your factory in `load_utilities`:

```yaml
load_utilities:
  mcp_tool_registry:
    provides: guillotina.contrib.mcp.interfaces.IMCPToolRegistry
    factory: myapp.mcp.MyMCPToolRegistry
    settings: {}
```

Call `register_tool` from your subclass `__init__` after `super().__init__()`.

## How clients discover parameters

MCP clients do not hardcode tool parameters. On connect they call `tools/list` and receive each tool’s `name`, `description`, and `inputSchema` (JSON Schema). The LLM uses that schema when calling `tools/call`.

For `search`, the `query` object is a free-form catalog query; document supported keys in your tool `description` or in project-specific docs so the model uses the right filters (`type_name`, `path__startswith`, `_metadata`, etc.).

## Limitations

- **No content creation or updates** in the default tool set. Use custom tools or the REST API (`POST` / `PATCH`).
- **`search`** and catalog-backed **`list_children`** need a configured catalog utility (e.g. `guillotina.contrib.catalog.pg`).
- MCP runs in the **same process** as Guillotina; heavy tool logic affects request workers.
