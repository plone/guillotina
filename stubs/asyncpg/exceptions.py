class PostgresConnectionError(Exception):
    ...


class InterfaceError(Exception):
    ...


class InternalClientError(Exception):
    ...


class InvalidCatalogNameError(Exception):
    ...


class ConnectionDoesNotExistError(Exception):
    ...


class UndefinedTableError(Exception):
    ...


class UniqueViolationError(Exception):
    ...


class ForeignKeyViolationError(Exception):
    ...


class DeadlockDetectedError(Exception):
    ...
