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
from guillotina.component._api import handle
from guillotina.component._declaration import adapter
from guillotina.component.interfaces import IAdapterRegistration
from guillotina.component.interfaces import IHandlerRegistration
from guillotina.component.interfaces import IRegistrationEvent
from guillotina.component.interfaces import ISubscriptionAdapterRegistration
from guillotina.component.interfaces import IUtilityRegistration


@adapter(IUtilityRegistration, IRegistrationEvent)
def dispatch_utility_registration_event(registration, event):
    handle(registration.component, event)
# provide_adapter(dispatch_utility_registration_event)


@adapter(IAdapterRegistration, IRegistrationEvent)
def dispatch_adapter_registration_event(registration, event):
    handle(registration.factory, event)


@adapter(ISubscriptionAdapterRegistration, IRegistrationEvent)
def dispatch_subscription_adapter_registration_event(registration, event):
    handle(registration.factory, event)


@adapter(IHandlerRegistration, IRegistrationEvent)
def dispatch_handler_registration_event(registration, event):
    handle(registration.handler, event)
