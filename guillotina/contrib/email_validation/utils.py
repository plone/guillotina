from datetime import datetime
from guillotina import app_settings
from guillotina.utils import get_jwk_key
from jwcrypto import jwe
from jwcrypto.common import json_encode

import logging
import orjson
import pytz
import time


logger = logging.getLogger("guillotina.email_validation")


async def generate_validation_token(data, ttl=3660):
    data = data or {}
    claims = {
        "iat": int(time.time()),
        "exp": int(time.time() + ttl),
    }
    claims.update(data)
    payload = orjson.dumps(claims)
    jwetoken = jwe.JWE(payload, json_encode({"alg": "A256KW", "enc": "A256CBC-HS512"}))
    jwetoken.add_recipient(get_jwk_key())
    token = jwetoken.serialize(compact=True)

    last_time = time.time() + ttl
    datetime_format = app_settings.get("datetime_format")
    default_timezone = app_settings.get("default_timezone", "UTC")
    tz = pytz.timezone(default_timezone)

    if datetime_format is None:
        last_date = datetime.fromtimestamp(last_time, tz=tz).isoformat()
    else:
        last_date = datetime.fromtimestamp(last_time, tz=tz).strftime(datetime_format)
    return token, last_date


async def extract_validation_token(jwt_token):
    try:
        jwetoken = jwe.JWE()
        jwetoken.deserialize(jwt_token)
        jwetoken.decrypt(get_jwk_key())
        payload = jwetoken.payload
    except jwe.InvalidJWEOperation:
        logger.warn(f"Invalid operation", exc_info=True)
        return
    except jwe.InvalidJWEData:
        logger.warn(f"Error decrypting JWT token", exc_info=True)
        return
    json_payload = orjson.loads(payload)
    if json_payload["exp"] <= int(time.time()):
        logger.warning(f"Expired token {jwt_token}", exc_info=True)
        return
    return json_payload
