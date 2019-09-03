from contextvars import ContextVar
from guillotina.db.interfaces import ITransaction
from guillotina.db.interfaces import ITransactionManager
from guillotina.interfaces import IContainer
from guillotina.interfaces import IDatabase
from guillotina.interfaces import IPrincipal
from guillotina.interfaces import IRegistry
from guillotina.interfaces import IRequest
from guillotina.interfaces import ISecurityPolicy
from typing import Dict
from typing import Optional


request: ContextVar[Optional[IRequest]] = ContextVar("g_request", default=None)
txn: ContextVar[Optional[ITransaction]] = ContextVar("g_txn", default=None)
tm: ContextVar[Optional[ITransactionManager]] = ContextVar("g_tm", default=None)
futures: ContextVar[Optional[Dict]] = ContextVar("g_futures", default=None)
authenticated_user: ContextVar[Optional[IPrincipal]] = ContextVar("g_authenticated_user", default=None)
security_policies: ContextVar[Optional[Dict[str, ISecurityPolicy]]] = ContextVar(
    "g_security_policy", default=None
)
container: ContextVar[Optional[IContainer]] = ContextVar("g_container", default=None)
registry: ContextVar[Optional[IRegistry]] = ContextVar("g_container", default=None)
db: ContextVar[Optional[IDatabase]] = ContextVar("g_database", default=None)
