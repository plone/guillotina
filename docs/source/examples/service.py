from guillotina import configure

@configure.service(name='@foobar')
async def foobar(context, request):
    return {"foo": "bar"}
