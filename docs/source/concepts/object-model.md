# Object Model

## What it is

Guillotina stores resources in a tree. The application root exposes databases,
databases expose containers, and containers hold content resources. URLs map to
that tree, so location is part of the API contract.

## Where it appears

- `/` resolves to the application object.
- `/db` resolves to a configured database named `db`.
- `/db/container` resolves to a container inside that database.
- `/db/container/item` resolves to a content object inside the container.

## Create a container

```shell
curl -u root:root \
  -X POST http://localhost:8080/db \
  -H 'Content-Type: application/json' \
  -d '{"@type": "Container", "id": "docs"}'
```

## Define a content type

```python
from guillotina import configure, content, schema
from zope import interface


class IArticle(interface.Interface):
    title = schema.TextLine(title="Title")


@configure.contenttype(type_name="Article", schema=IArticle)
class Article(content.Resource):
    pass
```

## Extension points

- Content type schemas define fields and validation.
- Behaviors add reusable fields or behavior to multiple content types.
- Services can target a specific content interface or a broader container type.
- Security and catalog behavior depend on the resolved context path.

## Common failures

- Creating content in the wrong container gives correct objects in the wrong
  security and search scope.
- Moving or copying content without considering local roles can change access.
- Assuming object IDs are globally unique ignores container boundaries.

## Related pages

- {doc}`traversal`
- {doc}`security-model`
- {doc}`catalog`
- {doc}`../developer/contenttypes`
