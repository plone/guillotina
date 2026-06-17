"""MCP integration for OAuth resource indicators, discovery, and auth policy."""

from guillotina.contrib.oauth.integrations.mcp import access as _access  # noqa: F401
from guillotina.contrib.oauth.integrations.mcp import discovery as _disc  # noqa: F401
from guillotina.contrib.oauth.integrations.mcp import grant as _grant  # noqa: F401
from guillotina.contrib.oauth.integrations.mcp import identifiers as _ids  # noqa: F401


def register_mcp_oauth_integration() -> None:
    from guillotina.contrib.oauth.discovery.protected_resource import register_protected_resource_provider
    from guillotina.contrib.oauth.indicators.registry import (
        register_allowed_indicator_resolver,
        register_required_indicator_resolver,
    )
    from guillotina.contrib.oauth.integrations.mcp.access import _mcp_protocol_audience_resolver
    from guillotina.contrib.oauth.integrations.mcp.discovery import _mcp_protected_resource_provider
    from guillotina.contrib.oauth.integrations.mcp.grant import _mcp_protocol_resource_resolver

    register_allowed_indicator_resolver(_mcp_protocol_resource_resolver)
    register_required_indicator_resolver(_mcp_protocol_audience_resolver)
    register_protected_resource_provider(_mcp_protected_resource_provider)
