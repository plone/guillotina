# Production

## Nginx front

Its so common to add the api with a nginx with a proxy_pass in front so there is the option
define which is going to be the url for the generated urls inside the api:

Adding the header:

```
X-VirtualHost-Monster https://example.com/api/
```

Will do a rewrite of the urls.

Some configuration on nginx :

```
    location /api/ {
        proxy_set_header X-VirtualHost-Monster $scheme://$http_host/api/
        proxy_pass http://api.guillotina.svc.cluster.local:80/;
    }
```