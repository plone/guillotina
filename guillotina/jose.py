from base64 import urlsafe_b64decode
from base64 import urlsafe_b64encode
from collections import namedtuple
from copy import deepcopy
from Crypto.Cipher import AES
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import HMAC
from Crypto.Hash import SHA256
from Crypto.Hash import SHA384
from Crypto.Hash import SHA512
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Signature import PKCS1_v1_5 as PKCS1_v1_5_SIG
from struct import pack
from time import time

import binascii
import datetime
import struct
import ujson
import zlib


__all__ = ['encrypt', 'decrypt', 'sign', 'verify']


JWE = namedtuple('JWE', ['header', 'cek', 'iv', 'ciphertext', 'tag'])
JWS = namedtuple('JWS', ['header', 'payload', 'signature'])
JWT = namedtuple('JWT', ['header', 'claims'])


CLAIM_ISSUER = 'iss'
CLAIM_SUBJECT = 'sub'
CLAIM_AUDIENCE = 'aud'
CLAIM_EXPIRATION_TIME = 'exp'
CLAIM_NOT_BEFORE = 'nbf'
CLAIM_ISSUED_AT = 'iat'
CLAIM_JWT_ID = 'jti'

# these are temporary to allow graceful deprecation of legacy encrypted tokens.
# these will be removed in v1.0
_TEMP_VER_KEY = '__v'
_TEMP_VER = 2


class Error(Exception):
    """ The base error type raised by jose
    """
    def __init__(self, message):
        self.message = message


class Expired(Error):
    """ Raised during claims validation if a JWT has expired
    """
    pass


class NotYetValid(Error):
    """ Raised during claims validation is a JWT is not yet valid
    """
    pass


def serialize_compact(jwt):
    """ Compact serialization of a :class:`~jose.JWE` or :class:`~jose.JWS`

    :rtype: str
    :returns: A string, representing the compact serialization of a
              :class:`~jose.JWE` or :class:`~jose.JWS`.
    """
    return b'.'.join(jwt)


def deserialize_compact(jwt):
    """ Deserialization of a compact representation of a :class:`~jwt.JWE`

    :param jwt: The serialized JWT to deserialize.
    :rtype: :class:`~jose.JWT`.
    :raises: :class:`~jose.Error` if the JWT is malformed
    """
    parts = jwt.split(b'.')

    # http://tools.ietf.org/html/
    # draft-ietf-jose-json-web-encryption-23#section-9
    if len(parts) == 3:
        token_type = JWS
    elif len(parts) == 5:
        token_type = JWE
    else:
        raise Error('Malformed JWT')

    return token_type(*parts)


def encrypt(claims, jwk, adata=b'', add_header=None, alg='RSA-OAEP',
            enc='A128CBC-HS256', rng=get_random_bytes, compression=None):
    """ Encrypts the given claims and produces a :class:`~jose.JWE`

    :param claims: A `dict` representing the claims for this
                   :class:`~jose.JWE`.
    :param jwk: A `dict` representing the JWK to be used for encryption of
                the CEK. This parameter is algorithm-specific.
    :param adata: Arbitrary string data to add to the authentication
                  (i.e. HMAC). The same data must be provided during
                  decryption.
    :param add_header: Additional items to be added to the header. Additional
                       headers *will* be authenticated.
    :param alg: The algorithm to use for CEK encryption
    :param enc: The algorithm to use for claims encryption
    :param rng: Random number generator. A string of random bytes is expected
                as output.
    :param compression: The compression algorithm to use. Currently supports
                `'DEF'`.
    :rtype: :class:`~jose.JWE`
    :raises: :class:`~jose.Error` if there is an error producing the JWE
    """
    # copy so the injected claim doesn't mutate the input claims
    # this is a temporary hack to allow for graceful deprecation of tokens,
    # ensuring that the library can still handle decrypting tokens issued
    # before the implementation of the fix
    claims = deepcopy(claims)
    assert _TEMP_VER_KEY not in claims
    claims[_TEMP_VER_KEY] = _TEMP_VER

    header = dict(add_header or {}, enc=enc, alg=alg)

    # promote the temp key to the header
    assert _TEMP_VER_KEY not in header
    header[_TEMP_VER_KEY] = claims[_TEMP_VER_KEY]

    plaintext = json_encode(claims)

    # compress (if required)
    if compression is not None:
        header['zip'] = compression
        try:
            (compress, _) = COMPRESSION[compression]
        except KeyError:
            raise Error(
                'Unsupported compression algorithm: {}'.format(compression))
        plaintext = compress(plaintext)

    # body encryption/hash
    ((cipher, _), key_size), ((hash_fn, _), hash_mod) = JWA[enc]
    iv = rng(AES.block_size)
    encryption_key = rng(hash_mod.digest_size)
    encryption_key_index = hash_mod.digest_size // 2

    ciphertext = cipher(
        plaintext, encryption_key[-encryption_key_index:], iv
    )
    hash = hash_fn(
        _jwe_hash_str(ciphertext, iv, adata),
        encryption_key[:-encryption_key_index], hash_mod
    )

    # cek encryption
    (cipher, _), _ = JWA[alg]
    encryption_key_ciphertext = cipher(encryption_key, jwk)

    jwe_components = (
        json_encode(header), encryption_key_ciphertext, iv, ciphertext,
        auth_tag(hash)
    )
    return JWE(*map(b64encode_url, jwe_components))


def decrypt(jwe, jwk, adata=b'', validate_claims=True,
            expiry_seconds=None):
    """ Decrypts a deserialized :class:`~jose.JWE`

    :param jwe: An instance of :class:`~jose.JWE`
    :param jwk: A `dict` representing the JWK required to decrypt the content
                of the :class:`~jose.JWE`.
    :param adata: Arbitrary string data used during encryption for additional
                  authentication.
    :param validate_claims: A `bool` indicating whether or not the `exp`, `iat`
                            and `nbf` claims should be validated. Defaults to
                            `True`.
    :param expiry_seconds: An `int` containing the JWT expiry in seconds, used
                           when evaluating the `iat` claim. Defaults to `None`,
                           which disables `iat` claim validation.
    :rtype: :class:`~jose.JWT`
    :raises: :class:`~jose.Expired` if the JWT has expired
    :raises: :class:`~jose.NotYetValid` if the JWT is not yet valid
    :raises: :class:`~jose.Error` if there is an error decrypting the JWE
    """
    header, encryption_key_ciphertext, iv, ciphertext, tag = map(
        b64decode_url, jwe
    )
    header = json_decode(header)

    # decrypt cek
    (_, decipher), _ = JWA[header['alg']]
    encryption_key = decipher(encryption_key_ciphertext, jwk)

    # decrypt body
    ((_, decipher), _), ((hash_fn, _), mod) = JWA[header['enc']]

    version = header.get(_TEMP_VER_KEY)
    if version:
        plaintext = decipher(
            ciphertext, encryption_key[-mod.digest_size // 2:], iv
        )
        hash = hash_fn(
            _jwe_hash_str(ciphertext, iv, adata, version),
            encryption_key[:-mod.digest_size // 2], mod=mod
        )
    else:
        plaintext = decipher(ciphertext, encryption_key[:-mod.digest_size], iv)
        hash = hash_fn(
            _jwe_hash_str(ciphertext, iv, adata, version),
            encryption_key[-mod.digest_size:], mod=mod
        )

    if not const_compare(auth_tag(hash), tag):
        raise Error('Mismatched authentication tags')

    if 'zip' in header:
        try:
            (_, decompress) = COMPRESSION[header['zip']]
        except KeyError:
            raise Error('Unsupported compression algorithm: {}'.format(
                header['zip']))

        plaintext = decompress(plaintext)

    claims = json_decode(plaintext)
    try:
        del claims[_TEMP_VER_KEY]
    except KeyError:
        # expected when decrypting legacy tokens
        pass

    _validate(claims, validate_claims, expiry_seconds)

    return JWT(header, claims)


def sign(claims, jwk, add_header=None, alg='HS256'):
    """ Signs the given claims and produces a :class:`~jose.JWS`

    :param claims: A `dict` representing the claims for this
                   :class:`~jose.JWS`.
    :param jwk: A `dict` representing the JWK to be used for signing of the
                :class:`~jose.JWS`. This parameter is algorithm-specific.
    :parameter add_header: Additional items to be added to the header.
                           Additional headers *will* be authenticated.
    :parameter alg: The algorithm to use to produce the signature.
    :rtype: :class:`~jose.JWS`
    """
    (hash_fn, _), mod = JWA[alg]
    header = dict(add_header or {}, alg=alg)
    header, payload = map(b64encode_url, map(json_encode, (header, claims)))

    sig = b64encode_url(
        hash_fn(_jws_hash_str(header, payload), jwk['k'], mod=mod)
    )

    return JWS(header, payload, sig)


def verify(jws, jwk, alg, validate_claims=True, expiry_seconds=None):
    """ Verifies the given :class:`~jose.JWS`

    :param jws: The :class:`~jose.JWS` to be verified.
    :param jwk: A `dict` representing the JWK to use for verification. This
                parameter is algorithm-specific.
    :param alg: The algorithm to verify the signature with.
    :param validate_claims: A `bool` indicating whether or not the `exp`, `iat`
                            and `nbf` claims should be validated. Defaults to
                            `True`.
    :param expiry_seconds: An `int` containing the JWT expiry in seconds, used
                           when evaluating the `iat` claim. Defaults to `None`,
                           which disables `iat` claim validation.
    :rtype: :class:`~jose.JWT`
    :raises: :class:`~jose.Expired` if the JWT has expired
    :raises: :class:`~jose.NotYetValid` if the JWT is not yet valid
    :raises: :class:`~jose.Error` if there is an error decrypting the JWE
    """
    header, payload, sig = map(b64decode_url, jws)
    header = json_decode(header)
    if alg != header['alg']:
        raise Error('Invalid algorithm')

    (_, verify_fn), mod = JWA[header['alg']]

    if not verify_fn(
        _jws_hash_str(jws.header, jws.payload), jwk['k'], sig, mod=mod
    ):
        raise Error('Mismatched signatures')

    claims = json_decode(b64decode_url(jws.payload))
    _validate(claims, validate_claims, expiry_seconds)

    return JWT(header, claims)


def b64decode_url(istr):
    """ JWT Tokens may be truncated without the usual trailing padding '='
        symbols. Compensate by padding to the nearest 4 bytes.
    """
    try:
        return urlsafe_b64decode(istr + b'=' * (4 - (len(istr) % 4)))
    except (TypeError, binascii.Error) as e:
        raise Error('Unable to decode base64: %s' % (e))


def b64encode_url(istr):
    """ JWT Tokens may be truncated without the usual trailing padding '='
        symbols. Compensate by padding to the nearest 4 bytes.
    """
    return urlsafe_b64encode(istr).rstrip(b'=')


def json_encode(x):
    """
    Dict -> Binary
    """
    return ujson.dumps(x).encode()


def json_decode(x):
    """
    Binary -> Dict
    """
    return ujson.loads(x.decode())


def auth_tag(hmac):
    # http://tools.ietf.org/html/
    # draft-ietf-oauth-json-web-token-19#section-4.1.4
    return hmac[:len(hmac) // 2]


def pad_pkcs7(s):
    sz = AES.block_size - (len(s) % AES.block_size)
    return s + (struct.Struct(">B").pack(sz) * sz)


def unpad_pkcs7(s):
    return s[:-s[-1]]


def encrypt_oaep(plaintext, jwk):
    return PKCS1_OAEP.new(RSA.importKey(jwk['k'])).encrypt(plaintext)


def decrypt_oaep(ciphertext, jwk):
    try:
        return PKCS1_OAEP.new(RSA.importKey(jwk['k'])).decrypt(ciphertext)
    except ValueError as e:
        raise Error(e.args[0])


def hmac_sign(s, key, mod=SHA256):
    hmac = HMAC.new(key, digestmod=mod)
    hmac.update(s)
    return hmac.digest()


def hmac_verify(s, key, sig, mod=SHA256):
    hmac = HMAC.new(key, digestmod=mod)
    hmac.update(s)

    if not const_compare(hmac.digest(), sig):
        return False

    return True


def rsa_sign(s, key, mod=SHA256):
    key = RSA.importKey(key)
    hash = mod.new(s)
    return PKCS1_v1_5_SIG.new(key).sign(hash)


def rsa_verify(s, key, sig, mod=SHA256):
    key = RSA.importKey(key)
    hash = mod.new(s)
    return PKCS1_v1_5_SIG.new(key).verify(hash, sig)


def encrypt_aescbc(plaintext, key, iv):
    plaintext = pad_pkcs7(plaintext)
    return AES.new(key, AES.MODE_CBC, iv).encrypt(plaintext)


def decrypt_aescbc(ciphertext, key, iv):
    return unpad_pkcs7(AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext))


def const_compare(stra, strb):
    if len(stra) != len(strb):
        return False

    res = 0
    for a, b in zip(stra, strb):
        res |= a ^ b
    return res == 0


class _JWA(object):
    """ Represents the implemented algorithms

    A big TODO list can be found here:
    http://tools.ietf.org/html/draft-ietf-jose-json-web-algorithms-24
    """
    _impl = {
        'HS256': ((hmac_sign, hmac_verify), SHA256),
        'HS384': ((hmac_sign, hmac_verify), SHA384),
        'HS512': ((hmac_sign, hmac_verify), SHA512),
        'RS256': ((rsa_sign, rsa_verify), SHA256),
        'RS384': ((rsa_sign, rsa_verify), SHA384),
        'RS512': ((rsa_sign, rsa_verify), SHA512),
        'RSA-OAEP': ((encrypt_oaep, decrypt_oaep), 2048),

        'A128CBC': ((encrypt_aescbc, decrypt_aescbc), 128),
        'A192CBC': ((encrypt_aescbc, decrypt_aescbc), 192),
        'A256CBC': ((encrypt_aescbc, decrypt_aescbc), 256),
    }

    def __getitem__(self, key):
        """ Derive implementation(s) from key
        """
        if key in self._impl:
            return self._impl[key]

        enc, hash = self._compound_from_key(key)
        return self._impl[enc], self._impl[hash]

    def _compound_from_key(self, key):
        try:
            enc, hash = key.split('+')
            return enc, hash
        except ValueError:
            pass

        try:
            enc, hash = key.split('-')
            return enc, hash
        except ValueError:
            pass

        raise Error('Unsupported algorithm: {}'.format(key))


JWA = _JWA()


COMPRESSION = {
    'DEF': (zlib.compress, zlib.decompress),
}


def _format_timestamp(ts):
    dt = datetime.datetime.utcfromtimestamp(ts)
    return dt.isoformat() + 'Z'


def _check_expiration_time(now, expiration_time):
    # Token is valid when nbf <= now < exp
    if now >= expiration_time:
        raise Expired('Token expired at {}'.format(
            _format_timestamp(expiration_time))
        )


def _check_not_before(now, not_before):
    # Token is valid when nbf <= now < exp
    if not_before > now:
        raise NotYetValid('Token not valid until {}'.format(
            _format_timestamp(not_before))
        )


def _validate(claims, validate_claims, expiry_seconds):
    """ Validate expiry related claims.

    If validate_claims is False, do nothing.

    Otherwise, validate the exp and nbf claims if they are present, and
    validate the iat claim if expiry_seconds is provided.
    """
    if not validate_claims:
        return

    now = time()

    # TODO: implement support for clock skew

    # The exp (expiration time) claim identifies the expiration time on or
    # after which the JWT MUST NOT be accepted for processing. The
    # processing of the exp claim requires that the current date/time MUST
    # be before the expiration date/time listed in the exp claim.
    try:
        expiration_time = claims[CLAIM_EXPIRATION_TIME]
    except KeyError:
        pass
    else:
        _check_expiration_time(now, expiration_time)

    # The iat (issued at) claim identifies the time at which the JWT was
    # issued. This claim can be used to determine the age of the JWT.
    # If expiry_seconds is provided, and the iat claims is present,
    # determine the age of the token and check if it has expired.
    try:
        issued_at = claims[CLAIM_ISSUED_AT]
    except KeyError:
        pass
    else:
        if expiry_seconds is not None:
            _check_expiration_time(now, issued_at + expiry_seconds)

    # The nbf (not before) claim identifies the time before which the JWT
    # MUST NOT be accepted for processing. The processing of the nbf claim
    # requires that the current date/time MUST be after or equal to the
    # not-before date/time listed in the nbf claim.
    try:
        not_before = claims[CLAIM_NOT_BEFORE]
    except KeyError:
        pass
    else:
        _check_not_before(now, not_before)


def _jwe_hash_str(ciphertext, iv, adata=b'', version=_TEMP_VER):
    # http://tools.ietf.org/html/
    # draft-ietf-jose-json-web-algorithms-24#section-5.2.2.1
    # Both tokens without version and with version 1 should be ignored in
    # the future as they use incorrect hashing. The version parameter
    # should also be removed.
    if not version:
        return b'.'.join(
            (adata, iv, ciphertext, str(len(adata)).encode('latin-1'))
        )
    elif version == 1:
        return b'.'.join(
            (adata, iv, ciphertext, pack("!Q", len(adata) * 8))
        )
    return b''.join(
        (adata, iv, ciphertext, pack("!Q", len(adata) * 8))
    )


def _jws_hash_str(header, claims):
    return b'.'.join((header, claims))
