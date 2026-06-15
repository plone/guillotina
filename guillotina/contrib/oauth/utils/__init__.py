"""Cross-cutting helpers used across the OAuth contrib.

These modules are intentionally low-level and have no dependency on the
API/HTTP, flow/domain or storage packages so they can be imported anywhere.
"""

from guillotina.contrib.oauth.utils.crypto import access_token_signing_key, token_hash
from guillotina.contrib.oauth.utils.errors import raise_oauth_error
from guillotina.contrib.oauth.utils.request import (
    duplicate_param_names,
    form_content_type_valid,
    normalize_list,
    params_preserving_repeated,
    parse_form_encoded,
    peer_ip_address,
    reject_duplicate_params,
)
from guillotina.contrib.oauth.utils.time import timestamp, utcnow
from guillotina.contrib.oauth.utils.urls import (
    container_issuer_url,
    validate_issuer,
    well_known_protected_resource_url,
)
from guillotina.contrib.oauth.utils.writable import requires_writable_transaction


__all__ = [
    "access_token_signing_key",
    "token_hash",
    "raise_oauth_error",
    "duplicate_param_names",
    "form_content_type_valid",
    "normalize_list",
    "parse_form_encoded",
    "params_preserving_repeated",
    "peer_ip_address",
    "reject_duplicate_params",
    "timestamp",
    "utcnow",
    "container_issuer_url",
    "validate_issuer",
    "well_known_protected_resource_url",
    "requires_writable_transaction",
]
