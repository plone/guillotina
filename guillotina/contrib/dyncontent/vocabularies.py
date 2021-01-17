from guillotina import app_settings
from guillotina import configure
from guillotina.contrib.dyncontent.exceptions import VocabularySettingNotFound
from guillotina.schema.interfaces import ISource
from zope.interface import implementer


@implementer(ISource)
class AppSettingSource:
    def __init__(self, dotted_setting, missing=None):
        self.dotted_setting = dotted_setting
        self.missing = missing
        self._values = None  # lazy load them

    @property
    def values(self):
        if self._values is not None:
            return self._values
        context = app_settings
        for part in self.dotted_setting.split("."):
            if part in context:
                context = context[part]
            else:
                if self.missing is not None:
                    return self.missing
                else:
                    raise VocabularySettingNotFound(self.dotted_setting)
        self._values = context
        return context

    def keys(self):
        return [k for k, v in self.values]

    def __iter__(self):
        return iter(self.keys())

    def __contains__(self, value):
        return value in self.keys()

    def __len__(self):
        return len(self.values)

    def getTerm(self, value):
        for k, v in self.values:
            if k == value:
                return value
        raise KeyError(value)


@configure.value_serializer(AppSettingSource)
def app_setting_source_serializer(value):
    return value.keys()
