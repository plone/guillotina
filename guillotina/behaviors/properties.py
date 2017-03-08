

class ContextProperty(object):

    def __init__(self, attribute, default):
        self.__name__ = attribute
        self.default = default

    def __get__(self, inst, klass):
        if inst is None:
            return self

        if hasattr(inst.context, self.__name__):
            return getattr(inst.context, self.__name__, self.default)
        else:
            raise AttributeError('{field} not found on {context}'.format(
                field=self.__name__, context=str(inst.context)))

    def __set__(self, inst, value):
        if hasattr(inst.context, self.__name__):
            setattr(inst.context, self.__name__, value)
            inst.context._p_register()
        else:
            raise AttributeError('{field} not found on {context}'.format(
                field=self.__name__, context=str(inst.context)))


class FunctionProperty(object):

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
