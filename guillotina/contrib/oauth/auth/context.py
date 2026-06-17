"""Typed context for a validated OAuth access token attached to the request."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OAuthTokenContext:
    client_id: str
    scopes: frozenset[str]
    resource_indicators: frozenset[str]
    claims: dict
