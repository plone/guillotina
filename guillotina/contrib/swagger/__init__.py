from guillotina import configure


configure.permission("guillotina.swagger.View", "View swagger definition")
configure.grant(permission="guillotina.swagger.View", role="guillotina.Anonymous")
configure.grant(permission="guillotina.swagger.View", role="guillotina.Authenticated")


app_settings = {
    "static": {"swagger_static": "guillotina.contrib.swagger:static"},
    "swagger": {
        "authentication_allowed": True,
        "base_url": None,
        "auth_storage_search_keys": ["auth"],
        "base_configuration": {
            "openapi": "3.0.2",
            "info": {"version": "1.0", "title": "Guillotina", "description": "The REST Resource API"},
            "servers": [{"url": ""}],
            "paths": {},
            "security": [{"basicAuth": []}, {"bearerAuth": []}],
            "components": {
                "securitySchemes": {
                    "basicAuth": {"type": "http", "scheme": "basic"},
                    "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
                }
            },
        },
    },
}


def includeme(root):
    configure.scan("guillotina.contrib.swagger.services")
