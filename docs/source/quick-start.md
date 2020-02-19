# Quick Start

## Pre.

```eval_rst
.. note::

   Add needed software requirements such as ``pip``
```

Install Guillotina:

```shell
pip install guillotina
g serve --port=8080
```

Then use curl, [Postman](https://www.postman.com/ "Link to Postman") or build something with it

```
curl -XPOST --user root:root http://localhost:8080/db -d '{
  "@type": "Container",
  "id": "container"
}'
curl --user root:root http://localhost:8080/db/container
```
