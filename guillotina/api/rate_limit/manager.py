from guillotina.api.rate_limit.utils import get_rate_limit_state_manager
from guillotina.utils.auth import get_authenticated_user_id
from guillotina.response import HTTPTooManyRequests
from guillotina import configure
from guillotina.interfaces import IRateLimitManager
from guillotina.interfaces import IView
from guillotina.interfaces import ILocation


@configure.adapter(
    for_=IView,
    provides=IRateLimitManager)
class ServiceRateLimitManager:
    def __init__(self, context):
        self.service = context
        self.state_manager = get_rate_limit_state_manager()
        self.user = get_authenticated_user_id(self.service.request)

    @property
    def key(self):
        context_id = self.service.context.id
        service_method = self.service.request.method
        service_name = self.service.__route__.view_name
        return f'{service_method} {context_id}/{service_name}'

    @property
    def rate_limits(self):
        return getattr(self.service, '__rate_limits')

    async def __call__(self):
        """This is called before the increment, so we need to check wether
        this request will exceed the limit.
        """
        max_count = self.rate_limits['hits']
        current_count = await self.state_manager.get_count(self.user, self.key)
        if current_count + 1 > max_count:
            # Exceeded
            remaining_time = await self.state_manager.get_remaining_time(self.user, self.key)
            resp = HTTPTooManyRequests(content={'reason': 'Rate limit exceeded'})
            resp.headers['Retry-After'] = str(remaining_time)
            raise resp
        else:
            # Not exceeded, just increment request count
            await self.state_manager.increment(self.user, self.key)

            # Set expiration if needed
            if not current_count:
                expiration = self.rate_limits['seconds']
                await self.state_manager.expire_after(self.user, self.key, expiration)
