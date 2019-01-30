# Serializing content

Guillotina provides ways to hook into the content serialization
that is done when you retreive content from the API.

All serializers are:

- adapters of the context and current request
- async callable objects that return a dictionary of json compatible data

The training doc has a great introduction on
[customizing the serialization for content](../training/extending/serialize.html).


Serialization interfaces:

- `guillotina.interfaces.IResourceSerializeToJson`: Provides full content
- `guillotina.interfaces.IResourceSerializeToJsonSummary`: Summary of content
- `guillotina.interfaces.IFactorySerializeToJson`: Information on conten type
- `guillotina.interfaces.ISchemaSerializeToJson`: Serialize full schema
- `guillotina.interfaces.ISchemaFieldSerializeToJson`: Feild of a schema
- `guillotina.interfaces.ICatalogDataAdapter`: Searchable data(for adapters like elasticsearch)
- `guillotina.interfaces.ISecurityInfo`: minimal data used for changes
  to security of object required by catalog adapters.
- `guillotina.db.interfaces.IJSONDBSerializer`: Content serialized to db
  in addition to pickled data. Used with the JSONB field in postgresql.
  By default this is the same as `ICatalogDataAdapter`.


## Type serialization

You can customize the any serialization by providing override adapters.

For example, to customize the default summary serialization of your custom type:

```python
from guillotina import configure
from guillotina.interfaces import IResourceSerializeToJsonSummary
from guillotina.json.serialize_content import DefaultJSONSummarySerializer
from zope.interface import Interface


@configure.adapter(
    for_=(IMyContext, Interface),
    provides=IResourceSerializeToJsonSummary)
class ConversationJSONSummarySerializer(DefaultJSONSummarySerializer):
    async def __call__(self):
        data = await super().__call__()
        data.update({
            'creation_date': self.context.creation_date,
            'title': self.context.title,
            'users': self.context.users
        })
        return data
```


## JSON DB

By default, `store_json` is `false` in the application settings. To activate this
feature, make sure to set `store_json: true` in your yaml configuration.

To customize the json serialized to the database for your application or type:

```python
from guillotina.db.interfaces import IJSONDBSerializer
from guillotina import configure

@configure.adapter(
    for_=IMyType,
    provides=IJSONDBSerializer)
class JSONDBSerializer(DefaultCatalogDataAdapter):
    async def __call__(self):
        return {
            'foo': 'bar'
        }
```
