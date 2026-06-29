from contextvars import ContextVar
from typing import Dict, Optional

from guillotina.db.interfaces import ITransaction, ITransactionManager
from guillotina.interfaces import IContainer, IDatabase, IPrincipal, IRegistry, IRequest, ISecurityPolicy


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
