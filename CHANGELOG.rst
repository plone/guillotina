CHANGELOG
=========

5.0.15 (unreleased)
-------------------

- Provide workaround for asyncio contextvars ipython bug in shell
  [vangheem]


5.0.14 (2019-10-02)
-------------------

- Throw an `TransactionObjectRegistrationMismatchException` exception if you attempt to
  register an object with a transaction that is a different than existing registration
  for that object.
  [vangheem]


5.0.13 (2019-09-27)
-------------------

- Case insensitive environ `G_` variable lookup
  [svx]

- Improve reST syntax of README
  [svx]

- Fix typo in CHANGELOG
  [svx]

5.0.12 (2019-09-24)
-------------------

- Fix shut down for redis pubsub driver
  [vangheem]

- Swagger url support for X-Forwarded-Proto and X-Forwarded-Schema
  [bloodbare]


5.0.11 (2019-09-18)
-------------------

- Fix patch field delete to handle when value is None
  [vangheem]

- Adjust Sphinx to build in parallel
  [svx]


5.0.10 (2019-09-06)
-------------------

- Be able to use guillotina's types in 3rd party apps
  [vangheem]


5.0.9 (2019-09-05)
------------------

- Handle errors vacuuming
  [vangheem]


5.0.8 (2019-09-05)
------------------

- pypi package desc fix


5.0.7 (2019-09-05)
------------------

- Explicitly reset task vars on every request
  [vangheem]

- Fix futures execute error when no futures are defined for type
  [vangheem]


5.0.6 (2019-09-04)
------------------

- Fix `execute.clear_futures()`
  [vangheem]

- Adding Helm Charts
  [karannaoh]

5.0.4 (2019-09-04)
------------------

- Upgrade mypy
  [vangheem]

- Fix not setting cache values for updated object when push is not enabled
  [vangheem]

- Fix conflict error handling with registry objects
  [vangheem]

- Sorted imports in all files and added `isort` in .travis to keep the format
  [masipcat]


5.0.3 (2019-09-02)
------------------

- `BaseObject.__txn__` now weakref to prevent reference cycles
  [vangheem]

- Change default service registration to work without inline defined klass methods
  [vangheem]

- Fix doc builds for new open api 3
  [vangheem]

- Fix getting cache value from redis
  [vangheem]

- Fix calculating in-memory cache size
  [vangheem]

- Update Makefile [svx]
- Remove buildout bits [svx]

5.0.2 (2019-08-30)
------------------

- Fix json schema validation
  [vangheem]

- Fix memory cache to be able to calc size properly
  [vangheem]

- Better redis pubsub error handling
  [vangheem]


5.0.1 (2019-08-30)
------------------

- Be not log verbose when pubsub utility task is cancelled
  [vangheem]


5.0.0 (2019-08-30)
------------------

- Be able to configure cache to not push pickles with invalidation data
  [vangheem]

- Fix transaction handling to always get current active transaction, throw exception
  when transaction is closed and be able to refresh objects.
  [vangheem]

- More normalization of execute module with task_vars/request objects
  [vangheem]

- Allow committing objects that were created with different transaction
  [vangheem]

- Fix async utils to work correctly with transactions and context vars
  [vangheem]

- Be able to have `None` default field values
  [vangheem]


5.0.0a16 (2019-08-26)
---------------------

- Throw exception when saving object to closed transaction
  [vangheem]

- Fix cache key for SQLStatements cache. This was causing vacuuming on multi-db environments
  to not work since the vacuuming object was shared between dbs on guillotina_dynamictablestorage.
  [vangheem]

- Refractor and bug fix in validation of parameter

- Implement more optimized way to vacuum objects which dramatically improves handling
  of deleting very large object trees
  [vangheem]

- Fix `LightweightConnection` pg class to close active cursors when connection done
  [vangheem]

- Swagger doc for search endpoint
  [karannaoh]

- Fix `modification_date` not indexed when an object is patched
  [masipcat]

- Move to black code formatter
  [vangheem]

- Fix field.validate() crashes when providing invalid schema (for field of type Object)
  [masipcat]

- Upgrade to Swagger 3/Open API 3
  [karannaoh]

- Implement json schema validation
  [karannaoh]


5.0.0a15 (2019-08-02)
---------------------

- Dict schema serialization needs properties to be valid JSON Schema
  [bloodbare]

- Fix potential bug when working with multiple databases/transaction managers
  [vangheem]

- New `guillotina.fields.BucketDictField`
  [vangheem]

- New `@fieldvalue/{field name or dotted behavior + field name}` endpoint
  [vangheem]


5.0.0a14 (2019-07-30)
---------------------

- Leaking txn on reindex on pg
  [bloodbare]


5.0.0a13 (2019-07-29)
---------------------

- Run default factory on attributes on behaviors
  [bloodbare]

- Allow to get full object serialization on GET operation
  [bloodbare]

- Only register object for writing if base object changed. Otherwise, changes to behavior data
  was also causing writes to the object it was associated with
  [vangheem]

- Add `x-virtualhost-path` header support for url generation
  [vangheem]


5.0.0a12 (2019-07-26)
---------------------

- Make Tuple type work with patch field
  [vangheem]

- Make IDublinCore.tags a patch field
  [vangheem]

- Add `appendunique` and `extendunique` to patch field operations
  [vangheem]

- Fix exhausted retries conflict error response
  [vangheem]

- Make sure field name of patch field is set before using
  [vangheem]

- Improve request memory usage
  [vangheem]

- Fix: just skip indexing attributes from schemas that object does not
  adapt to [lferran]


5.0.0a11 (2019-07-22)
---------------------

- Allow to receive a fullobject serialization on search
  [bloodbare]

- Allow to reindex on PG catalog implementation
  [bloodbare]

- Read only txn can be reused without changing read only param
  [bloodbare]

- Merge CORS headers
  [qiwn]

- Fix redis pubsub potential cpu bound deadlock
  [vangheem]

- Make sure that channel is configured on cache pubsub
  [bloodbare]

- Handle cancelled error on cleanup
  [vangheem]

- Define TTL on cache set
  [bloodbare]

- Logging async util exception
  [bloodbare]

- Documentation improvements
  [vangheem]

- Cache JSONField schema validator object
  [vangheem]

- JSONField works with dict instead of requiring str(which is then converted to dict anyways)
  [vangheem]


5.0.0a10 (2019-06-27)
---------------------

- Adding store_json property on db configuration so we can disable json storage for each db.
  [bloodbare]


5.0.0a9 (2019-06-27)
--------------------

- Move guillotina_mailer to guillotina.contrib.mailer
  [bloodbare]

- Be able to customize the object reader function with the `object_reader` setting
  [vangheem]

- Fix indexing data potentially missing updated content when `fields` for accessor
  is not specified
  [vangheem]

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
