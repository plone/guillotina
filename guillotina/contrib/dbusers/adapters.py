from .content.users import IUserManager
from guillotina import app_settings
from guillotina import configure
from guillotina.interfaces import IIDChecker

import re


# from https://github.com/theskumar/python-usernames/blob/master/usernames/validators.py

username_regex = re.compile(
    r"""
    ^                       # beginning of string
    (?!_$)                  # no only _
    (?![-.])                # no - or . at the beginning
    (?!.*[_.-]{2})          # no __ or _. or ._ or .. or -- inside
    [a-z0-9@_.-]+           # allowed characters, atleast one must be present
    (?<![.-])               # no - or . at the end
    $                       # end of string
    """,
    re.X,
)

reserved_words = ["root", "admin", "manager", "user"]


@configure.adapter(for_=IUserManager, provides=IIDChecker)
class UserIdChecker:
    def __init__(self, context):
        self.context = context

    async def __call__(self, id_, *_):
        if not re.match(username_regex, id_):
            return False
        if id_ in reserved_words:
            return False
        if len(id_) < app_settings["min_username_length"]:
            return False
        return True
