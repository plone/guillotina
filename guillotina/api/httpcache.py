from zope.interface import Interface


class IHttpCachePolicyUtility(Interface):
    def __call__(context, request):
        """
        Returns a dictionary with the headers to be added on the response
        """


class NoHttpCachePolicyUtility:
    def __init__(self, settings, loop=None):
        pass

    def __call__(self, context, request):
        # No headers in this case
        return None


class SimpleHttpCachePolicyUtility:
    def __init__(self, settings, loop=None):
        self.max_age = settings['max_age']
        self.public = settings.get('public', False)

    def __call__(self, context, request):
        cache_control = f'max-age={self.max_age}'
        publicstr = 'public' if self.public else 'private'
        cache_control += f', {publicstr}'

        return {
            'Cache-Control': cache_control,
            'ETag': context.tid
        }
