from guillotina.interfaces import WRITING_VERBS


def check_writable_request(request):
    return request.method in WRITING_VERBS
