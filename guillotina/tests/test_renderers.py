from datetime import datetime
from guillotina.renderers import guillotina_json_default

import pytest


def test_guillotina_json_default_doesnt_serialize_datetime():
    def _makeOne(obj):
        return guillotina_json_default(obj)

    with pytest.raises(TypeError):
        assert _makeOne(datetime(2020, 1, 1))
