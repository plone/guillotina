# CONFIGURATION

`plone.server` and it's addon define global configuration that is used throughout
the `plone.server`. All of these settings are configurable by providing a
JSON configuration file to the start script.

By default, the startup script looks for a `config.json` file. You can use a different
file by using the `-c` option for the script script like this `./bin/pserver -c myconfig.json`.


## Databases

To configure available databases, use the `databases` option. Configuration options
map 1-to-1 to ZODB setup:

```json
{
	"databases": [{
    "zodb1": {
			"storage": "ZODB",
			"path": "Data.fs"
		},
		"zodb2": {
			"storage": "ZEO",
			"address": "127.0.0.1",
      "port": 8090,
			"configuration": {
                "pool_size": 100,
                "cache_size": 100
           	}
		}
	}]
}
```

## STATIC FILES

```json
{
  "static": [
    {"favicon.ico": "static/favicon.ico"}
  ]
}
```


## SERVER PORT

```json
{
	"address": 8080
}
```


## ROOT USER PASSWORD

```json
{
	"root_user": {
		"password": "root"
	}
}
```

## CORS

```json
{
	"cors": {
		"allow_origin": ["*"],
		"allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH"],
		"allow_headers": ["*"],
		"expose_headers": ["*"],
		"allow_credentials": true,
		"max_age": 3660
	}
}
```

# ASYNC UTILITIES

```json
{
	"utilities": [{
    "provides": "plone.server.interfaces.ICatalogUtility",
    "factory": "pserver.elasticsearch.utility.ElasticSearchUtility",
    "settings": {}
  }]
}
