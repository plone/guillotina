from guillotina import interfaces
from guillotina.db.oid import generate_oid
from typing import Any
from typing import Dict


app_settings: Dict[str, Any] = {
    "debug": False,
    "aiohttp_settings": {},
    "databases": [],
    "storages": {},
    "conflict_retry_attempts": 3,
    "host": "127.0.0.1",
    "port": 8080,
    "static": {},
    "jsapps": {},
    "default_static_filenames": ['index.html', 'index.htm'],
    "utilities": [],
    "store_json": True,
    "root_user": {
        "password": ""
    },
    "auth_extractors": [
        "guillotina.auth.extractors.BearerAuthPolicy",
        "guillotina.auth.extractors.BasicAuthPolicy",
        "guillotina.auth.extractors.WSTokenAuthPolicy",
    ],
    "auth_user_identifiers": [],
    "auth_token_validators": [
        "guillotina.auth.validators.SaltedHashPasswordValidator",
        "guillotina.auth.validators.JWTValidator"
    ],
    "default_permission": 'guillotina.AccessContent',
    "available_addons": {},
    "api_definition": {},
    "cors": {
        "allow_origin": ["http://localhost:8080"],
        "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH", "OPTIONS"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "allow_credentials": True,
        "max_age": 3660
    },
    "jwt": {
        "algorithm": "HS256"
    },
    'commands': {
        '': 'guillotina.commands.server.ServerCommand',
        'serve': 'guillotina.commands.server.ServerCommand',
        'create': 'guillotina.commands.create.CreateCommand',
        'shell': 'guillotina.commands.shell.ShellCommand',
        'testdata': 'guillotina.commands.testdata.TestDataCommand',
        'initialize-db': 'guillotina.commands.initialize_db.DatabaseInitializationCommand',
        'run': 'guillotina.commands.run.RunCommand'
    },
    "json_schema_definitions": {},  # json schemas available to reference in docs
    "default_layer": interfaces.IDefaultLayer,
    "http_methods": {
        "PUT": interfaces.IPUT,
        "POST": interfaces.IPOST,
        "PATCH": interfaces.IPATCH,
        "DELETE": interfaces.IDELETE,
        "GET": interfaces.IGET,
        "OPTIONS": interfaces.IOPTIONS,
        "HEAD": interfaces.IHEAD,
        "CONNECT": interfaces.ICONNECT
    },
    "cloud_storage": "guillotina.interfaces.IDBFileField",
    "router": "guillotina.traversal.TraversalRouter",
    "pg_connection_class": "asyncpg.connection.Connection",
    "oid_generator": generate_oid,
    "cors_renderer": "guillotina.cors.DefaultCorsRenderer",
    "check_writable_request": "guillotina.writable.check_writable_request"
}
