

def get_acceptable_content_types(request):
    # We need to check for the language

    accepted = []

    if 'ACCEPT' in request.headers:
        for ct in request.headers['ACCEPT'].split(','):
            accepted.append(ct.split(';')[0].lower())

    return accepted


def get_acceptable_languages(request):
    # We need to check for the language
    langs = []
    if 'ACCEPT-LANGUAGE' in request.headers:
        for ct in request.headers['ACCEPT-LANGUAGE'].split(','):
            langs.append(ct.split(';')[0].lower())
    else:
        langs = ['en']

    return langs
