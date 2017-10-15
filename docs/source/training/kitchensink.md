# Kitchen Sink

This part of the training material is going to talk about the
[guillotina_kitchensink](https://github.com/guillotinaweb/guillotina_kitchensink)
repository.

This repository gives you a working configuration and install of:

- guillotina_dbusers: Store and manage users on the database
- guillotina_elasticsearch: Index on content in elasticsearch
- guillotina_swagger: Access site swagger definition at http://localhost:8080/@docs
- guillotina_rediscache: Cache db objects in redis


The components it runs as part of the docker compose file are:

- postgresql
- elasticsearch
- redis

First off, start by cloning the repository and starting it.

```
git clone https://github.com/guillotinaweb/guillotina_kitchensink.git
cd guillotina_kitchensink
docker-compose -f docker-compose.yaml run --rm --service-ports guillotina
```


Add some content using Postman and then let's do an elasticsearch query:

```
POST /db/container/@search
{
  "query": {
    "bool": {
      "must": [
        {
          "match": {
            "title": "foobar"
          }
        }
      ]
    }
  }
}
```
