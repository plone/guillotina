#!/bin/bash
set -e

if [ -z "$OAUTH_HOST" ]; then
    OAUTH_HOST='oauth'
fi

if [ -z "$OAUTH_PORT" ]; then
    OAUTH_PORT='6543'
fi

if [ -z "$ELASTIC_HOST" ]; then
    ELASTIC_HOST='elasticsearch'
fi

if [ -z "$ELASTIC_PORT" ]; then
    ELASTIC_PORT='9200'
fi

if [ -z "$JWTSECRET" ]; then
    echo >&2 'error: missing required JWTSECRET environment variable'
    echo >&2 '  Did you forget to -e JWTSECRET=... ?'
    echo >&2
    exit 1
fi

if [ -z "$JWTALGORITHM" ]; then
    echo >&2 'error: missing required JWTALGORITHM environment variable'
    echo >&2 '  Did you forget to -e JWTALGORITHM=... ?'
    echo >&2
    exit 1
fi

if [ -z "$CLIENTID" ]; then
    echo >&2 'error: missing required CLIENTID environment variable'
    echo >&2 '  Did you forget to -e CLIENTID=... ?'
    echo >&2
    exit 1
fi

if [ -z "$CLIENTPASSWORD" ]; then
    echo >&2 'error: missing required CLIENTPASSWORD environment variable'
    echo >&2 '  Did you forget to -e CLIENTPASSWORD=... ?'
    echo >&2
    exit 1
fi

echo "SET CONFIG"
echo '{
  "utility": "plone.server.auth.oauth.OAuth",
  "settings": {
    "server": "http://$OAUTH_HOST:$OAUTH_PORT/",
    "jwt_secret": "$JWTSECRET",
    "jwt_algorithm": "$JWTALGORITHM",
    "client_id": "$CLIENTID",
    "client_password": "$CLIENTPASSWORD"
  }
}' > /app/src/plone.server/plone/server/auth/oauth.json


sed -i 's/localhost:9200/$ELASTIC_HOST:$ELASTIC_PORT/' /app/src/plone.server/plone/server/search/elasticsearch.json

until nc -z $OAUTH_HOST $OAUTH_PORT;
do
  echo "Waiting for oauth"
  sleep 1
done

echo "START PLONE SERVER"

exec "$@"