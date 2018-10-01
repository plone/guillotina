# Debugging

Debugging Guillotina will be slightly different from other
web application that are not asyncio but Guillotina provides
some nice integration to help you out.

## X-Debug header

Any any request, you can provide the header `X-Debug:1` and
Guillotina will output debugging headers in the response
about timing, number of queries and cache hit/miss stats.


```eval_rst
.. make sure we have a container
.. http:gapi::
   :hidden: yes
   :method: POST
   :path: /db
   :basic_auth: root:root
   :headers: Content-Type:application/json
   :body: {"@type": "Container", "id": "container"}

.. http:gapi::
   :path_spec: /(db)/(container)
   :path: /db/container
   :basic_auth: root:root
   :headers: X-Debug:1
```


## GDEBUG

On startup, you can also provide the environment variable `GDEBUG=true`.
This will provide detailed query statistics with the `X-Debug:1`.


## aiomonitor

Guillotina also provides integration with the `aiomonitor` python module.
This module allows you to attach to a running python with asyncio
to inspect the active tasks running.

First, install aiomonitor:

```bash
pip install aiomonitor
```


Then, run guillotina with `--monitor`:

```bash
g server --monitor
```

Finally, connect to it:

```bash
python -m aiomonitor.cli
```


## Jupyter

Guillotina also works with Jupyter notebooks. Load the
[example notebook](https://github.com/plone/guillotina/blob/master/guillotina.ipynb) in the guillotina
repository to see an example of how to get started.
