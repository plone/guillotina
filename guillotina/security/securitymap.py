from guillotina import task_vars


class SecurityMap:
    def __init__(self):
        self._clear()

    def _clear(self):
        self._byrow = {}
        self._bycol = {}

    def __nonzero__(self):
        return bool(self._byrow)

    def add_cell(self, rowentry, colentry, value):
        # setdefault may get expensive if an empty mapping is
        # expensive to create, for PersistentDict for instance.
        row = self._byrow.get(rowentry)
        if row:
            if row.get(colentry) is value:
                return False
        else:
            row = self._byrow[rowentry] = {}

        col = self._bycol.get(colentry)
        if not col:
            col = self._bycol[colentry] = {}

        row[colentry] = value
        col[rowentry] = value

        self._invalidated_policy_cache()

        return True

    def _invalidated_policy_cache(self):
        policies = task_vars.security_policies.get() or {}
        policies.clear()

    def del_cell(self, rowentry, colentry):
        row = self._byrow.get(rowentry)
        if row and (colentry in row):
            del row[colentry]
            if not row:
                del self._byrow[rowentry]
            col = self._bycol[colentry]
            del col[rowentry]
            if not col:
                del self._bycol[colentry]

            self._invalidated_policy_cache()

            return True

        return False

    def query_cell(self, rowentry, colentry, default=None):
        row = self._byrow.get(rowentry)
        if row:
            return row.get(colentry, default)
        else:
            return default

    def get_cell(self, rowentry, colentry):
        marker = object()
        cell = self.queryCell(rowentry, colentry, marker)
        if cell is marker:
            raise KeyError("Not a valid row and column pair.")
        return cell

    def get_row(self, rowentry):
        row = self._byrow.get(rowentry)
        if row:
            return list(row.items())
        else:
            return []

    def get_col(self, colentry):
        col = self._bycol.get(colentry)
        if col:
            return list(col.items())
        else:
            return []

    def get_all_cells(self):
        res = []
        for r in self._byrow.keys():
            for c in self._byrow[r].items():
                res.append((r,) + c)
        return res


class GuillotinaSecurityMap(SecurityMap):
    def __init__(self, context):
        self.context = context
        map = self.context.acl.get(self.key)
        if map is None:
            self._byrow = {}
            self._bycol = {}
        else:
            self._byrow = map._byrow
            self._bycol = map._bycol
        self.map = map

    def _invalidated_policy_cache(self):
        super()._invalidated_policy_cache()
        try:
            del self.context.__volatile__["security_cache"]
        except KeyError:
            pass

    def _changed(self):
        map = self.map
        if self.context.__acl__ is None:
            self.context.__acl__ = dict({})
        if map is None:
            map = SecurityMap()
            map._byrow = self._byrow
            map._bycol = self._bycol
            self.context.__acl__[self.key] = map
        self.context.register()

    def add_cell(self, rowentry, colentry, value):
        if super().add_cell(rowentry, colentry, value):
            self._changed()

    def del_cell(self, rowentry, colentry):
        if super().del_cell(rowentry, colentry):
            self._changed()
