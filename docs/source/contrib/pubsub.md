# PubSub

`guillotina` provides out of the box pubsub service with redis driver.


## Configuration

```yaml
applications:
- guillotina.contrib.redis
- guillotina.contrib.pubsub
```

## Usage

You can subscribe to channels and define who you are so you make sure that you do not receive the message.

Multiple tasks can subscribe to the same channel and `guillotina` will broadcast all the messages to all tasks.

```python
from guillotina.component import get_utility
from guillotina.interfaces import IPusSubUtility


MY_PROCESS_ID = 'me'

async def callback(*, data=None, sender=None):
    ...


util = get_utility(IPusSubUtility)
await util.subscribe('channel_name', MY_PROCESS_ID, callback)
await util.publish('channel_name', MY_PROCESS_ID, 'mydata')

```