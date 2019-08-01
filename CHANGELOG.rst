CHANGELOG
=========

5.0.0a15 (unreleased)
---------------------

- Fix potential bug when working with multiple databases/transaction managers
  [vangheem]

- New `guillotina.fields.BucketDictField`
  [vangheem]

- New `@fieldvalue/{field name or dotted behavior + field name}` endpoint
  [vangheem]


4.8.19 (2019-07-28)
-------------------

- Only register object for writing if base object changed. Otherwise, changes to behavior data
  was also causing writes to the object it was associated with
  [vangheem]


4.8.18 (2019-07-26)
-------------------

- Add `x-virtualhost-path` header support for url generation
  [vangheem]


4.8.17 (2019-07-25)
-------------------

- Make Tuple type work with patch field
  [vangheem]

- Make IDublinCore.tags a patch field
  [vangheem]

- Add `appendunique` and `extendunique` to patch field operations
  [vangheem]


4.8.16 (2019-07-24)
-------------------

- Fix exhausted retries conflict error response
  [vangheem]


4.8.15 (2019-07-23)
-------------------

- Make sure field name of patch field is set before using
  [vangheem]


4.8.14 (2019-07-23)
-------------------

- Fix: just skip indexing attributes from schemas that object does not
  adapt to [lferran]

- Improve request memory usage
  [vangheem]


4.8.13 (2019-07-15)
-------------------

- Allow modifying app settings from pytest marks [lferran]

- Merge CORS headers
  [qiwn]

- Fix `managed_transaction()` crashes when `request` and `tm` are not provided
  [masipcat]


4.8.12 (2019-07-08)
-------------------

- Handle CancelledError on application cleanup. This seems to happen with uvloop
  [vangheem]


4.8.11 (2019-06-28)
-------------------

- Cache JSONField schema validator object
  [vangheem]

- JSONField works with dict instead of requiring str(which is then converted to dict anyways)
  [vangheem]

- A few more antipattern fixes [lferran]

4.8.10 (2019-06-26)
-------------------

- Fix indexing data potentially missing updated content when `fields` for accessor
  is not specified
  [vangheem]

- Fix events antipattern [lferran]

4.8.9 (2019-06-17)
------------------

- bump


4.8.8 (2019-06-17)
------------------

- Emit events for registry configuration changes
  [vangheem]


4.8.7 (2019-06-14)
------------------

- Add field mappings for test field [lferran]


4.8.6 (2019-06-10)
------------------

- Fix `@move` enable to allow being able to use it for renaming
  [vangheem]


4.8.5 (2019-06-07)
------------------

- Be compatible with aiohttp > 3 < 4
  [vangheem]

- Make sure utility you are providing also provides the interface you
  are creating it for in `load_utilities`. Before, it would not automatically
  apply the interface for you.
  [vangheem]


4.8.4 (2019-06-06)
------------------

- Fix aiohttp startup bug
  [vangheem]

- propagate unique violation errors on deletion as they should not happen
  anymore unless db hasn't been migrated
  [vangheem]


4.8.3 (2019-06-06)
------------------

- Upgrade to aiohttp 3.5.0
  [vangheem]


4.8.2 (2019-05-28)
------------------

- Fix bug where non-async object subscribers were getting called twice
  [vangheem]

4.8.2 (unreleased)
------------------

- Nothing changed yet.


4.8.1 (2019-05-25)
------------------

- Improve startup speed by not using glogger for startup code
  [vangheem]

- Support zope.Interface inheritance in schema.Object
  [masipcat]


4.8.0 (2019-05-13)
------------------

- `get_object_by_oid` now raises KeyError since it provided unsafe behavior
  when used with tombstoned objects
  [vangheem]


4.7.8 (2019-05-06)
------------------

- Fix potential memory leak in security lookup cache
  [vangheem]

- Fix security policy cache lookup to distinguish between types of cached
  decisions for parent vs top level object
  [vangheem]


4.7.7 (2019-05-01)
------------------

- Fix json schema definitions and provide `get_schema_validator` utility
  [vangheem]

- Fix `managed_transaction` context manager to correctly adopt parent transaction
  along with new transaction objects
  [vangheem]


4.7.6 (2019-04-28)
------------------

- Provide `connection_settings` on the request object with `tests.utils.get_container`
  [vangheem]


4.7.5 (2019-04-27)
------------------

- Fix command cleanup procedure to correctly cleanup asyncio tasks for commands
  [vangheem]


4.7.4 (2019-04-26)
------------------

- use execute utility for index future


4.7.3 (2019-04-26)
------------------

- Fix missing indexer
  [vangheem]


4.7.2 (2019-04-26)
------------------

- Provide `request_indexer` setting to be able to override how we handle
  indexing data
  [vangheem]

- Provide `connection_settings` on the request object with `tests.utils.get_container`
  [vangheem]


4.7.1 (2019-04-26)
------------------

- Update postgresql constraint to also not allow having parent id same as zoid
  [vangheem]

- Do not allow moving content into itself
  [vangheem]


4.7.0 (2019-04-16)
------------------

- Remove `IBeforeFieldModified` event and replace with `IBeforeObjectModifiedEvent`
>>>>>>> d2955243... bucket dict field implementation (#609)
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
