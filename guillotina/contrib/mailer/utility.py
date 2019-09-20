# -*- coding: utf-8 -*-
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from guillotina import app_settings
from guillotina import configure
from guillotina.component import query_utility
from guillotina.contrib.mailer import encoding
from guillotina.contrib.mailer.exceptions import NoEndpointDefinedException
from guillotina.interfaces import IMailEndpoint
from guillotina.interfaces import IMailer
from guillotina.utils import get_random_string
from html2text import html2text
from zope.interface import implementer

import aiosmtplib
import asyncio
import logging
import socket
import time


logger = logging.getLogger(__name__)


@configure.utility(provides=IMailEndpoint, name="smtp")
class SMTPMailEndpoint(object):
    def __init__(self):
        self.settings = {}
        self.conn = None
        self.queue = asyncio.Queue()
        self._exceptions = None

    def from_settings(self, settings):
        self.settings = settings

    async def connect(self):
        try:
            self.conn = aiosmtplib.SMTP(self.settings["host"], self.settings["port"])
            await self.conn.connect()
            if "username" in self.settings:
                await self.conn.login(self.settings["username"], self.settings["password"])
            if "tls" in self.settings and self.settings["tls"]:
                await self.conn.starttls()
        except Exception:
            logger.error("Error connecting to smtp server", exc_info=True)

    async def initialize(self):
        await self.connect()
        while True:
            got_obj = False
            reschedule = False
            try:
                tries, args = await self.queue.get()
                got_obj = True
                try:
                    await self.conn.sendmail(*args)
                except Exception:
                    reschedule = True
                    logger.error(
                        "Error sending mail {} times, retrying again".format(tries + 1), exc_info=True
                    )
            except RuntimeError:
                # just dive out here.
                return
            except (KeyboardInterrupt, MemoryError, SystemExit, asyncio.CancelledError):
                self._exceptions = True
                raise
            except Exception:  # noqa
                self._exceptions = True
                logger.error("Worker call failed", exc_info=True)
            finally:
                if got_obj:
                    self.queue.task_done()
                if reschedule:
                    if tries < 20:
                        # reschedule means there was an error,
                        # pause for a bit in case there is a problem...
                        await asyncio.sleep(1)
                        await self.connect()
                        await self.queue.put((tries + 1, args))

    async def send(self, sender, recipients, message):
        await self.queue.put((0, (sender, recipients, message.as_bytes())))


@implementer(IMailer)
class MailerUtility:
    def __init__(self, settings=None, loop=None):
        self._settings = settings or {}
        self._endpoints = {}
        self.loop = loop

    @property
    def settings(self):
        settings = app_settings.get("mailer", {})
        settings.update(self._settings.get("mailer", {}))
        return settings

    def get_endpoint(self, endpoint_name):
        """
        handle sending the mail
        right now, only support for smtp
        """
        if endpoint_name not in self._endpoints:
            settings = self.settings["endpoints"][endpoint_name]
            utility = query_utility(IMailEndpoint, name=settings["type"])
            if utility is None:
                if len(self._endpoints) > 0:
                    fallback = list(self.endpoints.keys())[0]
                    logger.warn(
                        'Endpoint "{}" not configured. Falling back to "{}"'.format(  # noqa
                            endpoint_name, fallback
                        )
                    )
                    return self._endpoints[endpoint_name]
                else:
                    raise NoEndpointDefinedException("{} mail endpoint not defined".format(endpoint_name))
            utility.from_settings(settings)
            asyncio.ensure_future(utility.initialize())
            self._endpoints[endpoint_name] = utility
        return self._endpoints[endpoint_name]

    async def _send(self, sender, recipients, message, endpoint_name="default"):
        endpoint = self.get_endpoint(endpoint_name)
        return await endpoint.send(sender, recipients, message)

    def build_message(self, message, text=None, html=None):
        if not text and html and self.settings.get("use_html2text", True):
            try:
                text = html2text(html)
            except Exception:
                pass

        if text is not None:
            message.attach(MIMEText(text, "plain"))
        if html is not None:
            message.attach(MIMEText(html, "html"))

    def get_message(
        self, recipient, subject, sender, message=None, text=None, html=None, message_id=None, attachments=[]
    ):
        if message is None:
            message = MIMEMultipart("alternative")
            self.build_message(message, text, html)

        message["Subject"] = subject
        message["From"] = sender
        message["To"] = recipient
        if message_id is not None:
            message["Message-Id"] = message_id
        else:
            message["Message-Id"] = self.create_message_id()

        for attachment in attachments:
            message.attach(attachment)

        return message

    async def send(
        self,
        recipient=None,
        subject=None,
        message=None,
        text=None,
        html=None,
        sender=None,
        message_id=None,
        endpoint="default",
        priority=3,
        attachments=[],
    ):
        if sender is None:
            sender = self.settings.get("default_sender")
        message = self.get_message(
            recipient, subject, sender, message, text, html, message_id=message_id, attachments=attachments
        )
        encoding.cleanup_message(message)
        if message["Date"] is None:
            message["Date"] = formatdate()
        await self._send(sender, recipient, message, endpoint)

    def create_message_id(self, _id=""):
        domain = self.settings["domain"]
        if domain is None:
            domain = socket.gethostname()
        if not _id:
            _id = "%s-%s" % (str(time.time()), get_random_string(20))
        return "<%s@%s>" % (_id, domain)

    async def initialize(self, app):
        """
        No implementation necessary
        """

    async def finalize(self):
        """
        No implementation necessary
        """


@implementer(IMailer)
class PrintingMailerUtility(MailerUtility):
    def __init__(self, settings=None, loop=None):
        self._queue = asyncio.Queue(loop=loop)
        self._settings = settings or {}

    async def _send(self, sender, recipients, message, endpoint_name="default"):
        print("DEBUG MAILER({}): \n {}".format(endpoint_name, message.as_string()))


@implementer(IMailer)
class TestMailerUtility(MailerUtility):
    def __init__(self, settings=None, loop=None):
        self._queue = asyncio.Queue(loop=loop)
        self.mail = []

    async def send(
        self,
        recipient=None,
        subject=None,
        message=None,
        text=None,
        html=None,
        sender=None,
        message_id=None,
        endpoint="default",
        priority=3,
        immediate=False,
        attachments=[],
    ):
        self.mail.append(
            {
                "subject": subject,
                "sender": sender,
                "recipient": recipient,
                "message": message,
                "text": text,
                "html": html,
                "message_id": message_id,
                "endpoint": endpoint,
                "immediate": immediate,
                "attachments": attachments,
            }
        )
