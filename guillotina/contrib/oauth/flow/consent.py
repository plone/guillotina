def build_consent_key(user_id, client_id, scopes, resources):
    return "|".join([user_id, client_id, " ".join(sorted(scopes)), " ".join(sorted(resources))])
