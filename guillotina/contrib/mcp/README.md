# guillotina.contrib.mcp

Contrib that exposes a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for Guillotina as an HTTP service. It provides **read-only tools** (search, count, get_content, list_children).

## Installation

1. Add the package to your dependencies (e.g. `contrib-requirements.txt` or `requirements.txt`):

   ```
   mcp>=1.0.0
   ```

2. Add the contrib to your application in `config.yaml`:

   ```yaml
   applications:
     - guillotina
     - guillotina.contrib.mcp
   ```

## Configuration

Default settings are defined in the contrib; you can override them in your app config:

```yaml
mcp:
  enabled: true
```

| Setting | Description |
|--------|-------------|
| `mcp.enabled` | If `false`, the `@mcp` service returns 404. Default: `true`. |
| `mcp.description_extras` | Optional dict: tool name → string appended to that tool's description (for LLM context). Keys: `search`, `count`, `get_content`, `list_children`. |
| `mcp.extra_tools_module` | Optional dotted path to a module that defines `register_extra_tools(mcp_server, backend)` to add project-specific MCP tools. |
| `mcp.token_max_duration_days` | Maximum allowed `duration_days` for `@mcp-token`. Default: `90`. |
| `mcp.token_allowed_durations` | Optional list of allowed values for `duration_days` (e.g. `[30, 60, 90]`). If not set, any integer from 1 to `token_max_duration_days` is allowed. |

## MCP service

The MCP server is exposed as a **service** on any resource. The resource (e.g. a container) is the context for all tools.

- **Endpoint**: `POST` or `GET` on `/{db}/{container_path}/@mcp` (e.g. `POST /db/guillotina/@mcp`).
- **Authentication**: Use normal Guillotina auth on the request to `@mcp`. The same user permissions apply. Two options:
  - **Bearer JWT**: Obtain a token via `POST /{db}/{container}/@login` (short-lived, e.g. 1 hour) or via `POST /{db}/{container}/@mcp-token` (long-lived, 30/60/90 days or custom). Send `Authorization: Bearer <token>` on each request to `@mcp`. For stable IDE/client configuration, prefer `@mcp-token`.
  - **Basic auth**: Send the same username/password as for Guillotina login (e.g. `Authorization: Basic <base64(user:password)>`).
- **Use case**: Same process as Guillotina.

Example with Basic auth:

```bash
curl -X POST -u root:password "http://localhost:8080/db/guillotina/@mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

Example with Bearer token (from `@mcp-token`):

```bash
# First obtain a long-lived token (e.g. 30 days)
TOKEN=$(curl -s -X POST -u root:password "http://localhost:8080/db/guillotina/@mcp-token" \
  -H "Content-Type: application/json" \
  -d '{"duration_days": 30}' | jq -r .token)
# Then call @mcp with the token
curl -X POST -H "Authorization: Bearer $TOKEN" "http://localhost:8080/db/guillotina/@mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

**Important:** The MCP transport requires the client to send `Accept: application/json, text/event-stream`. In Postman, add a header `Accept` = `application/json, text/event-stream`; otherwise you get HTTP 406 Not Acceptable.

### Endpoint `@mcp-token` (long-lived token for MCP)

Authenticated users can request a **long-lived JWT** for configuring MCP clients (e.g. Cursor, IDEs) without renewing every hour.

- **Endpoint**: `POST /{db}/{container_path}/@mcp-token`
- **Permission**: User must be authenticated (same as `@mcp`).
- **Body** (optional): `{"duration_days": 30}`. Default is 30. Allowed range: 1 to `mcp.token_max_duration_days` (default 90), or only values in `mcp.token_allowed_durations` if that option is set.
- **Response**: `{"token": "<jwt>", "exp": <timestamp>, "duration_days": <number>}`. Use the `token` as `Authorization: Bearer <token>` when calling `@mcp`.

## Tools (read-only)

| Tool | Description |
|------|-------------|
| `search` | Catalog search (like `@search`). Parameters: container path, query (filters, `_size`, `_from`, `_sort_asc` / `_sort_des`). |
| `count` | Count catalog results (like `@count`). |
| `get_content` | Get a resource by path or UID (like `GET` by path or `@resolveuid`). |
| `list_children` | List direct children of a container (like `@items` with pagination). |

## Com sap l’LLM quins paràmetres usar?

El client (Cursor, VS Code, etc.) **no** té els paràmetres hardcodats. Els obté del servidor MCP en connectar-se, mitjançant el protocol MCP.

1. **Descoberta d’eines**  
   En connectar (o en refrescar), el client envia una petició MCP estàndard **`tools/list`** al servidor Guillotina MCP. El servidor respon amb la llista d’eines disponibles i, per a cadascuna:
   - **nom** (p. ex. `search`, `get_content`)
   - **descripció** (el docstring de la funció)
   - **esquema d’entrada** (nom i tipus de cada paràmetre, extrets de la signatura de la funció)

2. **D’on surt l’esquema**  
   Al contrib, les eines es defineixen a `tools.py` amb `@mcp_server.tool()` sobre funcions async amb tipat. El SDK MCP (FastMCP) llegeix la signatura i els docstrings i genera l’esquema que s’envia al client. Per exemple:

   ```python
   @mcp_server.tool()
   async def search(
       container_path: typing.Optional[str] = None,
       query: typing.Optional[typing.Dict[str, str]] = None,
   ) -> dict:
       """Search the catalog. container_path is optional..."""
   ```

   Es converteix en una definició MCP amb `search`, la descripció i els paràmetres `container_path` (string, opcional) i `query` (object, opcional). El client rep aquest JSON i el passa a l’LLM.

3. **Com ho usa l’LLM**  
   Cursor (o un altre client) inclou aquestes definicions d’eines en el context de l’assistent. Quan l’usuari fa una pregunta (“quina carpeta té més items?”, “busca contenidors de tipus X”), l’model tria quina eina cridar i amb quins arguments (p. ex. `search` amb `query: {"type_name": "Folder"}`). El client envia **`tools/call`** amb el nom de l’eina i els arguments; el servidor MCP executa la funció (el nostre backend) i retorna el resultat, que el client torna a passar a l’LLM per continuar la conversa.

En resum: **l’LLM sap els paràmetres perquè el servidor MCP els publica via `tools/list`**, i aquests venen directament de les funcions que definim a `tools.py` (signatura + docstring). No cal configurar res més al client; només la URL i l’auth.

Per eines com `search` i `count`, el paràmetre `query` és un diccionari lliure (no hi ha esquema MCP per les claus). **L’LLM només “sap” quines claus pot usar (p. ex. `_sort_asc`, `_sort_des`, `type_name`) perquè les documentem al docstring de l’eina.** Al contrib hem posat al docstring els noms que segueix l’API @search de Guillotina; si afegiu més paràmetres a l’API de cerca, convé actualitzar el docstring de `search` (i `count` si aplica) perquè l’LLM els tingui al context.

## Permissions

The `@mcp` service requires the permission **`guillotina.mcp.Use`**, which is granted to **`guillotina.Authenticated`** by the contrib. Adjust grants in your app if you need to restrict or extend access.

## Extending the MCP for your project

Projects can give the LLM more context (e.g. your content types, field meanings) and add custom tools.

### Enriching tool descriptions

Extra text is appended to the base description of each tool so the LLM sees project-specific context.

**Option 1: config** — In your app config, set `mcp.description_extras` to a dict mapping tool name to a string:

```yaml
mcp:
  description_extras:
    search: "In this project, type_name 'Document' is the main content type; 'Folder' for containers."
    get_content: "Resources may have custom fields; use path relative to the container."
```

**Option 2: utility** — Register a callable utility providing `guillotina.contrib.mcp.interfaces.IMCPDescriptionExtras`. When called, it must return a dict `tool_name -> extra description string`. Use this when the text depends on code (e.g. content types from the registry).

```python
from guillotina import configure
from guillotina.contrib.mcp.interfaces import IMCPDescriptionExtras

@configure.utility(provides=IMCPDescriptionExtras)
class MyDescriptionExtras:
    def __call__(self):
        return {
            "search": "In this project, type_name 'Document' is the main content type.",
        }
```

Config and utility are merged; utility values are appended after config for the same tool.

### Adding custom tools

Set `mcp.extra_tools_module` to a dotted path of a module that defines a function **`register_extra_tools(mcp_server, backend)`**. That function receives the FastMCP server and InProcessBackend and can register more tools with `@mcp_server.tool()`.

```yaml
mcp:
  extra_tools_module: "myapp.mcp_tools"
```

```python
# myapp/mcp_tools.py
def register_extra_tools(mcp_server, backend):
    @mcp_server.tool()
    async def my_custom_tool(container_path: str = None, query: str = "") -> dict:
        """My project-specific tool. Does X with container_path and query."""
        # Use backend.search(..., backend.get_content(...), etc. as needed
        ...
```

---

## Configuració en clients (Cursor / VS Code)

Els clients MCP (Cursor, VS Code amb extensió MCP) es connecten al servidor Guillotina MCP mitjançant **Streamable HTTP**. La connexió es fa a l'endpoint `@mcp` del mateix servei Guillotina.

### Cursor

1. Obre **Settings → Developer → Edit Config** (o **Features → MCP → Add New MCP Server**).
2. Edita `~/.cursor/mcp.json` (global) o `.cursor/mcp.json` del projecte.
3. Afegeix un servidor amb `url` i, capçalera d’autenticació Basic.

```json
{
  "mcpServers": {
    "guillotina": {
      "url": "http://localhost:8080/db/guillotina/@mcp",
      "headers": {
        "Authorization": "Basic ${env:GUILLOTINA_BASIC_AUTH}"
      }
    }
  }
}
```

Cal que `GUILLOTINA_BASIC_AUTH` sigui el Base64 de `usuari:password` (per exemple `cm9vdDpwYXNzd29yZA==` per `root:password`). En terminal:

```bash
echo -n "root:password" | base64
```

Si preferiu no usar variable d’entorn, podeu posar la capçalera directament (eviteu en repos compartits):

```json
"headers": {
  "Authorization": "Basic cm9vdDpwYXNzd29yZA=="
}
```

Després de desar `mcp.json`, Cursor carrega les eines (search, count, get_content, list_children). Si no les veieu, feu un refresh o reinicia Cursor.

### VS Code

Amb la **extensió Model Context Protocol** (i VS Code 1.102+):

1. **Extensions** (Ctrl+Shift+X) → cercar “Model Context Protocol” → instal·lar.
2. Configuració MCP: depèn de l’extensió; si usa un fitxer tipus `mcp.json`, la forma és equivalent a Cursor: entrada amb `url` i opcionalment `headers` per Basic auth.

- URL: `http://localhost:8080/db/<container>/@mcp`
- Headers: `Authorization: Basic <base64(usuari:password)>`

Consulteu la documentació de l’extensió MCP per a VS Code per a la ubicació exacta del fitxer de configuració i el format (sovint similar al de Cursor).
