from guillotina.schema.utils import get_default_from_schema


_EMPTY = object()


class ContextProperty:
    def __init__(self, attribute, default=_EMPTY):
        self.__name__ = attribute
        self.default = default

    def __get__(self, inst, klass):
        if inst is None:
            return self

        result = getattr(inst.context, self.__name__, self.default)
        if callable(result):
            result = result(context=inst.context, name=self.__name__)
        if result == _EMPTY:
            return get_default_from_schema(inst.context, inst.schema, self.__name__)
        return result

    def __set__(self, inst, value):
        setattr(inst.context, self.__name__, value)
        inst.context.register()


class FunctionProperty:
    def __init__(self, attribute, getter, setter):
        self.__name__ = attribute
        self.setter = setter
        self.getter = getter

    def __get__(self, inst, klass):
        if inst is None:
            return self

        return self.getter(inst)

    def __set__(self, inst, value):
        return self.setter(inst, value)
