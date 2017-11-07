##############################################################################
#
# Copyright (c) 2003 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Vocabulary support for schema.
"""

from collections import OrderedDict
from guillotina.schema.interfaces import ITitledTokenizedTerm
from guillotina.schema.interfaces import ITokenizedTerm
from guillotina.schema.interfaces import ITreeVocabulary
from guillotina.schema.interfaces import IVocabularyRegistry
from guillotina.schema.interfaces import IVocabularyTokenized
from zope.interface import directlyProvides
from zope.interface import implementer


# simple vocabularies performing enumerated-like tasks
_marker = object()


@implementer(ITokenizedTerm)
class SimpleTerm(object):
    """Simple tokenized term used by SimpleVocabulary."""

    def __init__(self, value, token=None, title=None):
        """Create a term for value and token. If token is omitted,
        str(value) is used for the token.  If title is provided,
        term implements ITitledTokenizedTerm.
        """
        self.value = value
        if token is None:
            token = value
        # In Python 3 str(bytes) returns str(repr(bytes)), which is not what
        # we want here. On the other hand, we want to try to keep the token as
        # readable as possible.
        self.token = str(token) \
            if not isinstance(token, bytes) \
            else str(token.decode('ascii', 'ignore'))
        self.title = title
        if title is not None:
            directlyProvides(self, ITitledTokenizedTerm)  # noqa


@implementer(IVocabularyTokenized)
class SimpleVocabulary(object):
    """Vocabulary that works from a sequence of terms."""

    def __init__(self, terms, *interfaces, **kwargs):
        """Initialize the vocabulary given a list of terms.

        The vocabulary keeps a reference to the list of terms passed
        in; it should never be modified while the vocabulary is used.

        One or more interfaces may also be provided so that alternate
        widgets may be bound without subclassing.

        By default, ValueErrors are thrown if duplicate values or tokens
        are passed in. If you want to swallow these exceptions, pass
        in swallow_duplicates=True. In this case, the values will
        override themselves.
        """
        self.by_value = {}
        self.by_token = {}
        self._terms = terms
        for term in self._terms:
            swallow_dupes = kwargs.get('swallow_duplicates', False)
            if not swallow_dupes:
                if term.value in self.by_value:
                    raise ValueError(
                        'term values must be unique: %s' % repr(term.value))
                if term.token in self.by_token:
                    raise ValueError(
                        'term tokens must be unique: %s' % repr(term.token))
            self.by_value[term.value] = term
            self.by_token[term.token] = term
        if interfaces:
            directlyProvides(self, *interfaces)  # noqa

    @classmethod
    def fromItems(cls, items, *interfaces):
        """Construct a vocabulary from a list of (token, value) pairs.

        The order of the items is preserved as the order of the terms
        in the vocabulary.  Terms are created by calling the class
        method createTerm() with the pair (value, token).

        One or more interfaces may also be provided so that alternate
        widgets may be bound without subclassing.
        """
        terms = [cls.createTerm(value, token) for (token, value) in items]
        return cls(terms, *interfaces)

    @classmethod
    def fromValues(cls, values, *interfaces):
        """Construct a vocabulary from a simple list.

        Values of the list become both the tokens and values of the
        terms in the vocabulary.  The order of the values is preserved
        as the order of the terms in the vocabulary.  Tokens are
        created by calling the class method createTerm() with the
        value as the only parameter.

        One or more interfaces may also be provided so that alternate
        widgets may be bound without subclassing.
        """
        terms = [cls.createTerm(value) for value in values]
        return cls(terms, *interfaces)

    @classmethod
    def createTerm(cls, *args):
        """Create a single term from data.

        Subclasses may override this with a class method that creates
        a term of the appropriate type from the arguments.
        """
        return SimpleTerm(*args)

    def __contains__(self, value):
        """See guillotina.schema.interfaces.IBaseVocabulary"""
        try:
            return value in self.by_value
        except TypeError:
            # sometimes values are not hashable
            return False

    def getTerm(self, value):
        """See guillotina.schema.interfaces.IBaseVocabulary"""
        try:
            return self.by_value[value]
        except KeyError:
            raise LookupError(value)

    def getTermByToken(self, token):
        """See guillotina.schema.interfaces.IVocabularyTokenized"""
        try:
            return self.by_token[token]
        except KeyError:
            raise LookupError(token)

    def __iter__(self):
        """See guillotina.schema.interfaces.IIterableVocabulary"""
        return iter(self._terms)

    def __len__(self):
        """See guillotina.schema.interfaces.IIterableVocabulary"""
        return len(self.by_value)


def _createTermTree(ttree, dict_):
    """ Helper method that creates a tree-like dict with ITokenizedTerm
    objects as keys from a similar tree with tuples as keys.

    See fromDict for more details.
    """
    for key in sorted(dict_.keys()):
        term = SimpleTerm(key[1], key[0], key[-1])
        ttree[term] = TreeVocabulary.terms_factory()
        _createTermTree(ttree[term], dict_[key])
    return ttree


@implementer(ITreeVocabulary)
class TreeVocabulary(object):
    """ Vocabulary that relies on a tree (i.e nested) structure.
    """
    # The default implementation uses a dict to create the tree structure. This
    # can however be overridden in a subclass by any other IEnumerableMapping
    # compliant object type. Python 2.7's OrderedDict for example.
    terms_factory = OrderedDict

    def __init__(self, terms, *interfaces):
        """Initialize the vocabulary given a recursive dict (i.e a tree) with
        ITokenizedTerm objects for keys and self-similar dicts representing the
        branches for values.

        Refer to the method fromDict for more details.

        Concerning the ITokenizedTerm keys, the 'value' and 'token' attributes
        of each key (including nested ones) must be unique.

        One or more interfaces may also be provided so that alternate
        widgets may be bound without subclassing.
        """
        self._terms = self.terms_factory()
        self._terms.update(terms)

        self.path_by_value = {}
        self.term_by_value = {}
        self.term_by_token = {}
        self._populateIndexes(terms)

        if interfaces:
            directlyProvides(self, *interfaces)  # noqa

    def __contains__(self, value):
        """ See guillotina.schema.interfaces.IBaseVocabulary

        D.__contains__(k) -> True if D has a key k, else False
        """
        try:
            return value in self.term_by_value
        except TypeError:
            # sometimes values are not hashable
            return False

    def __getitem__(self, key):
        """x.__getitem__(y) <==> x[y]
        """
        return self._terms.__getitem__(key)

    def __iter__(self):
        """See guillotina.schema.interfaces.IIterableVocabulary

        x.__iter__() <==> iter(x)
        """
        return self._terms.__iter__()

    def __len__(self):
        """x.__len__() <==> len(x)
        """
        return self._terms.__len__()

    def get(self, key, default=None):
        """Get a value for a key

        The default is returned if there is no value for the key.
        """
        return self._terms.get(key, default)

    def keys(self):
        """Return the keys of the mapping object.
        """
        return self._terms.keys()

    def values(self):
        """Return the values of the mapping object.
        """
        return self._terms.values()

    def items(self):
        """Return the items of the mapping object.
        """
        return self._terms.items()

    @classmethod
    def fromDict(cls, dict_, *interfaces):
        """Constructs a vocabulary from a dictionary-like object (like dict or
        OrderedDict), that has tuples for keys.

        The tuples should have either 2 or 3 values, i.e:
        (token, value, title) or (token, value)

        For example, a dict with 2-valued tuples:

        dict_ = {
            ('exampleregions', 'Regions used in ATVocabExample'): {
                ('aut', 'Austria'): {
                    ('tyr', 'Tyrol'): {
                        ('auss', 'Ausserfern'): {},
                    }
                },
                ('ger', 'Germany'): {
                    ('bav', 'Bavaria'):{}
                },
            }
        }
        One or more interfaces may also be provided so that alternate
        widgets may be bound without subclassing.
        """
        return cls(_createTermTree(cls.terms_factory(), dict_), *interfaces)

    def _populateIndexes(self, tree):
        """ The TreeVocabulary contains three helper indexes for quick lookups.
        They are: term_by_value, term_by_token and path_by_value

        This method recurses through the tree and populates these indexes.

        tree:  The tree (a nested/recursive dictionary).
        """
        for term in tree.keys():
            value = getattr(term, 'value')
            token = getattr(term, 'token')

            if value in self.term_by_value:
                raise ValueError(
                    "Term values must be unique: '%s'" % value)

            if token in self.term_by_token:
                raise ValueError(
                    "Term tokens must be unique: '%s'" % token)

            self.term_by_value[value] = term
            self.term_by_token[token] = term

            if value not in self.path_by_value:
                self.path_by_value[value] = self._getPathToTreeNode(self,
                                                                    value)
            self._populateIndexes(tree[term])

    def getTerm(self, value):
        """See guillotina.schema.interfaces.IBaseVocabulary"""
        try:
            return self.term_by_value[value]
        except KeyError:
            raise LookupError(value)

    def getTermByToken(self, token):
        """See guillotina.schema.interfaces.IVocabularyTokenized"""
        try:
            return self.term_by_token[token]
        except KeyError:
            raise LookupError(token)

    def _getPathToTreeNode(self, tree, node):
        """Helper method that computes the path in the tree from the root
        to the given node.

        The tree must be a recursive IEnumerableMapping object.
        """
        path = []
        for parent, child in tree.items():
            if node == parent.value:
                return [node]
            path = self._getPathToTreeNode(child, node)
            if path:
                path.insert(0, parent.value)
                break
        return path

    def getTermPath(self, value):
        """Returns a list of strings representing the path from the root node
        to the node with the given value in the tree.

        Returns an empty string if no node has that value.
        """
        return self.path_by_value.get(value, [])


# registry code
class VocabularyRegistryError(LookupError):
    def __init__(self, name):
        self.name = name
        Exception.__init__(self, str(self))

    def __str__(self):
        return "unknown vocabulary: %r" % self.name


@implementer(IVocabularyRegistry)
class VocabularyRegistry(object):
    __slots__ = '_map',

    def __init__(self):
        self._map = {}

    def get(self, object, name):
        """See guillotina.schema.interfaces.IVocabularyRegistry"""
        try:
            vtype = self._map[name]
        except KeyError:
            raise VocabularyRegistryError(name)
        return vtype(object)

    def register(self, name, factory):
        self._map[name] = factory


_vocabularies = None


def getVocabularyRegistry():
    """Return the vocabulary registry.

    If the registry has not been created yet, an instance of
    VocabularyRegistry will be installed and used.
    """
    if _vocabularies is None:
        setVocabularyRegistry(VocabularyRegistry())
    return _vocabularies


def setVocabularyRegistry(registry):
    """Set the vocabulary registry."""
    global _vocabularies
    _vocabularies = registry


def _clear():
    """Remove the registries (for use by tests)."""
    global _vocabularies
    _vocabularies = None
