from guillotina import configure
from guillotina.interfaces import IAbsoluteURL
from guillotina.interfaces import IResource
from guillotina.response import HTTPNotFound
from guillotina.schema.vocabulary import getVocabularyRegistry
from guillotina.schema.vocabulary import VocabularyRegistryError
from os.path import join


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.AccessContent",
    name="@vocabularies",
    summary="Get available vocabularies",
)
async def get_vocabularies(context, request):
    result = []
    vocabulary_registry = getVocabularyRegistry()
    for key in vocabulary_registry._map.keys():
        result.append({"@id": join(IAbsoluteURL(context)(), "@vocabularies", key), "title": key})
    return result


@configure.service(
    context=IResource,
    method="GET",
    permission="guillotina.AccessContent",
    name="@vocabularies/{key}",
    summary="Get specific vocabulary",
)
async def get_block_schema(context, request):
    key = request.matchdict["key"]
    vocabulary_registry = getVocabularyRegistry()
    try:
        vocab = vocabulary_registry.get(context, key)
    except VocabularyRegistryError:
        return HTTPNotFound()

    title_filter = request.query.get("title")
    if title_filter:
        title_filter = title_filter.lower()
    token_filter = request.query.get("token")
    if token_filter:
        token_filter = token_filter.lower()

    result = {}
    result["@id"] = join(IAbsoluteURL(context)(), "@vocabularies", key)
    result["items"] = []
    for term in vocab.keys():
        if token_filter and token_filter not in str(term).lower():
            continue
        new_title = vocab.getTerm(term)
        if title_filter and title_filter not in str(new_title).lower():
            continue
        result["items"].append({"title": new_title, "token": term})
    result["items_total"] = len(result["items"])
    return result
