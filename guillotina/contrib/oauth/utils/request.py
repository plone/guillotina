from urllib.parse import parse_qs

from guillotina.contrib.oauth.utils.errors import raise_oauth_error


def normalize_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(normalize_list(item))
        return values
    return [item for item in str(value).split() if item]


def params_preserving_repeated(query):
    params = {}
    seen = set()
    keys = query.keys() if hasattr(query, "keys") else []
    for key in keys:
        if key in seen:
            continue
        seen.add(key)
        getall = getattr(query, "getall", None)
        if callable(getall):
            try:
                values = getall(key, [])
            except TypeError:
                values = getall(key)
        else:
            value = query.get(key) if hasattr(query, "get") else None
            values = value if isinstance(value, (list, tuple)) else [value]
        params[key] = values if len(values) > 1 else values[0]
    return params


def form_content_type_valid(request):
    content_type = request.headers.get("content-type", "")
    return content_type.split(";", 1)[0].strip().lower() == "application/x-www-form-urlencoded"


def peer_ip_address(request):
    """Return a stable identifier for the connecting peer.

    Uses the direct transport peer address (ASGI ``scope['client']``) rather
    than ``X-Forwarded-For`` so the value cannot be spoofed by the caller to
    bypass throttling. Behind a trusted reverse proxy every request shares the
    proxy address; operators wanting per-client limits there should terminate
    rate limiting at the proxy.
    """
    scope = getattr(request, "scope", None) or {}
    client = scope.get("client")
    if client:
        return str(client[0])
    return "unknown"


def duplicate_param_names(params, singleton_fields):
    duplicates = []
    for field in singleton_fields:
        getall = getattr(params, "getall", None)
        if callable(getall):
            try:
                values = getall(field, [])
            except TypeError:
                values = getall(field)
            if len(values) > 1:
                duplicates.append(field)
            continue
        value = params.get(field) if hasattr(params, "get") else None
        if isinstance(value, (list, tuple)) and len(value) > 1:
            duplicates.append(field)
    return duplicates


def reject_duplicate_params(params, singleton_fields):
    duplicates = duplicate_param_names(params, singleton_fields)
    if duplicates:
        raise_oauth_error("invalid_request", f"duplicate parameter: {duplicates[0]}")


def parse_form_encoded(body, *, singleton_fields=()):
    parsed = parse_qs(body, keep_blank_values=True)
    reject_duplicate_params(parsed, singleton_fields)
    return {key: values if len(values) > 1 else values[0] for key, values in parsed.items()}
