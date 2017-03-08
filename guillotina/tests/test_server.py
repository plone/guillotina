# -*- coding: utf-8 -*-
from guillotina.traversal import TraversalRouter


def test_make_app(dummy_guillotina):
    assert dummy_guillotina is not None
    assert type(dummy_guillotina.router) == TraversalRouter
