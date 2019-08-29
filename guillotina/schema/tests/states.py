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
# flake8: noqa
from guillotina.schema import Choice
from guillotina.schema import interfaces
from zope.interface import implementer


# This table is based on information from the United States Postal Service:
# http://www.usps.com/ncsc/lookups/abbreviations.html#states
_states = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AS": "American Samoa",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "DC": "District of Columbia",
    "FM": "Federated States of Micronesia",
    "FL": "Florida",
    "GA": "Georgia",
    "GU": "Guam",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MH": "Marshall Islands",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "MP": "Northern Mariana Islands",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PW": "Palau",
    "PA": "Pennsylvania",
    "PR": "Puerto Rico",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VI": "Virgin Islands",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


@implementer(interfaces.ITerm)
class State(object):
    __slots__ = "value", "title"

    def __init__(self, value, title):
        self.value = value
        self.title = title


for v, p in _states.items():
    _states[v] = State(v, p)  # type: ignore


class IStateVocabulary(interfaces.IVocabulary):
    """Vocabularies that support the states database conform to this."""


@implementer(IStateVocabulary)
class StateVocabulary(object):
    __slots__ = ()

    def __init__(self, object=None):
        pass

    def __contains__(self, value):
        return value in _states

    def __iter__(self):
        return iter(_states.values())

    def __len__(self):
        return len(_states)

    def getTerm(self, value):
        return _states[value]


class StateSelectionField(Choice):

    vocabulary = StateVocabulary()

    def __init__(self, **kw):
        super(StateSelectionField, self).__init__(vocabulary=StateSelectionField.vocabulary, **kw)
        self.vocabularyName = "states"
