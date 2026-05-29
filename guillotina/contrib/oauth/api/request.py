from urllib.parse import parse_qs

from guillotina.interfaces import WRITING_VERBS
from guillotina.response import HTTPBadRequest, HTTPPreconditionFailed


def check_writable_request(request):
    return request.method in WRITING_VERBS or (
        request.method == "GET" and str(getattr(request, "path", "")).endswith("/oauth/authorize")
    )


def normalize_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(normalize_list(item))
        return values
    return [item for item in str(value).split() if item]


def parse_form_encoded(body):
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values if len(values) > 1 else values[0] for key, values in parsed.items()}


def oauth_error(error, description=None, status=400):
    content = {"error": error}
    if description:
        content["error_description"] = description
    raise HTTPBadRequest(content=content) if status == 400 else HTTPPreconditionFailed(content=content)
