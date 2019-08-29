def get_ordered_content_type_value_list(value):
    """
    ca-ES,ca;q=0.9,en;q=0.8,es;q=0.7
    """
    result = []
    for idx, ct in enumerate(reversed(value.lower().split(","))):
        # idx used for apply tweaked value for tie breakers
        weight = 1.0
        ct_name = ct.split(";")[0].strip()
        for param in ct.split(";")[1:]:
            param = param.strip()
            if param.startswith("q="):
                try:
                    weight = float(param[len("q=") :])
                except ValueError:
                    pass
        result.append((weight + (idx / 1000), ct_name))
    return [i[1] for i in sorted(result, reverse=True)]


def get_acceptable_content_types(request):
    # We need to check for the language

    if "ACCEPT" in request.headers:
        return get_ordered_content_type_value_list(request.headers["ACCEPT"])
    else:
        return ["*/*"]


def get_acceptable_languages(request):
    if "ACCEPT-LANGUAGE" in request.headers:
        return get_ordered_content_type_value_list(request.headers["ACCEPT-LANGUAGE"])
    else:
        return ["en"]
