# -*- coding: utf-8 -*-
from plone.jsonserializer.interfaces import ISerializeToJson
from plone.jsonserializer.interfaces import IDeserializeFromJson
from plone.server.api.service import Service
from plone.server.registry import ICors
from plone.server.browser import get_physical_path
from zope.component import getMultiAdapter
from plone.server.browser import Response
from plone.server.browser import ErrorResponse
from plone.server.browser import UnauthorizedResponse
from plone.server import _
import fnmatch
from zope.security import checkPermission
from zope.security.interfaces import Unauthorized
from plone.dexterity.utils import createContentInContainer
from zope.component import queryMultiAdapter
import traceback
from datetime import datetime
import logging
from random import randint
from plone.jsonserializer.exceptions import DeserializationError
from plone.server.utils import get_authenticated_user_id



logger = logging.getLogger(__name__)


class DefaultGET(Service):
    async def __call__(self):
        serializer = getMultiAdapter(
            (self.context, self.request),
            ISerializeToJson)
        return serializer()
