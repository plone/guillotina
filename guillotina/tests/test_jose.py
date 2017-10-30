from Crypto.PublicKey import RSA
from guillotina import jose

import time


key = RSA.generate(2048)
pub_jwk = {'k': key.publickey().exportKey('PEM')}
priv_jwk = {'k': key.exportKey('PEM')}
RSA_TOKEN = {
    'pub': pub_jwk,
    'priv': priv_jwk
}


async def test_encrypt_descrypt():
    claims = {
        'iat': int(time.time()),
        'exp': int(time.time() + 30),
        'token': 'foobar'
    }
    jwe = jose.encrypt(claims, priv_jwk)
    encrypted_token = jose.serialize_compact(jwe)
    jwe = jose.deserialize_compact(encrypted_token)
    jwt = jose.decrypt(jwe, priv_jwk)
    assert jwt.claims == claims


async def test_sign():
    claims = {
        'iat': int(time.time()),
        'exp': int(time.time() + 30),
        'token': 'foobar'
    }
    jws = jose.sign(claims, pub_jwk, alg='HS256')
    jwt = jose.verify(jws, pub_jwk, alg='HS256')
    assert jwt.claims == claims
