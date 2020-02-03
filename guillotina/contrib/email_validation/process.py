

from guillotina.interfaces import IMailer
from guillotina.contrib.email_validation.interfaces import IValidationSettings
from guillotina.contrib.email_validation.utils import generate_validation_token
from guillotina.contrib.email_validation.utils import extract_validation_token
from guillotina.contrib.templates.interfaces import IJinjaUtility
from guillotina.utils import resolve_dotted_name
from guillotina.component import get_utility
from guillotina.utils import get_registry
from guillotina import app_settings
from guillotina.event import notify
from guillotina.events import ValidationEvent


async def start(
        as_user: str,
        email: str,
        from_user: str,
        task_description: str,
        task_id: str,
        redirect_url=None,
        context_description=None,
        ttl=3660,
        data=None):
    # from_user will be mostly anonymous
    registry = await get_registry()
    config = registry.for_interface(IValidationSettings)
    if config is None:
        raise HTTP

    util = get_utility(IMailer)
    if util is None:
        raise HTTPServiceUnavailable("Mail service")

    template_name = config['validation_template']
    site_url = config['site_url']
    validate_url = config['validation_url']

    render_util = get_utility(IJinjaUtility)
    if render_util is None:
        raise HTTPServiceUnavailable("Template render")

    if data is None:
        data = {}

    data.update({
        'v_user': as_user,
        'v_querier': from_user,
        'v_task': task_id,
        'v_redirect_url': redirect_url
    })

    token, last_date = await generate_validation_token(data, ttl=ttl)

    link = f"{site_url}{validate_url}/{token}"
    template = await render_util.render(
        template_name,
        context_description=context_description,
        link=link,
        last_date=last_date,
        task=task_description
    )
    await util.send(
        recipient=email,
        subject=task_description,
        html=template
    )


async def finish(token: str, payload=None):
    data = await extract_validation_token(token)
    
    action = data.get('v_task')
    if action in app_settings['validation_tasks']:
        task = resolve_dotted_name(app_settings['validation_tasks'][action])

        result = await task.run(data, payload)
    else:
        raise HTTPNotImplemented("Invalid task")
    await notify(ValidationEvent(data))
    return result