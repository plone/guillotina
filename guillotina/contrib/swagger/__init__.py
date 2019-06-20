from guillotina import configure


configure.permission("guillotina.swagger.View", "View swagger definition")
configure.grant(
    permission="guillotina.swagger.View", role="guillotina.Anonymous"
)
configure.grant(
    permission="guillotina.swagger.View", role="guillotina.Authenticated"
)


app_settings = {
    "static": {"swagger_static": "guillotina.contrib.swagger:static"},
    "swagger": {
        "authentication_allowed": True,
        "base_url": None,
        "auth_storage_search_keys": ["auth"],
        "base_configuration": {
            "swagger": "2.0",
            "info": {
                "version": "",
                "title": "Guillotina",
                "description": "The REST Resource API",
            },
            "host": "",
            "basePath": "",
            "schemes": [],
            "produces": ["application/json"],
            "consumes": ["application/json"],
            "paths": {},
            "definitions": {},
        },
    },
}


def includeme(root):
    configure.scan("guillotina.contrib.swagger.services")
