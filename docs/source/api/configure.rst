:mod:`guillotina.configure`
---------------------------

.. automodule:: guillotina.configure

  .. autofunction:: scan
  .. autofunction:: json_schema_definition

  .. function:: service(**kwargs)

     Configure a service

     >>> from guillotina import configure
     >>> @configure.service(name='@foobar')
         async def foobar_service(context, request): return {'foo': 'bar'}


     :param context: Content type interface this service is registered against
     :type context: Interface
     :param method: HTTP method this service works against. Defaults to `GET`.
     :type method: str
     :param permission: Permission this service requires
     :type permission: str
     :param layer: Layer this service is registered for. Default is `IDefaultLayer`
     :type layer: str
     :param name: This is used as part of the uri. Example `@foobar` -> `/mycontent/@foobar`.
     :param summary: Used for documentation and swagger.
     :param description: Used for documentation and swagger.
     :param responses: Used for documentation and swagger.
     :param parameters: Used for documentation and swagger.

  .. function:: contenttype(**kwargs)

     Configure content type

     >>> from guillotina import configure
     >>> from guillotina.content import Item
     >>> @configure.contenttype(type_name="Foobar")
         class Foobar(Item): pass

     :param type_name: Name of the content type
     :type type_name: str
     :param schema: Schema to use for content type
     :type schema: str
     :param add_permission: Permission required to add content. Defaults to `guillotina.AddContent`
     :type add_permission: str
     :param allowed_types: List of types allowed to be added inside this content assuming it is a Folder type. Defaults to allowing all types.
     :type allowed_types: list
     :param behaviors: List of behaviors to enable for this type.
     :type behaviors: list
     :param factory: Dotted name to custom factory to use. See guillotina.content.ResourceFactory for default implementation
     :type behaviors: str


  .. function:: behavior(**kwargs)

     Configure behavior

     >>> from guillotina import configure
     >>> from guillotina.behaviors.instance import ContextBehavior
     >>> class IMyBehavior(Interface): pass
     >>> @configure.behavior(
           title="Dublin Core fields",
           provides=IMyBehavior,
           for_="guillotina.interfaces.IResource")
         class MyBehavior(ContextBehavior): pass

     :param title: Title of behavior
     :param provides: Schema to use for behavior
     :param behavior: Marker interface to apply to utilized instance's behavior
     :param `for_`: Content type this behavior is available for


  .. function:: vocabulary(**kwargs)

     Configure vocabulary

     >>> from guillotina import configure
     >>> @configure.vocabulary(name="myvocab")
         class MyVocab:
           def __init__(self, context):
             self.context = context
             self.values = range(10)
           def __iter__(self):
             return iter([])
           def __contains__(self, value):
             return value in self.values
           def __len__(self):
             return len(self.values)
           def getTerm(self, value):
             return 'value'

     :param name: Reference of the vocabulary to get it


  .. function:: addon(**kwargs)

     Configure addon

     >>> from guillotina import configure
     >>> @configure.addon(
           name="docaddon",
           title="Doc addon",
           dependencies=["cms"])
         class TestAddon(Addon): pass

     :param name: Unique name of addon
     :param title: Title of addon
     :param dependencies: List of names of dependency addons


  .. function:: adapter(**kwargs)

     Configure adapter

     :param `for_`: Type or list of types this subscriber is for: *required*
     :param provides: Interface this adapter provides


  .. function:: utility(**kwargs)

     Configure utility

     :param provides: Interface this utility provides
     :param name: Optional to name the utility

  .. function:: permission(**kwargs)

     Configure permission

     :param id:
     :param title:
     :param description:

  .. function:: role(**kwargs)

     Configure role

     :param id:
     :param title:
     :param description:
     :param local: defaults to True
     :type local: bool


  .. function:: grant(**kwargs)

     Configure granting permission to role

     :param role:
     :param principal:
     :param permission:
     :param permissions:

  .. function:: value_serializer(type)

     Configure a value serializer

     >>> @configure.value_serializer(bytes)
     >>> def bytes_converter(value): return b64encode(value)

     :param type: type to serialize

  .. function:: value_deserializer(field_type)

     Configure a value deserializer

     >>> @configure.value_deserializer(IText)
     >>> def field_converter(field, value, context): return value

     :param field_type: type of field to deserialize

  .. function:: renderer(**kwargs)

     Configure a renderer

     >>> @configure.renderer(name='text/plain')
     >>> class RendererPlain(StringRenderer):
           content_type = 'text/plain'

     :param name: content type the renderer can be used for

  .. function:: language(name)

     Configure a language

     >>> @configure.language(name='en')
     >>> class EN(DefaultLanguage): pass

     :param name: Name of language


