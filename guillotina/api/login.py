# -*- encoding: utf-8 -*-
from datetime import datetime
from datetime import timedelta

import jwt
from guillotina import app_settings
from guillotina import configure
from guillotina.api.service import Service
from guillotina.auth import authenticate_user
from guillotina.event import notify
from guillotina.events import UserLogin
from guillotina.events import UserRefreshToken
from guillotina.interfaces import IContainer
from guillotina.interfaces import IApplication
from guillotina.response import HTTPUnauthorized
from guillotina.utils import get_authenticated_user


@configure.service(
    context=IContainer, method='POST',
    permission='guillotina.Public', name='@login',
    summary='Components for a resource', allow_access=True)
@configure.service(
    context=IApplication, method='POST',
    permission='guillotina.Public', name='@login',
    summary='Components for a resource', allow_access=True)
class Login(Service):

    async def __call__(self):
        data = await self.request.json()
        creds = {
            'type': 'basic',
            'token': data['password'],
            'id': data.get('username', data.get('login'))
        }

        for validator in app_settings['auth_token_validators']:
            if (validator.for_validators is not None and
                    'basic' not in validator.for_validators):
                continue
            user = await validator(self.request).validate(creds)
            if user is not None:
                break

        if user is None:
            raise HTTPUnauthorized(content={
                'text': 'login failed'
            })

        jwt_token, data = authenticate_user(user.id)
        await notify(UserLogin(user, jwt_token))

        return {
            'exp': data['exp'],
            'token': jwt_token
        }


@configure.service(
    context=IContainer, method='POST',
    permission='guillotina.AccessContent', name='@login-renew',
    summary='Refresh to a new token')
@configure.service(
    context=IApplication, method='POST',
    permission='guillotina.AccessContent', name='@login-renew',
    summary='Refresh to a new token')
class Refresh(Service):
    token_timeout = 60 * 60 * 1

    async def __call__(self):
        user = get_authenticated_user(self.request)
        data = {
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(seconds=self.token_timeout),
            'id': user.id
        }
        jwt_token = jwt.encode(
            data, app_settings['jwt']['secret'],
            algorithm=app_settings['jwt']['algorithm']).decode('utf-8')

        await notify(UserRefreshToken(user, jwt_token))

        return {
            'exp': data['exp'],
            'token': jwt_token
        }
