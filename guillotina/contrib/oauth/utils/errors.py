from guillotina.response import HTTPBadRequest, HTTPPreconditionFailed


def raise_oauth_error(error, description=None, status=400):
    content = {"error": error}
    if description:
        content["error_description"] = description
    raise HTTPBadRequest(content=content) if status == 400 else HTTPPreconditionFailed(content=content)
