# Production

## Nginx front

It's very common to run the API using `nginx` with a `proxy_pass` in front,
so there is an option to define the URL for the generated URLs inside the API:

Adding the header:

```
X-VirtualHost-Monster https://example.com/api/
```

will do a rewrite of the URLs.

Sample configuration on `nginx`:

```
    location /api/ {
        proxy_set_header X-VirtualHost-Monster $scheme://$http_host/api/
        proxy_pass http://api.guillotina.svc.cluster.local:80/;
    }
```


## Servicing Guillotina with Ambassador/Envoy

Working with ambassador/envoy works the same as with any other api service gateway; however,
there are a few things you can do to improve your experience.

First off, if you want to use internal urls to access guillotina defined services,
you will need to utilize dynamically adding a header to the request in order
for Guillotina to understand how it's being served and generate urls correctly.

Example with ambassador:

```
getambassador.io/config: |
  ...
  add_request_headers:
    x-virtualhost-path: /path-served-at/
  ...
```

Additionally, it is recommended to use a resolver with a load balancer that will
hash requests to backends based on the Authorization header. This encourages
requests from a single user to be directed at the same backend so you will get
more cache hits.

```
getambassador.io/config: |
  ...
  resolver: <my endpoint resolver>
  load_balancer:
    policy: ring_hash
    header: Authorization
```


## PostgreSQL

With very large databases, PostgreSQL can get into a state where particular
prepared statements perform very poorly and they'll start pegging your CPU.

The origin of this problem is related to how asyncpg caches prepared statements.

If you start seeing this problem, it is recommended to tune the following
connection configuration options:

- `statement_cache_size`: Setting to `0` is an option
- `max_cached_statement_lifetime`: Set to extremely low value(2)


(Make sure to tune PostgreSQL for your server and dataset size.)