from guillotina import configure
from guillotina.schema.vocabulary import getVocabularyRegistry

import pytest


@configure.vocabulary(name="testvocab")
class VocabTest:
    def __init__(self, context):
        self.context = context

    def __iter__(self):
        return iter([self.getTerm(x) for x in range(0, 10)])

    def __contains__(self, value):
        return 0 <= value < 10

    def __len__(self):
        return 10

    def keys(self):
        return range(0, 10)

    def getTerm(self, value):
        return "value"


def test_registered_vocabulary(dummy_request):
    vr = getVocabularyRegistry()
    vocabulary = vr.get(None, "testvocab")
    assert vocabulary is not None
    assert 0 in vocabulary
    assert vocabulary.getTerm(0) == "value"


@pytest.mark.asyncio
async def test_api_vocabulary(container_requester):
    async with container_requester as requester:
        response, _ = await requester("GET", "/db/guillotina/@vocabularies")
        assert len(response) == 1
        assert response[0]["title"] == "testvocab"

        response, _ = await requester("GET", "/db/guillotina/@vocabularies/testvocab")
        assert len(response["items"]) == 10

        response, _ = await requester("GET", "/db/guillotina/@vocabularies/testvocab?token=1")
        assert len(response["items"]) == 1

        response, _ = await requester("GET", "/db/guillotina/@vocabularies/testvocab?title=val")
        assert len(response["items"]) == 10
