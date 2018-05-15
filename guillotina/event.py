from guillotina.component.event import async_subscribers
from guillotina.component.event import sync_subscribers


async def notify(event):
    """Notify all subscribers of ``event``."""
    for subscriber in async_subscribers:
        await subscriber(event)


def sync_notify(event):
    """Notify all subscribers of ``event``."""
    for subscriber in sync_subscribers:
        subscriber(event)
