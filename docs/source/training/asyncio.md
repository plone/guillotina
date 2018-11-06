# AsyncIO

Python’s asyncio library allows you to run single threaded "concurrent"
code using coroutines inside an event loop.

The event loop is designed for I/O over sockets and other resources,
it is especially good for working with client/server network connections.

Python >= 3.4(best features and performance in 3.6)

## Explanation

### Benefits

The event loop allows you to handle a larger number of network connections at once.

No network blocks, so you can have long running connections with very little performance
impact (HTML5 sockets for example).


### How web servers are typically designed

- (Pyramid, Flash, Plone, etc)
- Processes X Threads = Total number of concurrent connections that can be handled at once.
- Client makes a request to web server, request is assigned thread, thread handle request and sends response
- If no threads available, request is blocked, waiting for an open thread
- Threads are expensive (CPU), Processes are expensive on RAM


### How it works with AsyncIO

- All requests are thrown on thread loop
- Since we don’t block on network traffic, we can juggle many requests at the same time
- Modern web application servers connect with many different services that can
  potentially block on network traffic — BAD
- Limiting factor is maxed out CPU, not costly thread switching between requests — GOOD


### Where is network traffic used?

- Web Client/App Server
- App Server/Database
- App Server/Caching(redis)
- App Server/OAUTH
- App Server/Cloud storage
- App Server/APIs(gdrive, m$, slack, etc)


### Implementation details

In order to benefit, the whole stack needs to be asyncio-aware.

Anywhere in your application server that is not and does network traffic
WILL BLOCK all other connections while it is doing its network traffic
(example: using the `requests` library instead of `aiohttp`)


## Basics

Get active event loop or create new one

Run coroutine inside event loop with `asyncio.run_until_complete`


```python
import asyncio


async def hello():
    print('hi')


event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(hello())
```

## Basics(2)

`asyncio.run_until_complete` automatically wraps your coroutine into a Future
object and waits for it to finish.

`asyncio.ensure_future` will wrap a coroutine in a future and return it to you

So you can schedule multiple coroutines that can run at the same time

```python
import asyncio


async def hello1():
    await asyncio.sleep(0.5)
    print('hi 1')


async def hello2():
    print('hi 2')


event_loop = asyncio.get_event_loop()
future1 = asyncio.ensure_future(hello1(), loop=event_loop)
future2 = asyncio.ensure_future(hello2(), loop=event_loop)
event_loop.run_until_complete(future2)
event_loop.run_until_complete(future1)
```


## Long running tasks

You can also schedule long running tasks on the event loop.

The tasks can run forever…

“Task” objects are the same as “Future” objects(well, close)

```python
import asyncio
import random


async def hello_many():
    while True:
        number = random.randint(0, 3)
        await asyncio.sleep(number)
        print('Hello {}'.format(number))


event_loop = asyncio.get_event_loop()
task = asyncio.Task(hello_many())
print('task running now...')
event_loop.run_until_complete(asyncio.sleep(10))
print('we waited 10 seconds')
task.cancel()
print('task cancelled')
```


## ALL YOUR ASYNC BELONGS TO US

**gotcha**

If you want part of your code to be async(say a function), the complete stack of
the caller must be async and running on the event loop.


```python
import asyncio


async def print_foobar1():
    print('foobar1')


async def print_foobar2():
    print('foobar2')


async def foobar():
    await print_foobar1()
    print_foobar2()  # won't work, never awaited


event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(foobar())
print_foobar1()  # won't work, never awaited
# await print_foobar1()  # error, not running in event loop
```


## "multi" processing

AsyncIO isn't really multiprocessing but it gives you the illusion of it.

A simple example can be shown with the `asyncio.gather` function.

```python
import asyncio
import aiohttp


async def download_url(url):
    async with aiohttp.ClientSession() as session:
        resp = await session.get(url)
        text = await resp.text()
        print(f'Downloaded {url}, size {len(text)}')


event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(asyncio.gather(
    download_url('https://www.google.com'),
    download_url('https://www.facebook.com'),
    download_url('https://www.twitter.com'),
    download_url('https://www.stackoverflow.com')
))
```


## asyncio loops

Using `yield` with loops allows you to "give up" execution on every iteration of the loop.

```python
import asyncio


async def yielding():
    for idx in range(5):
        print(f'Before yield {idx}')
        yield idx


async def foobar2():
    async for idx in yielding():
        print(f"Yay, I've been yield'd {idx}")


event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(foobar2())
```


## Scheduling


`loop.call_later`: arrange to call on a delay
`loop.call_at`: arrange function to be called at specified time


## Executors

An executor is available to use when you have non-async code that needs to be made async.

A typical executor is a thread executor. This means, anything you run in an executor
is being thrown in a thread to run.

It’s worse to have non-async code than to use thread executors.

Executors are also good for CPU bound code.

```python
import asyncio
import requests
import concurrent.futures


def download_url(url):
    resp = requests.get(url)
    text = resp.content
    print(f'Downloaded {url}, size {len(text)}')


async def foobar():
    print('foobar')


executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(asyncio.gather(
    event_loop.run_in_executor(executor, download_url, 'https://www.google.com'),
    event_loop.run_in_executor(executor, download_url, 'https://www.facebook.com'),
    event_loop.run_in_executor(executor, download_url, 'https://www.twitter.com'),
    event_loop.run_in_executor(executor, download_url, 'https://www.stackoverflow.com'),
    foobar()
))
```

## Subprocess

Python also provides a very neat asyncio subprocess module.

```python
import asyncio


async def run_cmd(cmd):
    print(f'Executing: {" ".join(cmd)}')
    process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
    out, error = await process.communicate()
    print(out.decode('utf8'))


event_loop = asyncio.get_event_loop()
event_loop.run_until_complete(asyncio.gather(
    run_cmd(['sleep', '1']),
    run_cmd(['echo', 'hello'])
))
```
