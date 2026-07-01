# Catalog

## What it is

The catalog is Guillotina's indexed search layer. It lets clients query content
without walking the object tree manually. The JSONB catalog stores indexed data
in PostgreSQL and exposes search through the `@search` endpoint.

## Where it appears

- Content fields can be indexed by content type or behavior configuration.
- Mutations update indexed state as part of persistence workflows.
- Clients query container or content scopes through `@search`.

## Search content

```shell
curl -u root:root \
  'http://localhost:8080/db/docs/@search?type_name=Article&title__in=Guillotina'
```

## Define an indexed field

```python
from guillotina import configure, content, schema
from guillotina.directives import index_field
from zope import interface


class IArticle(interface.Interface):
    index_field("title", type="text")
    title = schema.TextLine(title="Title")


@configure.contenttype(type_name="Article", schema=IArticle)
class Article(content.Resource):
    pass
```

`index_field` is a directive that must be called inside the interface body so it
attaches indexing metadata to the schema. To index a field defined elsewhere,
use `index_field.apply(IArticle, "title", type="text")` instead.

## Index a computed value

Use `index_field.with_accessor` when the indexed value is not a direct schema
field but is derived from the object. It decorates an accessor function that
receives the resource and returns the value to index.

```python
from guillotina.directives import index_field


@index_field.with_accessor(IArticle, "author_name", type="keyword")
def get_author_name(ob):
    return ob.author.name
```

## Extension points

- Use `@search` for user-facing content discovery.
- Add indexes for fields that need filtering or sorting.
- Use catalog-aware utilities instead of loading large object trees into memory.

## Common failures

- Searching on a field that is not indexed gives incomplete or unexpected
  behavior.
- Stale indexes can hide recently changed content until reindexing completes.
- Querying too broad a container scope can make expensive searches look like API
  failures.
- Security still applies: search results are filtered by accessible context.

## Related pages

- {doc}`storage`
- {doc}`traversal`
- {doc}`security-model`
- {doc}`../rest/search`
- {doc}`../contrib/jsonbcatalog`
