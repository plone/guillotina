import logging
import string
from guillotina._settings import app_settings
from jwcrypto import jwk


logger = logging.getLogger('guillotina')


def get_jwk_key(settings=None):
    if settings is None:
        settings = app_settings
    if settings.get('jwk') is None:
        if not settings.get('debug'):
            logger.warning(
                'You are utilizing JWK keys but you have not provided '
                'a jwk key setting in your application settings. '
                'A key has been dynamically generated for you; however, '
                'if you are running more than one guillotina process, '
                'the key will NOT be shared between them and your '
                'application will not function properly')
        key = jwk.JWK.generate(kty='oct', size=256)
        settings['jwk'] = key
    return settings['jwk']


def secure_passphrase(val: str) -> bool:
    '''
    Attempt to guess if a passphrase is of succifient complexity
    '''
    if len(val) < 15:
        return False
    if len([v for v in val if v not in string.ascii_letters]) < 5:
        return False

    return True
