from guillotina import task_vars
from guillotina.db.interfaces import IPostgresStorage
from guillotina.interfaces import IAddons
from guillotina.response import HTTPPreconditionFailed
from guillotina.transactions import get_transaction


def oauth_container_db_key(container):
    txn = get_transaction()
    db_id = None
    if txn is not None:
        db_id = getattr(getattr(txn, "manager", None), "db_id", None)
    if not db_id:
        db = task_vars.db.get(None)
        db_id = getattr(db, "id", None) or getattr(db, "__db_id__", None)
    if not db_id:
        raise RuntimeError("OAuth storage requires an active database context")
    return f"{db_id}/{container.id}"


def is_installed(container):
    registry = task_vars.registry.get(None)
    if registry is None:
        return False
    try:
        return "oauth" in registry.for_interface(IAddons)["enabled"]
    except Exception:
        return False


def get_oauth_store(container, *, require_installed=True):
    if require_installed and not is_installed(container):
        raise HTTPPreconditionFailed(content={"reason": "OAuth addon is not installed"})
    txn = get_transaction()
    if txn is None or not IPostgresStorage.providedBy(txn.storage):
        raise RuntimeError(
            "OAuth storage requires PostgreSQL but the active database storage is not PostgreSQL"
        )
    from guillotina.contrib.oauth.storage.pg.repository import OAuthRepository

    return OAuthRepository(oauth_container_db_key(container))
