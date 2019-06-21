CHANGELOG
=========

5.0.0a4 (unreleased)
--------------------

- Fix path__startswith query
  [vangheem]


5.0.0a3 (2019-06-21)
--------------------

- Add `guillotina.contrib.swagger`


5.0.0a2 (2019-06-19)
--------------------

- Missing mypy requirement
- Fix catalog interface
- Fix catalog not working with db schemas
- Update intro docs


5.0.0a1 (2019-06-19)
--------------------

- Fix events antipattern [lferran]

- Rename `utils.get_object_by_oid` to `utils.get_object_by_uid`

- Emit events for registry configuration changes

- Default catalog interface removes the following methods: `get_by_uuid`, `get_by_type`, `get_by_path`,
  `get_folder_contents`. Keep interfaces simple, use search/query.

- Allow modifying app settings from pytest marks [lferran]

- No longer setup fake request with login for base command

- Moved `ISecurityPolicy.cached_principals` to module level function `guillotina.security.policy.cached_principals`

- Moved `ISecurityPolicy.cached_roles` to module level function `guillotina.security.policy.cached_roles`

- `utils.get_authenticated_user_id` no longer accepts `request` param

- `utils.get_authenticated_user` no longer accepts `request` param

- Removed `guillotina.exceptions.NoInteraction`

- Removed `guillotina.interfaces.IInteraction`

- `auth_user_identifiers` no longer accept `IRequest` in the constructor. Use `utils.get_current_request`

- `auth_user_identifiers` no longer accept `IRequest` in constructor. Use `utils.get_current_request`

- Remove `IInteraction`. Use `guillotina.utils.get_security_policy()`

- Remove `Request._db_write_enabled`, `Transaction` now has `read_only` property

- Remove `Request._db_id`, Use `guillotina.task_vars.db.get().id`

- Remove `Request.container_settings`, Use `guillotina.utils.get_registry`

- Remove `Request._container_id`, use `guillotina.task_vars.container.get().id`

- Remove `Request.container`, Use `guillotina.task_vars.container.get()`

- Remove `Request.add_future`. Use `guillotina.utils.execute.add_future`

- Add `guillotina.utils.get_current_container`

- Rename `request_indexer` setting to `indexer`

- Rename `guillotina.catalog.index.RequestIndexer` to `guillotina.catalog.index.Indexer`

- Rename `IWriter.parent_id` to `IWriter.parent_uid`

- Rename `guillotina.db.oid` to `guillotina.db.uid`

- Rename `oid_generate` setting to `uid_generator`

- Rename `BaseObject._p_register` -> `BaseObject.register`

- Rename `BaseObject._p_serial` -> `BaseObject.__serial__`

- Rename `BaseObject._p_oid` -> `BaseObject.__uuid__`

- Rename `BaseObject._p_jar` -> `BaseObject.__txn__`

- separate transaction from request object

- rename `guillotina.transactions.managed_transaction` to `guillotina.transactions.transaction`
