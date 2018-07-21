# Component Architecture

Guillotina is built on a component architecture. The component
architecture uses adapter and singleton software design patterns
to help manage complexity. It allows users to register and lookup
adapters and utility defined against interfaces.


## Why

> program to an interface, not an implementation

> favor object composition over class inheritance

> keep objects stupid

The component architecture is a powerful tool to help you build
complex software that needs to be extensible. In software
engineering, adapters and singletons are used often so it is
a natural pattern to build on.

Almost any component/functionality in Guillotina can be
overridden in an add-on application by overriding Guillotina's
components.

## Basics

To query an adapter on content:

```python
from guillotina.component import get_adapter
from guillotina.interfaces import IResource
from zope.interface import Interface
from guillotina import configure

class IMyAdapter(Interface):
    pass

@configure.adapter(for_=IResource, provides=IMyAdapter)
class MyAdapter:
    def __init__(self, ob):
        self.ob = ob

    def do_something(self):
        pass

adapter = get_adapter(ob, IMyAdapter)
adapter.do_something()
```

To query for a utility(which is what we call singletons), it's similiar:

```python
from guillotina.component import get_utility
from guillotina.interfaces import IPermission
permission = get_utility(IPermission, name='guillotina.AccessContent')
```

## Details

To describe power of this approach, we'll go through
using adapters without the registration and lookup
and then with the component architecture.


### Adapters without CA

```python
class Automobile:
    wheels = 4

    def __init__(self):
        pass


class Motorcycle(Automobile):
    wheels = 2


class SemiTruck(Automobile):
    wheels = 18


class Operate:

    def __init__(self, automobile: Automobile):
        self.automobile = automobile

    def drive(self):
        pass


class OperateMotocycle:

    def drive(self):
        pass


class OperateSemi:

    def drive(self):
        pass
```

Then, to use these adapters, you might do something like:

```python
if isinstance(auto, SemiTruck):
    operate = OperateSemi(auto)
elif isinstance(auto, Motorcycle):
    operate = OperateMotocycle(auto)
else:
    operate = Operate(auto)
operate.drive()
```


### Adapters with CA

```python
from guillotina import configure
from zope.interface import Attribute, Interface, implementer


class IAutomobile(Interface):
    wheels = Attribute('number of wheels')


class IMotocycle(IAutomobile):
    pass


class ISemiTruck(IAutomobile):
    pass


@implementer(IAutomobile)
class Automobile:
    wheels = 4


@implementer(IMotocycle)
class Motorcycle(Automobile):
    wheels = 2


@implementer(ISemiTruck)
class SemiTruck(Automobile):
    wheels = 18


class IOperate(Interface):
    def drive():
        pass


@configure.adapter(for_=IAutomobile, provides=IOperate)
class Operate:

    def __init__(self, automobile: Automobile):
        self.automobile = automobile

    def drive(self):
        return 'driving automobile'


@configure.adapter(for_=IMotocycle, provides=IOperate)
class OperateMotocycle(Operate):

    def drive(self):
        return 'driving motocycle'


@configure.adapter(for_=ISemiTruck, provides=IOperate)
class OperateSemi(Operate):

    def drive(self):
        return 'driving semi'
```


Then, to use it:


```python
from guillotina.component import get_adapter
semi = SemiTruck()
operate = get_adapter(semi, IOperate)
operate.drive()
```
