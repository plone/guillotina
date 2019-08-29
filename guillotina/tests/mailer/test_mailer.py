from guillotina.interfaces import IMailer
from guillotina.component import get_utility

import pytest


pytestmark = pytest.mark.asyncio


@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.mailer"],
        "mailer": {"utility": "guillotina.contrib.mailer.utility.TestMailerUtility"},
    }
)
async def test_send_mail(guillotina_main, event_loop):

    util = get_utility(IMailer)
    await util.send(
        recipient="me@you.hi",
        subject="Test Mail",
        message="Good mail",
        text="Good mail",
        html="<h1>Good mail</h1>",
        sender=None,
        message_id=None,
        endpoint="default",
        priority=3,
        immediate=False,
        attachments=[],
    )

    assert util.mail[0]["subject"] == "Test Mail"
