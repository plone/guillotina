from guillotina import configure


configure.json_schema_definition('Addon', {
    "type": "object",
    "title": "Addon data",
    "properties": {
        "id": {
            "type": "string"
        },
        "title": {
            "type": "string"
        }
    },
    'required': ['id']
})


configure.json_schema_definition('AddonResponse', {
    "type": "object",
    "title": "Addons response data",
    "properties": {
        "available": {
            "type": "array",
            "items": {
                "type": "object",
                "$ref": "#/definitions/Addon"
            }
        },
        "installed": {
            "type": "array",
            "items": {
                "type": "object",
                "$ref": "#/definitions/Addon"
            }
        }
    }
})

configure.json_schema_definition('Application', {
    "type": "object",
    "title": "Application data",
    "properties": {
        "databases": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "static_file": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "static_directory": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    }
})


configure.json_schema_definition('Behavior', {
    "type": "object",
    "title": "Behavior",
    "properties": {
        "behavior": {
            "type": "string",
            "title": "Dotted name to interface"
        }
    },
    'required': ['behavior']
})

configure.json_schema_definition('BehaviorsResponse', {
    "type": "object",
    "title": "Behavior data on a resource",
    "properties": {
        "static": {
            "type": "array",
            "items": {
                "type": "string",
                "title": "Dotted name to interface",
            }
        },
        "dynamic": {
            "type": "array",
            "items": {
                "type": "string",
                "title": "Dotted name to interface",
            }
        },
        "available": {
            "type": "array",
            "items": {
                "type": "string",
                "title": "Dotted name to interface",
            }
        }
    }
})


configure.json_schema_definition('BaseResource', {
    "type": "object",
    "title": "Base resource data",
    "properties": {
        "id": {
            "type": "string"
        },
        "@type": {
            "type": "string"
        },
        "title": {
            "type": "string"
        }
    },
    'required': ['id']
})


configure.json_schema_definition('WritableResource', {
    "type": "object",
    "title": "Writable resource data",
    "properties": {
        "title": {
            "type": "string"
        }
    }
})


configure.json_schema_definition('AddableResource', {
    "type": "object",
    "title": "Writable resource data",
    "allOf": [
        {"$ref": "#/definitions/BaseResource"},
        {"$ref": "#/definitions/WritableResource"}
    ]
})


configure.json_schema_definition('Resource', {
    "type": "object",
    "title": "Resource data",
    "allOf": [
        {"$ref": "#/definitions/WritableResource"},
        {
            "type": "object",
            "properties": {
                "@id": {
                    "type": "string"
                },
                "@type": {
                    "type": "string"
                },
                "parent": {
                    "type": "object",
                    "schema": {
                        "properties": {
                            "@id": {
                                "type": "string"
                            },
                            "@type": {
                                "type": "string"
                            }
                        }
                    }
                }
            },
            'required': ['@id', '@type']
        }
    ]
})


configure.json_schema_definition('ResourceFolder', {
    "type": "object",
    "title": "Resource folder data",
    "allOf": [
        {"$ref": "#/definitions/Resource"},
        {
            "properties": {
                "items": {
                    "type": "object",
                    "schema": {
                        "$ref": "#/definitions/Resource"
                    }
                },
                "length": {
                    "type": "integer"
                }
            }
        }
    ]
})


configure.json_schema_definition('ACL', {
    "type": "object",
    "title": "A set of permissions",
    "properties": {
        "@id": {
            "type": "string",
        },
        "roleperm": {
            "type": "object"
        },
        "prinperm": {
            "type": "object"
        },
        "prinrole": {
            "type": "object"
        }
    }
})


configure.json_schema_definition('ResourceACL', {
    "type": "object",
    "title": "All permissions for an object",
    "properties": {
        "local": {
            "type": "object",
            "schema": {
                "$ref": "#/definitions/ACL"
            }
        },
        "inherit": {
            "type": "array",
            "items": {
                "type": "object",
                "schema": {
                    "$ref": "#/definitions/ACL"
                }
            }
        }
    }
})


configure.json_schema_definition('PrincipalRole', {
    "type": "object",
    "title": "Role assigned to principal",
    "properties": {
        "principal": {
            "type": "string",
        },
        "role": {
            "type": "string",
        },
        "setting": {
            "enum": ["Allow", "Deny", "AllowSingle", "Unset"],
        }
    },
    'required': ['principal', 'role', 'setting']
})


configure.json_schema_definition('PrincipalPermission', {
    "type": "object",
    "title": "Permission assigned to principal",
    "properties": {
        "principal": {
            "type": "string"
        },
        "permission": {
            "type": "string"
        },
        "setting": {
            "enum": ["Allow", "Deny", "AllowSingle", "Unset"]
        }
    },
    'required': ['principal', 'permission', 'setting']
})


configure.json_schema_definition('RolePermission', {
    "type": "object",
    "title": "Permission assigned to role",
    "properties": {
        "permission": {
            "type": "string",
        },
        "role": {
            "type": "string",
        },
        "setting": {
            "enum": ["Allow", "Deny", "AllowSingle", "Unset"],
        }
    },
    'required': ['role', 'permission', 'setting']
})


configure.json_schema_definition('Permissions', {
    "type": "object",
    "title": "Permissions defined for a resource ACL",
    "properties": {
        "prinperm": {
            "type": "array",
            "items": {
                "type": "object",
                "schema": {
                    "$ref": "#/definitions/PrincipalPermission"
                }
            },
        },
        "prinrole": {
            "type": "array",
            "items": {
                "type": "object",
                "schema": {
                    "$ref": "#/definitions/PrincipalRole"
                }
            },
        },
        "roleperm": {
            "type": "array",
            "items": {
                "type": "object",
                "schema": {
                    "$ref": "#/definitions/RolePermission"
                },
            }
        }
    }
})

configure.json_schema_definition('AllPermissions', {
    "type": "array",
    "items": {
        "type": "object",
        "schema": {
            "type": "object",
            "schema": {
                "$ref": "#/definitions/Permissions"
            }
        }
    }
})


configure.json_schema_definition('SearchResult', {
    "type": "object",
    "title": "Search result",
    "properties": {

    }
})


configure.json_schema_definition('SearchResults', {
    "type": "object",
    "title": "Search results",
    "properties": {
        "member": {
            "type": "array",
            "items": {
                "type": "object",
                "schema": {
                    "$ref": "#/definitions/SearchResult"
                }
            }
        },
        "items_count": {
            "type": "integer"
        }
    },
    'required': ['member']
})
