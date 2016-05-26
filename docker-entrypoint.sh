#!/bin/bash
set -e

if [ -n "$OAUTH_PORT_6543_TCP_ADDR" ]; then
    if [ -z "$OAUTH_HOST" ]; then
        OAUTH_HOST='oauth'
    else
        echo >&2 'warning: both OAUTH_HOST and OAUTH_PORT_6379_TCP_ADDR found'
        echo >&2 "  Connecting to OAUTH_HOST ($OAUTH_HOST)"
        echo >&2 '  instead of the linked oauth container'
    fi
fi

if [ -n "$OAUTH_PORT_6543_TCP_PORT" ]; then
    if [ -z "$OAUTH_PORT" ]; then
        OAUTH_PORT=6379
    else
        echo >&2 'warning: both OAUTH_PORT and OAUTH_PORT_8080_TCP_PORT found'
        echo >&2 "  Connecting to OAUTH_PORT ($OAUTH_PORT)"
        echo >&2 '  instead of the linked oauth container'
    fi
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

until nc -z $OAUTH_HOST $OAUTH_PORT;
do
  echo "Waiting for oauth"
  sleep 1
done

echo "START PLONE SERVER"

exec "$@"