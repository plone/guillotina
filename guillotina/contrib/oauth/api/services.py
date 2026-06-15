from guillotina import configure
from guillotina.api.service import Service
from guillotina.contrib.oauth.api.endpoints.authorize import authorization_endpoint
from guillotina.contrib.oauth.api.endpoints.common import OAuthService
from guillotina.contrib.oauth.api.endpoints.consents import list_consents_endpoint, revoke_consent_endpoint
from guillotina.contrib.oauth.api.endpoints.register import client_registration_endpoint
from guillotina.contrib.oauth.api.endpoints.revoke import token_revocation_endpoint
from guillotina.contrib.oauth.api.endpoints.token import token_endpoint
from guillotina.contrib.oauth.api.well_known import WELL_KNOWN_HANDLERS, serve_well_known_metadata
from guillotina.interfaces import IApplication, IContainer
from guillotina.response import HTTPNotFound


# Dispatch tables mapping the ``oauth/{action}`` matchdict to its handler.
OAUTH_GET_ACTIONS = {
    "authorize": authorization_endpoint,
    "consents": list_consents_endpoint,
}
OAUTH_POST_ACTIONS = {
    "register": client_registration_endpoint,
    "authorize": authorization_endpoint,
    "token": token_endpoint,
    "revoke": token_revocation_endpoint,
    "consents": revoke_consent_endpoint,
}


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.Public",
    name=".well-known/{action}",
    allow_access=True,
)
class ContainerOAuthWellKnownService(OAuthService):
    async def __call__(self):
        self.oauth_store()
        action = self.request.matchdict.get("action", "")
        if action in WELL_KNOWN_HANDLERS:
            return WELL_KNOWN_HANDLERS[action](self.request, self.context)
        return HTTPNotFound(content={"reason": f"Unknown well-known endpoint: {action}"})


@configure.service(
    context=IApplication,
    method="GET",
    permission="guillotina.Public",
    name=".well-known/{action}/{target_path:path}",
    allow_access=True,
)
class ApplicationOAuthWellKnownService(Service):
    async def __call__(self):
        action = self.request.matchdict.get("action", "")
        if action not in WELL_KNOWN_HANDLERS:
            return HTTPNotFound(content={"reason": f"Unknown well-known endpoint: {action}"})
        target_path = self.request.matchdict.get("target_path", "")
        try:
            return await serve_well_known_metadata(self.request, action, target_path, WELL_KNOWN_HANDLERS)
        except HTTPNotFound as exc:
            return exc


@configure.service(
    context=IContainer,
    method="GET",
    permission="guillotina.Public",
    name="oauth/{action}",
    allow_access=True,
)
class ContainerOAuthGetService(OAuthService):
    async def __call__(self):
        action = self.request.matchdict.get("action", "")
        handler = OAUTH_GET_ACTIONS.get(action)
        if handler is None:
            return HTTPNotFound(content={"reason": f"Unknown OAuth GET action: {action}"})
        return await handler(self, self.oauth_store())


@configure.service(
    context=IContainer,
    method="POST",
    permission="guillotina.Public",
    name="oauth/{action}",
    allow_access=True,
)
class ContainerOAuthPostService(OAuthService):
    async def __call__(self):
        action = self.request.matchdict.get("action", "")
        handler = OAUTH_POST_ACTIONS.get(action)
        if handler is None:
            return HTTPNotFound(content={"reason": f"Unknown OAuth POST action: {action}"})
        return await handler(self, self.oauth_store())
