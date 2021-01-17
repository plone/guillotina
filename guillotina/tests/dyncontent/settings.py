DEFAULT_SETTINGS = {
    "applications": ["guillotina.contrib.dyncontent"],
    "myoptions": [["guillotina", "Also Love Guillotina"], ["plone", "Also Love Plone"]],
    "behaviors": {
        "myannotationdata": {
            "title": "MyData",
            "for": "guillotina.interfaces.IResource",
            "inherited_class": "guillotina.behaviors.instance.AnnotationBehavior",
            "properties": {
                "mydata1": {
                    "type": "guillotina.schema.TextLine",
                    "title": "Text",
                    "default": "Hello",
                    "required": True,
                }
            },
        },
        "mycontextdata": {
            "title": "MyLocalData",
            "for": "guillotina.interfaces.IResource",
            "inherited_class": "guillotina.behaviors.instance.ContextBehavior",
            "properties": {
                "mydata2": {"type": "guillotina.schema.TextLine", "title": "Text", "default": "Hello"}
            },
        },
    },
    "contents": {
        "mydoc": {
            "title": "My Doc",
            "inherited_interface": "guillotina.interfaces.IFolder",
            "inherited_class": "guillotina.content.Folder",
            "add_permission": "guillotina.AddContent",
            "allowed_types": ["Image", "File"],
            "behaviors": [
                "guillotina.behaviors.dublincore.IDublinCore",
                "guillotina.contrib.dyncontent.interfaces.Imycontextdata",
            ],
            "properties": {
                "json_example": {
                    "type": "guillotina.schema.JSONField",
                    "schema": {"type": "object", "properties": {"items": {"type": "array"}}},
                    "title": "My Json Field",
                },
                "text": {
                    "type": "guillotina.schema.Text",
                    "widget": "richtext",
                    "title": "Text",
                    "write_permission": "guillotina.Manager",
                    "index": {"type": "searchabletext"},
                    "required": True,
                },
                "mysecondoption": {
                    "type": "guillotina.schema.Choice",
                    "title": "My loved option",
                    "vocabulary": "appsettings:myoptions",
                    "index": {"type": "keyword"},
                },
                "mythirdoption": {
                    "type": "guillotina.schema.Choice",
                    "title": "My loved option",
                    "vocabulary": {"option1": "token1", "option2": "token2"},
                    "index": {"type": "keyword"},
                },
                "mylovedlist": {
                    "type": "guillotina.schema.List",
                    "value_type": "guillotina.schema.TextLine",
                    "title": "My loved action",
                    "index": {"type": "keyword"},
                },
            },
        }
    },
}
