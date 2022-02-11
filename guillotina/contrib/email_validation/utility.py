from guillotina import app_settings
from guillotina.component import get_utility
from guillotina.contrib.email_validation.interfaces import IValidationSettings
from guillotina.contrib.email_validation.utils import extract_validation_token
from guillotina.contrib.email_validation.utils import generate_validation_token
from guillotina.contrib.templates.interfaces import IJinjaUtility
from guillotina.event import notify
from guillotina.events import ValidationEvent
from guillotina.interfaces import IMailer
from guillotina.response import HTTPNotImplemented
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPServiceUnavailable
from guillotina.response import HTTPUnauthorized
from guillotina.utils import get_registry
from guillotina.utils import resolve_dotted_name
from jsonschema import validate as jsonvalidate
from jsonschema.exceptions import ValidationError

import logging


logger = logging.getLogger("guillotina.email_validation")


class EmailValidationUtility:
    def __init__(self, settings):
        pass

    async def initialize(self, app=None):
        pass

    async def finalize(self):
        pass

    async def start(
        self,
        as_user: str,
        email: str,
        from_user: str,
        task_description: str,
        task_id: str,
        redirect_url=None,
        context_description=None,
        ttl=3660,
        data=None,
        render_options={},
    ):
        # from_user will be mostly anonymous
        registry = await get_registry()
        if registry is None:
            logger.error("No registry")
            raise HTTPServiceUnavailable()

        config = registry.for_interface(IValidationSettings)
        if config is None:
            logger.error("No configuration on registry")
            raise HTTPServiceUnavailable()

        util = get_utility(IMailer)
        if util is None:
            logger.error("No mail service configured")
            raise HTTPServiceUnavailable()

        template_name = config["validation_template"]
        site_url = config["site_url"]
        validate_url = config["validation_url"]
        from_email = config["site_mails_from"]

        render_util = get_utility(IJinjaUtility)
        if render_util is None:
            logger.error("Template render not enabled")
            raise HTTPServiceUnavailable()

        if task_id not in app_settings["auth_validation_tasks"]:
            logger.error(f"Task {task_id} unavailable")
            raise HTTPServiceUnavailable()

        custom_template = app_settings["auth_validation_tasks"][task_id].get("custom_template")
        if custom_template is not None:
            template_name = custom_template

        custom_validate_url = app_settings["auth_validation_tasks"][task_id].get("custom_validate_url")
        if custom_validate_url is not None:
            validate_url = custom_validate_url

        if data is None:
            data = {}

        data.update(
            {"v_user": as_user, "v_querier": from_user, "v_task": task_id, "v_redirect_url": redirect_url}
        )
        ttl = app_settings.get("ttl_email_validation", ttl)

        token, last_date = await generate_validation_token(data, ttl=ttl)

        link = f"{site_url}{validate_url}?token={token}"
        template = await render_util.render(
            template_name,
            context_description=context_description,
            link=link,
            last_date=last_date,
            task=task_description,
            **render_options,
        )
        await util.send(recipient=email, sender=from_email, subject=task_description, html=template)

    async def schema(self, token: str):
        data = await extract_validation_token(token)

        action = data.get("v_task")
        if action in app_settings["auth_validation_tasks"]:
            return app_settings["auth_validation_tasks"][action]["schema"]
        else:
            return None

    async def finish(self, token: str, payload=None):
        data = await extract_validation_token(token)
        if data is None:
            raise HTTPUnauthorized()

        action = data.get("v_task")
        if action in app_settings["auth_validation_tasks"]:
            if "schema" in app_settings["auth_validation_tasks"][action]:
                schema = app_settings["auth_validation_tasks"][action]["schema"]

                try:
                    jsonvalidate(instance=payload, schema=schema)
                except ValidationError as e:
                    raise HTTPPreconditionFailed(
                        content={
                            "reason": "json schema validation error",
                            "message": e.message,
                            "validator": e.validator,
                            "validator_value": e.validator_value,
                            "path": [i for i in e.path],
                            "schema_path": [i for i in e.schema_path],
                            "schema": schema,
                        }
                    )

            task = resolve_dotted_name(app_settings["auth_validation_tasks"][action]["executor"])

            result = await task.run(data, payload)
        else:
            logger.error(f"Invalid task {action}")
            raise HTTPNotImplemented()
        await notify(ValidationEvent(data))
        return result
