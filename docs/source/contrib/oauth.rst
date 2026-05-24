OAuth authorization server
==========================

Install ``guillotina.contrib.oauth`` as an application and install the
``oauth`` addon in each container that should act as an authorization server.
OAuth state is stored in the reserved container annotation ``.oauth``.

Supported flow
--------------

The contrib implements public-client OAuth 2.1 Authorization Code with PKCE
(``S256``), dynamic client registration, opaque refresh tokens, revocation, and
JWT access tokens signed with Guillotina's configured JWT secret.
Authorization codes and refresh tokens are stored only as HMAC SHA-256 hashes.

Endpoints are container scoped::

  GET  /db/container/.well-known/oauth-authorization-server
  POST /db/container/oauth/register
  GET  /db/container/oauth/authorize
  POST /db/container/oauth/authorize
  POST /db/container/oauth/token
  POST /db/container/oauth/revoke

Examples
--------

Register a public client::

  curl -X POST https://host/db/container/oauth/register \
    -H 'Content-Type: application/json' \
    -d '{"client_name":"MCP Client","redirect_uris":["http://127.0.0.1:12345/callback"],"token_endpoint_auth_method":"none"}'

Open the authorize URL in a browser::

  https://host/db/container/oauth/authorize?response_type=code&client_id=CLIENT&redirect_uri=http://127.0.0.1:12345/callback&scope=guillotina:mcp.read&code_challenge=CHALLENGE&code_challenge_method=S256&resource=https://host/db/container/@mcp/protocol

Exchange the code::

  curl -X POST https://host/db/container/oauth/token \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -d 'grant_type=authorization_code&client_id=CLIENT&redirect_uri=http://127.0.0.1:12345/callback&code=CODE&code_verifier=VERIFIER'

Refresh and revoke::

  curl -X POST https://host/db/container/oauth/token \
    -d 'grant_type=refresh_token&client_id=CLIENT&refresh_token=REFRESH'

  curl -X POST https://host/db/container/oauth/revoke \
    -d 'client_id=CLIENT&token=REFRESH&token_type_hint=refresh_token'

MCP scopes
----------

``guillotina:mcp.read`` allows basic MCP discovery/read calls.
``guillotina:mcp.search`` allows search. ``guillotina:mcp.content.read`` is
required for serialized content responses.

``@login`` JWTs authenticate Guillotina sessions directly. OAuth access tokens
include ``token_type=oauth_access_token``, ``client_id``, ``scope`` and
audience/resource claims and are validated by the OAuth validator. MCP clients
should use OAuth discovery and must not store manually copied bearer tokens in
configuration.
