import pytest

from guillotina.component import get_utility
from guillotina.contrib.mailer.utility import MailerUtility
from guillotina.interfaces import IMailer


pytestmark = pytest.mark.asyncio


class CapturingMailerUtility(MailerUtility):
    async def _send(self, sender, recipients, message, endpoint_name="default"):
        self.sender = sender
        self.recipients = recipients
        self.message = message
        self.endpoint_name = endpoint_name


async def test_send_mail_formats_list_address_headers():
    mailer = CapturingMailerUtility(
        {"mailer": {"default_sender": "sender@example.com", "domain": "example.com"}}
    )

    await mailer.send(
        recipient=["primary@example.com", "other@example.com"],
        subject="Test Mail",
        text="Good mail",
        cc=["cc@example.com", "second-cc@example.com"],
    )

    assert mailer.recipients == [
        "primary@example.com",
        "other@example.com",
        "cc@example.com",
        "second-cc@example.com",
    ]
    assert mailer.message["To"] == "primary@example.com, other@example.com"
    assert mailer.message["Cc"] == "cc@example.com, second-cc@example.com"
    assert "To: primary@example.com, other@example.com" in mailer.message.as_string()
    assert "Cc: cc@example.com, second-cc@example.com" in mailer.message.as_string()


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
        attachments=[],
    )

    assert util.mail[0]["subject"] == "Test Mail"


@pytest.mark.app_settings(
    {
        "applications": ["guillotina", "guillotina.contrib.mailer"],
        "mailer": {"utility": "guillotina.contrib.mailer.utility.PrintingMailerUtility"},
    }
)
async def test_send_mail_print(guillotina_main, event_loop):

    util = get_utility(IMailer)
    await util.send(
        recipient="me@you.hi", subject="Test Mail", html="<h1>Good mail</h1>", sender="you@you.hi"
    )
