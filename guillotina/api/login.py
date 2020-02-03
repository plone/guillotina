# -*- encoding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
from guillotina import app_settings
from guillotina import configure
from guillotina.api.service import Service
from guillotina.auth import authenticate_user
from guillotina.component import get_utility
from guillotina.event import notify
from guillotina.events import UserLogin
from guillotina.events import UserRefreshToken
from guillotina.interfaces import IApplication
from guillotina.interfaces import IContainer
from guillotina.interfaces import IAuthValidationUtility
from guillotina.response import HTTPUnauthorized
from guillotina.response import HTTPPreconditionFailed
from guillotina.utils import get_authenticated_user
from guillotina.auth.recaptcha import RecaptchaValidator
from guillotina.auth.utils import find_user
from json.decoder import JSONDecodeError
import jwt


@configure.service(
    context=IContainer,
    method="POST",
    permission="guillotina.Public",
    name="@login",
    summary="Components for a resource",
    allow_access=True,
)
@configure.service(
    context=IApplication,
    method="POST",
    permission="guillotina.Public",
    name="@login",
    summary="Components for a resource",
    allow_access=True,
)
class Login(Service):
    async def __call__(self):
        data = await self.request.json()
        creds = {"type": "basic", "token": data["password"], "id": data.get("username", data.get("login"))}

        for validator in app_settings["auth_token_validators"]:
            if validator.for_validators is not None and "basic" not in validator.for_validators:
                continue
            user = await validator().validate(creds)
            if user is not None:
                break

        if user is None:
            raise HTTPUnauthorized(content={"text": "login failed"})

        jwt_token, data = authenticate_user(user.id, timeout=app_settings["jwt"]["token_expiration"])
        await notify(UserLogin(user, jwt_token))

        return {"exp": data["exp"], "token": jwt_token}


@configure.service(
    context=IContainer,
    method="POST",
    permission="guillotina.RefreshToken",
    name="@login-renew",
    summary="Refresh to a new token",
    allow_access=True,
)
@configure.service(
    context=IApplication,
    method="POST",
    permission="guillotina.RefreshToken",
    name="@login-renew",
    summary="Refresh to a new token",
    allow_access=True,
)
class Refresh(Service):
    async def __call__(self):
        user = get_authenticated_user()
        data = {
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(seconds=app_settings["jwt"]["token_expiration"]),
            "id": user.id,
        }
        jwt_token = jwt.encode(
            data, app_settings["jwt"]["secret"], algorithm=app_settings["jwt"]["algorithm"]
        ).decode("utf-8")

        await notify(UserRefreshToken(user, jwt_token))

        return {"exp": data["exp"], "token": jwt_token}


@configure.service(
    context=IContainer,
    method="POST",
    permission="guillotina.Logout",
    name="@logout",
    summary="Logout application",
    allow_access=True,
)
@configure.service(
    context=IApplication,
    method="POST",
    permission="guillotina.Logout",
    name="@logout",
    summary="Logout application",
    allow_access=True,
)
class Logout(Service):
    async def __call__(self):
        user = get_authenticated_user()
        try:
            await user.logout(self.request)
        except AttributeError:
            raise HTTPNotAcceptable()

@configure.service(
    context=IContainer,
    name="@users/{user}/reset-password",
    method="POST",
    permission="guillotina.Public",
    responses={
        "200": {
            "description": "Reset password",
        }
    },
    summary="Reset password",
    allow_access=True,
)
class ResetPasswordUsers(Service):
    async def __call__(self):
        user_id: str = self.request.matchdict["user"]
        actual_user = get_authenticated_user()
        if actual_user.id == user_id:
            # Self setting password
            # Payload : {
            #   'old_password': 'secret',
            #   'new_password': 'verysecret',
            # }

            data = await self.request.json()
            try:
                await actual_user.set_password(
                    data.get('new_password', None),
                    old_password=data.get('old_password', None)
                )
            except AttributeError:
                raise HTTPNotAcceptable()
        else:
            # We validate with recaptcha
            validator = RecaptchaValidator()
            status = await validator.validate()
            if status is False:
                raise HTTPUnauthorized(content={"text": "Invalid validation"})

            # We need to validate is a valid user
            user = await find_user({'id': user_id})

            if user is None:
                raise HTTPUnauthorized(content={"text": "Invalid operation"})

            # We need to validate is a valid user
            try:
                email = user.properties.get('email', user.email)
            except AttributeError:
                email = None
            if email is None and '@' in user_id:
                email = user_id

            if email is None:
                raise HTTPPreconditionFailed(
                    content={
                        "reason": "User without mail configured"
                    }
                )

            # We need to generate a token and send to user email
            validation_utility = get_utility(IAuthValidationUtility)
            if validation_utility is not None:
                redirect_url = self.request.query.get('redirect_url', None)
                await validation_utility.start(
                    as_user=user_id,
                    from_user=actual_user.id,
                    email=email,
                    task_description='Reset password',
                    task_id='reset_password',
                    context_description=self.context.title,
                    redirect_url=redirect_url)
            else:
                raise HTTPNotAcceptable()


@configure.service(
    context=IContainer,
    name="@validate_schema/{token}",
    method="POST",
    permission="guillotina.Public",
    responses={
        "200": {
            "description": "Validate operation",
        }
    },
    summary="Validate operation",
    allow_access=True,
)
class ValidateOperation(Service):
    async def __call__(self):
        validation_utility = get_utility(IAuthValidationUtility)
        if validation_utility is not None:
            payload = await validation_utility.schema(token=self.request.matchdict["token"])
            return payload
        else:
            raise HTTPNotAcceptable()


@configure.service(
    context=IContainer,
    name="@validate/{token}",
    method="POST",
    permission="guillotina.Public",
    responses={
        "200": {
            "description": "Validate operation"
        }
    },
    summary="Validate operation",
    allow_access=True,
)
class ValidateOperation(Service):
    async def __call__(self):
        validation_utility = get_utility(IAuthValidationUtility)
        if validation_utility is not None:
            try:
                request_payload = await self.request.json()
            except JSONDecodeError:
                request_payload = None
            payload = await validation_utility.finish(
                token=self.request.matchdict["token"],
                payload=request_payload)
            return payload
        else:
            raise HTTPNotAcceptable()


@configure.service(
    context=IContainer,
    name="@users",
    method="POST",
    permission="guillotina.Public",
    responses={
        "200": {
            "description": "Register a user",
        }
    },
    summary="Register Users",
    allow_access=True,
)
class RegisterUsers(Service):
    async def __call__(self):
        allowed = app_settings.get('allow_register', False)
        if allowed is False:
            raise HTTPUnauthorized(content={"text": "Not allowed registration"})

        validator = RecaptchaValidator()
        status = await validator.validate()
        if status is False:
            raise HTTPUnauthorized(content={"text": "Invalid validation"})

        payload = await self.request.json()

        user_id = payload.get('id', None)
        user = await find_user({'id': user_id})
        if user is not None:
            raise HTTPUnauthorized(content={"text": "Invalid login"})

        validation_utility = get_utility(IAuthValidationUtility)
        if validation_utility is not None:
            redirect_url = self.request.query.get('redirect_url', None)
            username = payload.get('fullname', payload.get('id', ''))
            task_description = f"Registering user {username}"
            actual_user = get_authenticated_user()
            await validation_utility.start(
                as_user=payload.get('id'),
                from_user=actual_user.id,
                task_description=task_description,
                task_id='register_user',
                email=payload.get('email'),
                context_description=self.context.title,
                redirect_url=redirect_url,
                data=payload)
        else:
            raise HTTPNotAcceptable()


@configure.service(
    context=IContainer,
    name="@info",
    method="GET",
    permission="guillotina.Public",
    responses={
        "200": {
            "description": "Get public information about user access",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "register": {"type": "boolean"},
                            "title": {"type": "string"},
                            "social": {"type": "array"},
                        }
                    }
                }
            }
        }
    },
    summary="Info Access",
    allow_access=True,
)
class InfoAccess(Service):
    async def __call__(self):
        validator = RecaptchaValidator()
        status = await validator.validate()
        if status is False:
            raise HTTPUnauthorized(content={"text": "Invalid validation"})

        auth_providers = app_settings.get('auth_providers', {})
        providers = []
        if 'twitter' in auth_providers:
            providers.append('twitter')
        if 'facebook' in auth_providers:
            providers.append('facebook')
        if 'google' in auth_providers:
            providers.append('google')

        return {
            'register': app_settings.get('allow_register', False),
            'social': providers,
            'title': self.context.title
        }