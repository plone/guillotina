# MCP

`guillotina.contrib.mcp` provides a low-level MCP integration layer built on
the official `mcp.server.lowlevel` primitives (no FastMCP wrapper).

## Installation

```bash
pip install "guillotina[mcp]"
```

## Configuration

```yaml
applications:
  - guillotina
  - guillotina.contrib.mcp

mcp:
  enabled: true
  server_name: guillotina-mcp
  default_child_limit: 50
```

## Runtime endpoints

- `GET /@mcp`: registry metadata and registered tools.
- `GET /@mcp/tools`: tool list and schemas.
- `POST /@mcp/tools/invoke`: executes one tool with payload
  `{ "tool": "<name>", "arguments": { ... } }`.
- `GET /@mcp/server/status`: validates low-level SDK availability.

## Built-in tools

- `resolve_path`: resolve a path and return basic metadata.
- `list_children`: list child resources from a folder-like resource.
- `serialize_resource`: execute Guillotina serialization adapters.
- `notify_modified`: emit an `ObjectModifiedEvent`.

The tool registry is implemented as a Guillotina utility and cache invalidation
is handled by subscribers on object add/modify/remove events.

