# Production

## Nginx front

It's very common to run the API using `nginx` with a `proxy_pass` in front, 
so there is an option to define the URL for the generated URLs inside the api:

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


## Postgresql

With very large databases, Postgresql can get into a state where particular
prepared statements perform very poorly and they'll start pegging your CPU.

The origin of this problem is related to how asyncpg caches prepared statements.

If you start seeing this problem, it is recommdned to tune the following
connection configuration options:

- `statement_cache_size`: Setting to `0` is an option
- `max_cached_statement_lifetime`: Set to extremely low value(2)


(Make sure to tune postgresql for your server and dataset size.)