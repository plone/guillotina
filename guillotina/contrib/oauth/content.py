"""OAuth data model helpers.

OAuth state is stored in a reserved container annotation named ``.oauth`` with
four dictionaries: ``clients``, ``codes``, ``refresh_tokens`` and ``consents``.
Authorization codes and refresh tokens are never stored in plaintext; only HMAC
SHA-256 digests are persisted.
"""

from guillotina.annotations import AnnotationData


OAUTH_STORAGE_KEY = ".oauth"


def new_oauth_storage():
    return AnnotationData(
        {
            "clients": {},
            "codes": {},
            "refresh_tokens": {},
            "consents": {},
        }
    )
