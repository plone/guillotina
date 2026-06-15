from guillotina.interfaces import WRITING_VERBS


def requires_writable_transaction(request):
    """Return True when the request should run inside a writable transaction.

    OAuth authorization requests are an exception: they are GETs but they
    may create consent records or authorization codes.
    """
    return request.method in WRITING_VERBS or (
        request.method == "GET" and str(getattr(request, "path", "")).endswith("/oauth/authorize")
    )
