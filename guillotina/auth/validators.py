from concurrent.futures import ThreadPoolExecutor
from functools import partial
from guillotina import configure
from guillotina._settings import app_settings
from guillotina.auth import find_user
from guillotina.component import get_utility
from guillotina.component import query_utility
from guillotina.interfaces import IApplication
from guillotina.interfaces import IPasswordChecker
from guillotina.interfaces import IPasswordHasher
from guillotina.utils import strings_differ
from lru import LRU

import argon2
import asyncio
import hashlib
import jwt
import logging
import uuid


ph = argon2.PasswordHasher()
_pw_auth_validator = LRU(100)

logger = logging.getLogger("guillotina")


class BaseValidator:
    for_validators = None


@configure.utility(provides=IPasswordHasher, name="argon2")
def argon2_pw_hasher(pw, salt):
    return ph.hash(pw + salt)


@configure.utility(provides=IPasswordChecker, name="argon2")
def argon2_password_checker(token, password):
    split = token.split(":")
    if len(split) != 3:
        return False
    salt = split[1]
    hashed = split[2]
    try:
        return ph.verify(hashed, password + salt)
    except (argon2.exceptions.InvalidHash, argon2.exceptions.VerifyMismatchError):
        return False


@configure.utility(provides=IPasswordHasher, name="sha512")
def sha512_pw_hasher(pw, salt):
    return hashlib.sha512(pw + salt).hexdigest()


@configure.utility(provides=IPasswordChecker, name="sha512")
def hash_password_checker(token, password):
    split = token.split(":")
    if len(split) != 3:
        return False
    algorithm = split[0]
    salt = split[1]
    return not strings_differ(hash_password(password, salt, algorithm), token)


def hash_password(password, salt=None, algorithm="argon2"):
    if salt is None:
        salt = uuid.uuid4().hex

    if isinstance(salt, str):
        salt = salt.encode("utf-8")

    if isinstance(password, str):
        password = password.encode("utf-8")

    hash_func = get_utility(IPasswordHasher, name=algorithm)
    hashed_password = hash_func(password, salt)
    return "{}:{}:{}".format(algorithm, salt.decode("utf-8"), hashed_password)


def check_password(token, password):
    cache_key = token + hashlib.sha256(password.encode("utf-8")).hexdigest()
    if cache_key in _pw_auth_validator:
        return _pw_auth_validator[cache_key]
    split = token.split(":")
    if len(split) != 3:
        return False
    algorithm = split[0]
    check_func = query_utility(IPasswordChecker, name=algorithm)
    if check_func is None:
        logger.warning(f"Could not find password checker for {algorithm}")
        return False
    decision = check_func(token, password)
    _pw_auth_validator[cache_key] = decision
    return decision


class SaltedHashPasswordValidator:
    for_validators = ("basic", "wstoken")

    def get_executor(self):
        root = get_utility(IApplication, name="root")
        if not hasattr(root, "_pw_executor"):
            root._pw_executor = ThreadPoolExecutor(max_workers=2)
        return root._pw_executor

    async def validate(self, token):
        user = await find_user(token)
        user_pw = getattr(user, "password", None)
        if not user_pw or ":" not in user_pw or "token" not in token:
            return
        executor = self.get_executor()
        loop = asyncio.get_event_loop()
        if await loop.run_in_executor(executor, partial(check_password, user_pw, token["token"])):
            return user


class JWTValidator:
    for_validators = ("bearer", "wstoken", "cookie")

    async def validate(self, token):
        if token.get("type") not in ("bearer", "wstoken", "cookie"):
            return

        if "." not in token.get("token", ""):
            # quick way to check if actually might be jwt
            return

        try:
            validated_jwt = jwt.decode(
                token["token"], app_settings["jwt"]["secret"], algorithms=[app_settings["jwt"]["algorithm"]]
            )
            token["id"] = validated_jwt["id"]
            token["decoded"] = validated_jwt
            user = await find_user(token)
            if user is not None and user.id == token["id"]:
                return user
        except (jwt.exceptions.DecodeError, jwt.exceptions.ExpiredSignatureError, KeyError):
            pass

        return
