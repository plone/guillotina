from guillotina import configure


@configure.service(method='POST', name='@foobar',
                   permission='guillotina.AccessContent')
async def example_service(self):
    return {
        'foo': 'bar'
    }
