CHANGELOG
=========

5.0.0a9 (unreleased)
--------------------

- Executioner:
    - providing pagination support in navigation (1.2.0)
    - supporting token authentication from login form (1.3.0)
    - using @search endpoint to navigate in container items

- A few more python antipattern fixes [lferran]

5.0.0a8 (2019-06-23)
--------------------

- Aggregations in PG JSONb
  [bloodbare]


5.0.0a7 (2019-06-22)
--------------------

- Change `guillotina.files.utils.generate_key` to not accept a `request` parameter. It was
  used to get the container id which is now a context var.
  [vangheem]

- Add `IExternalFileStorageManager` interface to be able to designate a file storage that
  store a file into an external database. This enables you to automatically leverage the
  `redis` data manager.

- Add `cloud_datamanager` setting. Allows you to select between `db`(default) and
  `redis`(if `guillotina.contrib.redis` is used) to not write to db to maintain state.
  The `redis` option is only usable for gcloud and s3 adapters.

5.0.0a6 (2019-06-22)
--------------------

- Cache password checked decisions to fix basic auth support
  [vangheem]

- Make sure you can import contrib packages without automatically activating them
  [vangheem]

5.0.0a5 (2019-06-22)
--------------------
- Adding rediscache and pubsub logic. Now you can have memory cache, network cache with invalidation
  and pubsub service. `guillotina_rediscache` is not necessary any more.
  [bloodbare]


- deprecate `__local__properties__`. `ContextProperty` works on it's own now
  [vangheem]

- Add argon2 pw hashing
  [vangheem]

- Completely remove support for `utilities` configuration. Use `load_utilities`.
  [vangheem]

5.0.0a4 (2019-06-21)
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
