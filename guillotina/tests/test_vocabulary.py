from guillotina import configure
from guillotina.schema.vocabulary import getVocabularyRegistry


@configure.vocabulary(
    name="testvocab")
class VocabTest:

    def __init__(self, context):
        self.context = context

    def __iter__(self):
        return iter([self.getTerm(x) for x in range(0, 10)])

    def __contains__(self, value):
        return 0 <= value < 10

    def __len__(self):
        return 10

    def getTerm(self, value):
        return 'value'


def test_registered_vocabulary(dummy_request):
    vr = getVocabularyRegistry()
    vocabulary = vr.get(None, 'testvocab')
    assert vocabulary is not None
    assert 0 in vocabulary
    assert vocabulary.getTerm(0) == 'value'
