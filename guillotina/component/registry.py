##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
# flake8: noqa
# BBB, import component-related from zope.interface
from zope.interface.registry import Components
from zope.interface.registry import _getUtilityProvided
from zope.interface.registry import _getAdapterProvided
from zope.interface.registry import _getAdapterRequired
from zope.interface.registry import UtilityRegistration
from zope.interface.registry import AdapterRegistration
from zope.interface.registry import SubscriptionRegistration
from zope.interface.registry import HandlerRegistration

from guillotina.component._api import handle
from guillotina.component._declaration import adapter

from guillotina.component.interfaces import IAdapterRegistration
from guillotina.component.interfaces import IHandlerRegistration
from guillotina.component.interfaces import IRegistrationEvent
from guillotina.component.interfaces import ISubscriptionAdapterRegistration
from guillotina.component.interfaces import IUtilityRegistration
from guillotina.component.globalregistry import provideAdapter


@adapter(IUtilityRegistration, IRegistrationEvent)
def dispatchUtilityRegistrationEvent(registration, event):
    handle(registration.component, event)
# provideAdapter(dispatchUtilityRegistrationEvent)


@adapter(IAdapterRegistration, IRegistrationEvent)
def dispatchAdapterRegistrationEvent(registration, event):
    handle(registration.factory, event)


@adapter(ISubscriptionAdapterRegistration, IRegistrationEvent)
def dispatchSubscriptionAdapterRegistrationEvent(registration, event):
    handle(registration.factory, event)


@adapter(IHandlerRegistration, IRegistrationEvent)
def dispatchHandlerRegistrationEvent(registration, event):
    handle(registration.handler, event)
