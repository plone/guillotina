from datetime import datetime
from guillotina.renderers import guillotina_json_default

import unittest


class Test_guillotina_json_default(unittest.TestCase):
    def _makeOne(self, obj):
        return guillotina_json_default(obj)

    def test_datetime(self):
        date = datetime(2020, 1, 1)
        self.assertEquals(self._makeOne(date), date.isoformat())
