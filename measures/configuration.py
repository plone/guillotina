from guillotina import configure
from guillotina import schema
from guillotina.behaviors.instance import AnnotationBehavior
from guillotina.content import Item
from guillotina.interfaces import IItem
from zope.interface import Interface


class IMarkerBehavior1(Interface):
    pass

class IMarkerBehavior2(Interface):
    pass

class IMarkerBehavior3(Interface):
    pass

class ITestBehavior1(Interface):
    foobar = schema.TextLine()

class ITestBehavior2(Interface):
    foobar = schema.TextLine()

class ITestBehavior3(Interface):
    foobar = schema.TextLine()


@configure.behavior(
    title="",
    provides=ITestBehavior1,
    marker=IMarkerBehavior1,
    for_="guillotina.interfaces.IResource")
class TestBehavior1(AnnotationBehavior):
    pass


@configure.behavior(
    title="",
    provides=ITestBehavior2,
    marker=IMarkerBehavior2,
    for_="guillotina.interfaces.IResource")
class TestBehavior2(AnnotationBehavior):
    pass


@configure.behavior(
    title="",
    provides=ITestBehavior3,
    marker=IMarkerBehavior3,
    for_="guillotina.interfaces.IResource")
class TestBehavior3(AnnotationBehavior):
    pass


class ITestContent1(IItem):
    foobar1 = schema.TextLine()


class ITestContent2(ITestContent1):
    foobar2 = schema.TextLine()


class ITestContent3(ITestContent2):
    foobar3 = schema.TextLine()


class ITestContent4(ITestContent3):
    foobar4 = schema.TextLine()


class ITestContent5(ITestContent4):
    foobar5 = schema.TextLine()


class ITestContent6(ITestContent5):
    foobar6 = schema.TextLine()


@configure.contenttype(
    type_name="TestContent1",
    schema=ITestContent1,
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore",
        "measures.configuration.ITestBehavior1",
        "measures.configuration.ITestBehavior2",
        "measures.configuration.ITestBehavior3",
    ])
class TestContent1(Item):
    pass


@configure.contenttype(
    type_name="TestContent6",
    schema=ITestContent6,
    behaviors=[
        "guillotina.behaviors.dublincore.IDublinCore",
        "measures.configuration.ITestBehavior1",
        "measures.configuration.ITestBehavior2",
        "measures.configuration.ITestBehavior3",
    ])
class TestContent6(Item):
    pass
