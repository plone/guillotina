from guillotina.content import Folder
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces import IDatabase
from zope.interface import implementer_only


@implementer_only(IDatabase, IBaseObject)
class Root(Folder):

    __name__ = None
    __immutable_cache__ = True
    __db_id__ = None
    type_name = "GuillotinaDBRoot"
    migration_version = "1.0.0"  # base version

    def __init__(self, db_id):
        super().__init__()
        self.__db_id__ = db_id

    def __repr__(self):
        return "<Database %d>" % id(self)
