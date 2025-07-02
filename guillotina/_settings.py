from guillotina import interfaces
from guillotina.db.uid import generate_uid
from typing import Any
from typing import Dict

import copy
import pickle
import string


app_settings: Dict[str, Any] = {
    "debug": False,
    "databases": [],
    "storages": {},
    "cache": {"strategy": "dummy"},
    "conflict_retry_attempts": 3,
    "host": "127.0.0.1",
    "port": 8080,
    "static": {},
    "jsapps": {},
    "post_serialize": [],
    "default_static_filenames": ["index.html", "index.htm"],
    "container_types": ["Container"],
    "load_utilities": {
        "guillotina.queue": {
            "provides": "guillotina.interfaces.IQueueUtility",
            "factory": "guillotina.async_util.QueueUtility",
            "settings": {},
        },
        "guillotina.jobpool": {
            "provides": "guillotina.interfaces.IAsyncJobPool",
            "factory": "guillotina.async_util.AsyncJobPool",
            "settings": {"max_size": 5},
        },
    },
    "store_json": True,
    "pickle_protocol": pickle.HIGHEST_PROTOCOL,
    "root_user": {"password": ""},
    "auth_extractors": [
        "guillotina.auth.extractors.BearerAuthPolicy",
        "guillotina.auth.extractors.BasicAuthPolicy",
        "guillotina.auth.extractors.WSTokenAuthPolicy",
    ],
    "auth_user_identifiers": [],
    "auth_token_validators": [
        "guillotina.auth.validators.SaltedHashPasswordValidator",
        "guillotina.auth.validators.JWTValidator",
    ],
    "default_permission": "guillotina.AccessContent",
    "available_addons": {},
    "api_definition": {},
    "cors": {
        "allow_origin": ["http://localhost:8080"],
        "allow_methods": ["GET", "POST", "DELETE", "HEAD", "PATCH", "PUT", "OPTIONS"],
        "allow_headers": ["*"],
        "expose_headers": ["*"],
        "allow_credentials": True,
        "max_age": 3660,
    },
    "jwt": {"algorithm": "HS256", "token_expiration": 60 * 60 * 1},
    "commands": {
        "": "guillotina.commands.server.ServerCommand",
        "serve": "guillotina.commands.server.ServerCommand",
        "create": "guillotina.commands.create.CreateCommand",
        "shell": "guillotina.commands.shell.ShellCommand",
        "testdata": "guillotina.commands.testdata.TestDataCommand",
        "initialize-db": "guillotina.commands.initialize_db.DatabaseInitializationCommand",
        "run": "guillotina.commands.run.RunCommand",
        "dbvacuum": "guillotina.commands.vacuum.VacuumCommand",
        "migrate": "guillotina.commands.migrate.MigrateCommand",
        "gen-key": "guillotina.commands.crypto.CryptoCommand",
        "serve-reload": "guillotina.commands.serve_reload.ServeReloadCommand",
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
        "CONNECT": interfaces.ICONNECT,
    },
    "cloud_storage": "guillotina.interfaces.IDBFileField",
    "cloud_datamanager": "db",
    "router": "guillotina.traversal.TraversalRouter",
    "pg_connection_class": "asyncpg.connection.Connection",
    "uid_generator": generate_uid,
    "cors_renderer": "guillotina.cors.DefaultCorsRenderer",
    "check_writable_request": "guillotina.writable.check_writable_request",
    "indexer": "guillotina.catalog.index.Indexer",
    "search_parser": "default",
    "object_reader": "guillotina.db.reader.reader",
    "thread_pool_workers": 32,
    "server_settings": {"uvicorn": {"timeout_keep_alive": 5, "http": "h11"}},
    "valid_id_characters": string.digits + string.ascii_lowercase + ".-_@$^()+ =",
    "load_catalog": True,
    "catalog_max_results": 50,
    "managers_roles": {
        "guillotina.ContainerAdmin": 1,
        "guillotina.ContainerDeleter": 1,
        "guillotina.Owner": 1,
        "guillotina.Member": 1,
        "guillotina.Manager": 1,
    },
}
default_settings = copy.deepcopy(app_settings)
