# OAuth authorization server

Install `guillotina.contrib.oauth` as an application and install the `oauth` addon in each container that should act as an authorization server. OAuth state is stored in PostgreSQL tables, configured via the `oauth_storage` utility settings.

## Configuration

To enable and configure the OAuth 2.0 Authorization Code + PKCE public-client profile, the following settings must be defined in your Guillotina configuration (e.g., `config.yaml`).

### 1. Enable the Application

Add `guillotina.contrib.oauth` to your list of active applications:

```yaml
applications:
  - guillotina.contrib.oauth
```

### 2. Configure JWT Secrets

Since OAuth Access Tokens are issued as signed JSON Web Tokens (JWT), you **must** configure the global JWT signing settings:

```yaml
jwt:
  secret: YOUR_SECURE_JWT_SECRET_KEY  # Change this to a secure key!
  algorithm: HS256
```

OAuth derives a purpose-specific signing key from `jwt.secret` (domain-separated from Guillotina's generic `@login` JWTs). Access tokens carry `token_type=oauth_access_token` and are validated only by `OAuthJWTValidator`.

### 3. Configure Authentication Extractors and Validators

Loading `guillotina.contrib.oauth` registers `OAuthJWTValidator` and the default password/JWT validators automatically via `app_settings`. You must still configure `auth_extractors` so the browser login and consent forms work:

```yaml
auth_extractors:
  - guillotina.auth.extractors.BearerAuthPolicy
  - guillotina.auth.extractors.BasicAuthPolicy
  - guillotina.auth.extractors.WSTokenAuthPolicy
  - guillotina.auth.extractors.CookiePolicy       # Required for browser login & consent form
```

Override `auth_token_validators` only when you need a custom validator order or additional validators.

### 4. Set Write Permissions for GET Requests

Guillotina normally prevents database writes on GET requests. Since the `/oauth/authorize` endpoint (which is a GET request) needs to create/validate authorization states, `check_writable_request` must allow writes for that path. Loading `guillotina.contrib.oauth` sets this automatically; override only if you use a custom checker:

```yaml
check_writable_request: guillotina.contrib.oauth.utils.writable.requires_writable_transaction
```

### 5. Customize OAuth Server Settings (Optional)

Protocol settings (issuer, token TTLs, PKCE, scopes, rate limits) live under the `oauth` block. PostgreSQL cleanup tuning lives under `load_utilities.oauth_storage.settings`:

```yaml
oauth:
  issuer: null                    # Custom issuer URL (e.g. "https://auth.example.com"); see below
  trust_proxy_headers: false      # Honor X-Forwarded-Proto / X-VirtualHost-* when deriving issuer
  authorization_code_ttl: 600     # Time to live in seconds for Authorization Codes (default 10 min)
  access_token_ttl: 3600          # Time to live in seconds for Access Tokens (default 1 hour)
  refresh_token_ttl: 2592000      # Time to live in seconds for Refresh Tokens (default 30 days)
  consent_ttl: 2592000            # Remembered consent lifetime (default 30 days; 0 = indefinite)
  allowed_code_challenge_methods: # PKCE S256 is always required for public clients
    - S256
  scopes_supported:               # Whitelist of scopes accepted at authorize and registration
    - guillotina:access
  registration_rate_limit: 20     # Dynamic registration requests per IP (0 = disabled)
  registration_rate_window: 600
  login_rate_limit: 10            # Failed login attempts per IP+username (0 = disabled)
  login_rate_window: 300
  token_rate_limit: 120           # Token endpoint requests per IP (0 = disabled)
  token_rate_window: 60
  revoke_rate_limit: 120          # Revocation endpoint requests per IP (0 = disabled)
  revoke_rate_window: 60

load_utilities:
  oauth_storage:
    settings:
      cleanup_interval: 900       # seconds between expired-row cleanup runs
      cleanup_batch_size: 5000    # rows deleted per cleanup batch
```

The same cleanup keys may still be set under `oauth` for backward compatibility; utility settings take precedence.

OAuth state is always persisted in PostgreSQL tables (`oauth_clients`, `oauth_authorization_codes`, …). A PostgreSQL database storage is required.

### 6. Issuer URL and Reverse Proxies

The issuer URL appears in discovery metadata, JWT `iss` claims, and authorization redirects ([RFC 9207](https://www.rfc-editor.org/rfc/rfc9207)).

When `oauth.issuer` is set, it must be an absolute `http` or `https` URL without query, fragment, or userinfo. Production issuers must use `https` (plain `http` is allowed only for `localhost`, `127.0.0.1`, and `::1`).

When `oauth.issuer` is `null` (the default), the issuer is derived from the request:

- With `trust_proxy_headers: false` (the default), only the transport scheme and `Host` header are used. Spoofable `X-Forwarded-Proto` headers are ignored.
- With `trust_proxy_headers: true`, set this only behind a trusted reverse proxy so forwarded scheme and virtual-host headers are honored.

## Discovery and OpenID Connect

Authorization server metadata ([RFC 8414](https://www.rfc-editor.org/rfc/rfc8414)) is exposed at:

```text
GET /db/container/.well-known/oauth-authorization-server
GET /.well-known/oauth-authorization-server/db/container
```

The OAuth contrib does not expose `/.well-known/openid-configuration` because that path identifies OpenID Connect provider metadata, and this contrib does not implement OpenID Connect (`id_token`, UserInfo, OIDC JWKS, subject types, etc.).

## Architecture: protocol phases

The OAuth contrib is organized around the three phases of the protocol:

| Phase | Module | RFC |
|-------|--------|-----|
| Discovery | `discovery/` | RFC 8414, RFC 9728 |
| Grant (resource validation) | `indicators/grant.py` | RFC 8707 |
| Access (token validation) | `indicators/access.py`, `auth/` | RFC 8707 |
| Token issuance | `flow/` | RFC 6749 |
| MCP integration | `integrations/mcp/` | — |

### Resource indicator vocabulary

A single *resource indicator* (the URL like `https://host/db/container/@mcp/protocol`) appears across discovery, grant, and access:

| Phase | Where | Term |
|-------|-------|------|
| Discovery (protected resource) | `oauth-protected-resource` JSON `"resource"` field | resource |
| Grant | authorize/token `resource=` parameter | resource indicator |
| Access | JWT `aud` claim | resource indicator |

Authorization server metadata (RFC 8414) does not include a `resource` field. The `resource` field appears only in protected resource metadata (RFC 9728).

The same resource indicator at grant time becomes the `aud` of the JWT and is checked at access time. Multiple `resource=` parameters may be sent at authorize time; each allowed value is stored and included in `aud`.

## Allowed `resource` values (RFC 8707)

The `resource` parameter is restricted to URLs returned by registered resolvers in `guillotina.contrib.oauth.indicators`. The oauth application registers the **container issuer** by default (`https://host/db/container`). When both `guillotina.contrib.oauth` and `guillotina.contrib.mcp` are in `applications`, OAuth also loads the MCP integration, registers `{container}/@mcp/protocol` (and subfolder MCP paths such as `{container}/subfolder/@mcp/protocol`), and exposes MCP protected-resource metadata. That MCP resolver is ignored for OAuth-only deployments, so the MCP protocol URL is not accepted as a `resource` unless MCP is enabled.

At the token endpoint, `resource` is optional. When present, every value must be a subset of the resources bound to the authorization code or refresh token.

Register allowed values from your addon `includeme` (or startup hook):

```python
from guillotina.contrib.oauth.indicators.registry import register_allowed_indicator_resolver

def my_resolver(request, container):
    from guillotina.contrib.oauth.utils.urls import container_issuer_url
    base = container_issuer_url(request, container)
    return {f"{base}/@services/my-hook"}

register_allowed_indicator_resolver(my_resolver)
```

Register a required audience for the access phase when a protocol endpoint must enforce a specific `aud` value:

```python
from guillotina.contrib.oauth.indicators.registry import register_required_indicator_resolver

def my_audience_resolver(request, container):
    if str(getattr(request, "path", "") or "").endswith("/@services/my-hook"):
        from guillotina.contrib.oauth.utils.urls import container_issuer_url
        return f"{container_issuer_url(request, container)}/@services/my-hook"

register_required_indicator_resolver(my_audience_resolver)
```

## Dynamic client registration and redirect URIs

`/oauth/authorize` accepts only redirect URIs that are already present on the client record. Loopback redirect URIs may use a different runtime port than the registered URI, as recommended for native apps. `/oauth/register` always creates a new public client and returns a server-issued `client_id`; client-supplied `client_id` values are rejected. The registration endpoint does not update existing clients and does not issue client secrets. Public clients that need multiple callbacks, such as Cursor native and loopback redirects, must include all allowed `redirect_uris` in the same dynamic client registration request. HTTPS redirect URIs are accepted for web clients. Plain HTTP is accepted only for loopback/native redirects (`localhost`, `127.0.0.1`, `::1`). Private-use native redirects using reverse-domain schemes such as `com.example.app:/oauth2redirect/provider` are accepted. Redirect URIs with fragments are rejected.

Registered clients must include the `guillotina:access` scope (the default when `scope` is omitted). Only scopes listed in `oauth.scopes_supported` are accepted.

## Supported flow

The contrib implements an OAuth 2.0 Authorization Code + PKCE (`S256`) public-client profile, aligned with RFC 9700 guidance and selected extensions including dynamic client registration, authorization server metadata, resource indicators, issuer identification, protected resource metadata, opaque refresh tokens, revocation, and JWT access tokens signed with a key derived from Guillotina's configured `jwt.secret`.

![OAuth 2.0 authorization code flow with PKCE in Guillotina](../_static/oauth-flow.svg)

Endpoints are container scoped:

```text
GET  /db/container/.well-known/oauth-authorization-server
POST /db/container/oauth/register
GET  /db/container/oauth/authorize
```

RFC 8414 discovery for issuers with a path component (such as `/db/container`) is also exposed at the application root:

```text
GET /.well-known/oauth-authorization-server/db/container
```

When using MCP, protected resource metadata follows [RFC 9728](https://www.rfc-editor.org/rfc/rfc9728):

```text
GET /db/container/.well-known/oauth-protected-resource
GET /.well-known/oauth-protected-resource/db/container/@mcp/protocol
GET /.well-known/oauth-protected-resource/db/container/subfolder/@mcp/protocol
```

Other container-scoped endpoints:

```text
POST /db/container/oauth/authorize    # login form, consent form, and consent submission
POST /db/container/oauth/token
POST /db/container/oauth/revoke
GET  /db/container/oauth/consents   # list remembered consents (authenticated)
POST /db/container/oauth/consents   # revoke a remembered consent (authenticated)
```

Opaque token prefixes: `goc_` (authorization codes), `gor_` (refresh tokens).

## How to Use PKCE and the OAuth Flow (Step-by-Step)

Follow these steps to generate PKCE credentials, register a client, authorize a user, and exchange the resulting authorization code for an Access Token.

### Step 1: Generate PKCE Secrets on the Client

Clients must generate a high-entropy random `code_verifier` between **43 and 128** characters from the unreserved set in RFC 7636 (`[A-Z] [a-z] [0-9] - . _ ~`), and compute its `code_challenge` using SHA-256 (BASE64URL encoding without padding).

#### **Bash / OpenSSL Example:**

If you are working on the terminal, you can quickly generate both secrets in your shell using `openssl`:

```bash
# 1. Generate a secure random code_verifier (URL-safe base64 encoded)
code_verifier=$(openssl rand -base64 32 | tr -d '=' | tr '/+' '_-')
echo "code_verifier: $code_verifier"

# 2. Compute the S256 code_challenge
code_challenge=$(echo -n "$code_verifier" | openssl dgst -binary -sha256 | openssl base64 | tr -d '=' | tr '/+' '_-')
echo "code_challenge: $code_challenge"
```

#### **Python Example:**

```python
import base64
import hashlib
import secrets

# 1. Generate the random code_verifier (keep this secret on the client!)
code_verifier = secrets.token_urlsafe(64)

# 2. Compute the code_challenge (SHA-256 hashed and encoded as URL-safe base64 with no padding)
hash_digest = hashlib.sha256(code_verifier.encode('ascii')).digest()
code_challenge = base64.urlsafe_b64encode(hash_digest).rstrip(b'=').decode('ascii')
```

#### **JavaScript Example:**

```javascript
// 1. Generate the random code_verifier (keep this secret!)
function generateCodeVerifier() {
  const charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~";
  const array = new Uint8Array(64);
  window.crypto.getRandomValues(array);
  return Array.from(array, (b) => charset[b % charset.length]).join("");
}

// 2. Compute the S256 code_challenge
async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const hashed = await window.crypto.subtle.digest("SHA-256", data);

  return btoa(String.fromCharCode(...new Uint8Array(hashed)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}
```

### Step 2: Register a Public Client

Register your public client on the Guillotina container:

```bash
curl -X POST http://localhost:8080/db/container/oauth/register \
  -H 'Content-Type: application/json' \
  -d '{"client_name":"MCP Client","redirect_uris":["http://127.0.0.1:12345/callback"],"token_endpoint_auth_method":"none"}'
```

Save the resulting `client_id` returned by the server.

### Step 3: Direct the User to the Authorization Endpoint (Send Challenge)

Direct the user's browser to the authorize URL. **Here you must append the `code_challenge` and set `code_challenge_method=S256`** as query parameters.

For a **REST API client** (container-wide access), omit `resource` or set it to the container URL:

```text
http://localhost:8080/db/container/oauth/authorize?response_type=code&client_id=CLIENT_ID&redirect_uri=http://127.0.0.1:12345/callback&scope=guillotina:access&code_challenge=YOUR_CODE_CHALLENGE&code_challenge_method=S256&state=some_random_state
```

For an **MCP client**, include the MCP protocol endpoint as `resource`:

```text
http://localhost:8080/db/container/oauth/authorize?response_type=code&client_id=CLIENT_ID&redirect_uri=http://127.0.0.1:12345/callback&scope=guillotina:access&code_challenge=YOUR_CODE_CHALLENGE&code_challenge_method=S256&state=some_random_state&resource=http://localhost:8080/db/container/@mcp/protocol
```

The `scope` parameter is required and must include `guillotina:access`.

The GET request returns an HTML login form. The user submits credentials via **POST** to the same `/oauth/authorize` URL (preserving all query parameters and adding `username`, `password`, and the hidden `oauth_csrf` field from the form). If consent is required, a consent form is shown and the user submits **POST** with `decision=allow` (or `deny`) and the same parameters.

Once the user logs in and consents, they are redirected back to your `redirect_uri`. The redirect includes the authorization code, the original `state`, and the issuer identifier `iss` ([RFC 9207](https://www.rfc-editor.org/rfc/rfc9207)):

```text
http://127.0.0.1:12345/callback?code=goc_XYZ123&state=some_random_state&iss=http://localhost:8080/db/container
```

### Step 4: Exchange the Code for Access & Refresh Tokens (Send Verifier)

Now, send a POST request to the token endpoint to exchange the received code for actual tokens. **Here you must provide the original `code_verifier` (in plaintext) as a parameter** so the server can verify it against the challenge from Step 3:

```bash
curl -X POST http://localhost:8080/db/container/oauth/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'grant_type=authorization_code&client_id=CLIENT_ID&redirect_uri=http://127.0.0.1:12345/callback&code=goc_XYZ123&code_verifier=YOUR_CODE_VERIFIER'
```

You may optionally narrow the token audience with `resource=` (every value must have been authorized in Step 3).

If successful, the response will contain your `access_token` and `refresh_token`.

### Step 5: Refresh and Revoke (Optional)

To obtain a new access token using your refresh token:

```bash
curl -X POST http://localhost:8080/db/container/oauth/token \
  -d 'grant_type=refresh_token&client_id=CLIENT_ID&refresh_token=YOUR_REFRESH_TOKEN'
```

Guillotina rotates refresh tokens on every successful refresh. The response contains a new `access_token` and a new `refresh_token`:

```json
{
  "access_token": "NEW_ACCESS_TOKEN",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "NEW_REFRESH_TOKEN",
  "scope": "guillotina:access"
}
```

Clients must persist the new `refresh_token` and discard the old one immediately. The previous refresh token is revoked as soon as the rotation succeeds.

Reusing an already-rotated refresh token returns `invalid_grant` but does not invalidate the current token in the rotation chain. Serialize refresh operations so two concurrent requests do not try to use the same refresh token at the same time.

To revoke an active refresh token (this revokes the entire refresh-token family from the same authorization grant):

```bash
curl -X POST http://localhost:8080/db/container/oauth/revoke \
  -d 'client_id=CLIENT_ID&token=YOUR_REFRESH_TOKEN&token_type_hint=refresh_token'
```

Access token revocation is not supported (`token_type_hint=access_token` returns `unsupported_token_type`). Revoking a refresh token also deletes the remembered consent for that grant.

Authenticated users can list and revoke remembered consents. Revoking a consent also revokes every refresh token that user holds for that client:

```bash
curl http://localhost:8080/db/container/oauth/consents \
  -H "Authorization: Bearer ACCESS_TOKEN"

curl -X POST http://localhost:8080/db/container/oauth/consents \
  -H "Authorization: Bearer ACCESS_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'consent_key=CONSENT_KEY'
```

## Authorization model

OAuth provides **authentication** and **resource binding**. **Authorization** is always enforced with native Guillotina permissions on the authenticated user.

| Concern | Mechanism |
|---------|-----------|
| Who is the user? | OAuth token `sub` claim |
| Which client? | OAuth token `client_id` claim |
| Which resource? | Token audience (`aud`) — container URL or MCP endpoint |
| What can they do? | Guillotina roles and ACLs (`AddContent`, `ModifyContent`, `MCPExecute`, …) |

OAuth access tokens must include the `guillotina:access` scope. Authorization is still enforced with native Guillotina permissions on the authenticated user.

### REST API clients

Authorize without `resource` (defaults to the container). Use the access token as a Bearer token on any Guillotina API endpoint. The user's existing roles and ACLs apply.

```bash
curl http://localhost:8080/db/container/@addons \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### MCP clients (Cursor)

Authorize with `resource` set to the MCP protocol URL. MCP additionally verifies that the token audience includes that endpoint.

Example Cursor `mcp.json`:

```json
"mcp-name": {
    "url": "http://localhost:8080/db/container/@mcp/protocol",
    "auth": {
      "scopes": [
        "guillotina:access"
      ]
    }
  }
```

`@login` JWTs authenticate Guillotina sessions directly. OAuth access tokens include `token_type=oauth_access_token`, `client_id`, `scope` and audience/resource claims and are validated by the OAuth validator. MCP clients should use OAuth discovery and must not store manually copied bearer tokens in configuration.

MCP also accepts native Guillotina authentication (for example an existing `@login` session) when OAuth is not used.
