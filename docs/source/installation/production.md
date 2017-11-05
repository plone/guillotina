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
