CHANGELOG
=========

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
  [vangheem]


4.6.3 (2019-04-16)
------------------

- Proper ContentAPI login to define user
  [bloodbare]

- Util function to get a database object
  [bloodbare]

- PyYaml 5.1 upgrade version
  [bloodbare]

- Add async feature on patch operation set
  [bloodbare]

4.6.2 (2019-04-12)
------------------

- enable the option to define specific transaction manager for each database
  [bloodbare]


4.6.1 (2019-04-12)
------------------

- check for trashed parent id with `get_object_by_oid` to make sure object
  has not been tombstoned for deletion.
  [vangheem]

- Do not allow bad logging config cause guillotina to fail to start
  [vangheem]


4.6.0 (2019-04-09)
------------------

Fixes:

- Fix potential configuration conflict errors when sub-packages are used
  as unique applications
  [vangheem]

New:

- Remove dependency on aioconsole and move to `ipython` for shell support
  [vangheem]

- Added Heroku deploy button
  [karannaoh]

- Start to improve the docker setup
  [svx]


4.5.13 (2019-04-04)
-------------------

- Provide `api.container.create_container` function
  [vangheem]

- Fix docker build
  [vangheem]


4.5.12 (2019-04-03)
-------------------

- Be able to create container with array of `@addons`.
  [vangheem]

- Fix Command.__run() not waiting for all aio tasks to finish
  [masipcat]


4.5.11 (2019-04-01)
-------------------

- Provide utilities for move and duplicate
  [vangheem]


4.5.10 (2019-03-28)
-------------------

Fixes:

- Fix to work with cockroach db >= 2.1
  [vangheem]

- Fix use of default factory for default value on content
  [vangheem]


New:

- Provide warning when using insecure jwt secret in production
  [vangheem]

- Provide new `gen-key` for generating secure jwk keys
  and jwt secrets
  [vangheem]

- Give warning when generating jwk key
  [vangheem]

- Fix jwt implementation to use customized algorithm for encoding
  [vangheem]

- Fix jwe implementation
  [bloodbare]

- Fix error message when trying to delete a concrete behavior
  [marcus29200]

Changes:

- Remove `utils.clear_conn_statement_cache`
  [vangheem]

- Lazy load dynamically generated jwk key
  [vangheem]


4.5.9 (2019-03-18)
------------------

- Implement "del" operation for dynamic field values
  [vangheem]


4.5.8 (2019-03-15)
------------------

- Add `container_id` to jsonb data
  [vangheem]

- Fix memory leak in security policy lookups
  [vangheem]

- Introduce migrate command
  [vangheem]

- Add vacuum command
  [vangheem]

- Fix HEAD tus
  [bloodbare]

- Define option to not purge DB on deletes
  [bloodbare]

- Run `request.execute_futures` with managed_transaction context manager
  [vangheem]

- Add code owners
  [bloodbare]


4.5.7 (2019-03-08)
------------------

- Introduce `UnionField` schema type to allow fields to be one of multiple
  types of fields.
  [vangheem]

- Fix dynamic field keyword values to work with single or array values. This helps
  integration with elasticsearch.
  [vangheem]

- Fix `GuillotinaDBRequester.make_request()` not decoding json responses
  [masipcat]

- Missing 'db_schema' in 'tid_sequence' table
  [masipcat]

- Add 'db_schema' to postgresql storage config
  [masipcat]


4.5.6 (2019-02-18)
------------------

- Fix CORS on tus
  [bloodbare]

- Support tus upload for multifile field
  [bloodbare]

- Ws token on application
  [bloodbare]


4.5.5 (2019-02-15)
------------------

- Fix losing startup command setting hints after application configuration
  [vangheem]

- Be able to provide additional metadata for dynamic fields
  [vangheem]

- Bugfix: Raise HTTPUnauthorized if trying to modify a write_protected
  field [lferran]

- Adding = to valid chars.
  [bloodbare]

- Allowing to get user information of application
  [bloodbare]

- Fixing SQL creation function
  [bloodbare]


4.5.4 (2019-02-07)
------------------

- Fix serialization of json field to work with swagger
  [vangheem]


4.5.3 (2019-01-31)
------------------

- Add `get` method to `BucketListValue` class
  [vangheem]


4.5.2 (2019-01-31)
------------------

- Reusage of jwt decode
  [bloodbare]


4.5.1 (2019-01-30)
------------------

- Fix read connection lock regression
  [vangheem]


4.5.0 (2019-01-30)
------------------

- By default, do not serialize json data to postgresql anymore. If you were
  depending on `store_json` default to be `true`, you need to update
  [vangheem]

- Provide `guillotina.db.interfaces.IJSONDBSerializer` to be able to
  override json stored in posgresql to be different than what is serialized
  in catalog/elasticsearch/etc
  [vangheem]

- Improved PostgresqlStorage._check_bad_connection()
  [masipcat]

-fix typos in documentation



4.4.10 (2019-01-23)
-------------------

- postgresql storage needs to share connection lock
  [vangheem]


4.4.9 (2019-01-15)
------------------

- Handle if no data to iterate on for downloads
  [vangheem]


4.4.8 (2019-01-15)
------------------

- Fix release
  [vangheem]


4.4.7 (2019-01-15)
------------------

- Defer preparing download response so http exceptions are
  handle correctly
  [vangheem]


4.4.6 (2019-01-15)
------------------

- Fix getting binding file field for cloud files
  [vangheem]

- provide `guillotina.utils.get_url` function that pays attention
  to `X-VirtualHost-Monster` header
  [vangheem]

- Take `X-Forwarded-Proto` into account for request url
  [vangheem]

- Implement multi attachments
  [masipcat]


4.4.5 (2019-01-11)
------------------

- Allow to login on IApplication.
  [bloodbare]


4.4.4 (2019-01-11)
------------------

- Be able to prevent closing database connection pools
  [vangheem]


4.4.3 (2019-01-11)
------------------

- Implement `db.storage.spg.PGConnectionManager` class to allow
  safely sharing pool and read connections between multiple
  storages.
  [vangheem]


4.4.2 (2019-01-10)
------------------

- Option to add different type of containers.
  [bloodbare]


4.4.1 (2019-01-09)
------------------

- Postgresql storage accepts pool arguments
  [vangheem]


4.4.0 (2018-12-27)
------------------

New:

- Implement HEAD for `@download` endpoint
  [vangheem]

- Be able to customize the table names used with `objects_table_name` and
  `blobs_table_name` database configuration options.
  [vangheem]

- Adding the option to define the reader for annotations
  [bloodbare]

Fixes:

- Fix Resource.__getattr__() for empty fields with default values
  [masipcat]


4.3.5 (2018-12-09)
------------------

- Added before render view event [lferran]

4.3.4 (2018-12-06)
------------------

- Check valid generated id
  [vangheem]

- Implement delete by value for `PatchField(value_type=schema.List())`
  [vangheem]


4.3.3 (2018-12-03)
------------------

- Be able to override configuration with environment variables
  [vangheem]


4.3.2 (2018-11-20)
------------------

- Fix MockTransaction test object to have `manager` property
  [vangheem]

4.3.1 (2018-11-15)
------------------

- Missing utilities settings should not cause error
  [vangheem]


4.3.0 (2018-11-13)
------------------

- Remove Container from available-types
  [bloodbare]

- No automatic async util loaded.
  [bloodbare]

  **BREAKING CHANGE**: Async Utilities are not loaded by default so they
  need to be defined on the package configuration on the merging settings at
  `__init__.py`.
  Utilities are not key mapped, each utility has an id to reflect it.
  Now config.yaml files only need to define them if you want to overwrite.

- Improve Documentation

  - Index page
  - Security page

  [hirokiky]


4.2.13 (2018-11-09)
-------------------

- Update admin interface:

  - Support for guillotina.cms
  - Edit form
  - Add medium-like richtext editor

  [ebrehault]


4.2.12 (2018-11-07)
-------------------

- Be able to specify `?include=*` to include all behaviors in response
  [vangheem]

- Be able to specify `data_key` and `auto_serialize` for behavior configuration
  [vangheem]

- Fixing #374 were required fields were not checked
  [bloodbare]

- Fix shell command with Python 3.7
  [vangheem]

- No longer use `utils.clear_conn_statement_cache` as asyncpg does not properly
  clean up prepared statements when using the clear method.
  See https://github.com/MagicStack/asyncpg/blob/v0.13.0/asyncpg/connection.py#L1499
  The `_maybe_gc_stmt` is never called on the statement so they never get
  cleaned from the database. Due to this implementation, with databases under
  large enough load, it can cause postgresql to run out of memory.
  `utils.clear_conn_statement_cache` is now considered a dangerous API method,
  is marked deprecated, implementation is now emptied and will be removed
  in the next major version of Guillotina.

  As an alternative, use the connection option of `statement_cache_size: 0` or
  a very low value for `max_cached_statement_lifetime`.

  This case is only noteworthy when running against very large postgresql databases.
  In certain cases, PG does a terrible job query planning and pegs CPU.
  [vangheem]


4.2.11 (2018-10-30)
-------------------

- Do not error on indexing with invalid payload
  [vangheem]

- Be able to override factory for content types
  [vangheem]

- Workaround to fix aiohttp bug: https://github.com/aio-libs/aiohttp/issues/3335
  [vangheem]


4.2.10 (2018-10-07)
-------------------

- Choice should be serialized as string
  [bloodbare]

- Add `IPasswordChecker` and `IPasswordHasher` utilities
  [vangheem]

- make `guillotina.auth.validators.hash_password` more generic
  [vangheem]

- add `guillotina.auth.validators.check_password`
  [vangheem]

- make sure to load dependency application commands
  [vangheem]


4.2.9 (2018-10-04)
------------------

- Also accept filename in `@download` url like `@download/file/foobar.jpg`
  [vangheem]

- Fix `Access-Control-Allow-Credentials` header value to be `true` instead of `True`
  [vangheem]


4.2.8 (2018-10-03)
------------------

- Be able to specify dependency addons with `dependencies` configuration param
  [vangheem]


4.2.7 (2018-10-01)
------------------

- Be able to set `uid` on object creation
  [vangheem]

- Provide simple content api
  [vangheem]

- Fix inheritance going in reverse and affecting parent tasks
  [vangheem]

- Jupyter notebook compatibility
  [vangheem]


4.2.6 (2018-09-28)
------------------

- Adding support for default value on ContextProperties
  [bloodbare]


4.2.5 (2018-09-27)
------------------

- Automatically load dependent applications if defined in base application
  app_settings object.
  [vangheem]


4.2.4 (2018-09-27)
------------------

- Correctly handle issues when releasing connections back to the pool
  [vangheem]


4.2.3 (2018-09-26)
------------------

- Added cookie support on auth.
  [bloodbare]


4.2.2 (2018-09-26)
------------------

- Allow value serializers to be coroutines
  [vangheem]


4.2.1 (2018-09-25)
------------------

- Adding logging and renew token endpoint
  [bloodbare]


4.2.0 (2018-09-23)
------------------

- Add new events:
    - IApplicationCleanupEvent
    - IApplicationConfiguredEvent
    - IApplicationInitializedEvent
    - IDatabaseInitializedEvent
    - ITraversalMissEvent
    - ITraversalResourceMissEvent
    - ITraversalRouteMissEvent
    - ITraversalViewMissEvent

- upgrade shipped asyncpg version
  [vangheem]

- Add events for application configuration, request traversal misses
  and database itialization.
  [vangheem]

- Add `@resolveuid` endpoint
  [vangheem]

- Change `@ids` endpoint permission to `guillotina.Manage`
  [vangheem]

- Change `@items` endpoint permission to `guillotina.Manage`
  [vangheem]

- Add `guillotina.Manage` permission which only `guillotina.Managers` roles
  have by default.
  [vangheem]


4.1.12 (2018-09-20)
-------------------

- Fix file handling to properly provide 404 responses when no value is set
  [vangheem]

- Move static guillotina assets into python package so they can be
  referenced from python dotted paths with `guillotina:static/assets`
  [vangheem]

- Be able to configure behavior directly against a schema instead
  of needing to define concret behavior
  [vangheem]

4.1.11 (2018-09-19)
-------------------

- Fixing serialization bug
  [bloodbare]


4.1.10 (2018-09-19)
-------------------

- Fixing Bug on Serialize Schema
  [bloodbare]

- Adding static behaviors on REST serialize
  [bloodbare]

- Fix cookiecutter application template
  [vangheem]


4.1.9 (2018-09-17)
------------------

- Adding annotation support on registry object
  [bloodbare]

- Fix IJSONToValue adapter for IPatchField
  [masipcat]


4.1.8 (2018-09-14)
------------------

- Be able to override configuration values with `--override` parameter
  [vangheem]


4.1.7 (2018-09-12)
------------------

- Provide more flexibility for traversal sub-routes
  [vangheem]

- Make sure ApplicationRoot knows about the loop it is used with
  [vangheem]

4.1.6 (2018-08-31)
------------------

- On PUT, completely delete existing existing behavior objects
  [vangheem]


4.1.5 (2018-08-30)
------------------

- Allow PUT in CORS policy
  [ebrehault]

- Update admin interface:

  - Use PUT to edit
  - Preserve path when logging in

  [ebrehault]

4.1.4 (2018-08-29)
------------------

- Implement default PUT method to be able to replace content
  [vangheem]

- Fix error on invalid CORS ch
  [vangheem]

- Option to disable inheritance on role permission relation
  [bloodbare]

- Add get_behavior utility
  [vangheem]

- IBeforeFieldModified event to hook before setting a field
  [bloodbare]

- Added PatchField for ints to be used as counters [lferran]

4.1.3 (2018-08-08)
------------------

- Split sharing function to be reusable
  [bloodbare]


4.1.2 (2018-08-06)
------------------

- Binding fields to objecst on deserialize to make sure vocabulary is enabled
  [bloodbare]

- Enabling uploading files with a JSON payload
  [bloodbare]


4.1.1 (2018-07-30)
------------------

- Adding decorator for vocabulary definition
  [bloodbare]

- Adding tests on cookiecutter
  [bloodbare]

- Add 'Navigator' utility, that provides a path-based index to the already
  loaded objects.
  [cdevienne]


4.1.0 (2018-07-23)
------------------

- Various doc improvements including security section rewrite
  [WnP]

- Allow DELETE with params on url.
  [jordic]

- Add admin interface as static JS app on http://localhost:8080/+admin/
  [mathilde-pellerin, ebrehault]

4.0.7 (2018-07-21)
------------------

- Improve and fix docs
  [vangheem]

- Fix interface for layers
  [bloodbare]

- Updating requirements for py3.7
  [bloodbare]


4.0.6 (2018-07-20)
------------------

- Provide IIDGenerator interface to customize generating new ids
  [bloodbare]

- Fix applying cors when errors on traversal
  [bloodbare]


4.0.5 (2018-07-19)
------------------

- Fix run_app args when access_log_format is None
  [vangheem]


4.0.4 (2018-07-19)
------------------

- Use guillotina response exceptions everywhere so we
  use built-in CORS

- Serialize if a content is folderish
  [bloodbare]

- Serialize the schema with the full behavior name
  [bloodbare]

- Upgrade to aiohttp > 3 < 4.
  Notable aiohttp changes:
    - Response.write is now a coroutine
    - Response.write should explicitly use write_eof
    - Websockets send_str is now a coroutine
  [vangheem]

- Dublin core should not be required
  [bloodbare]

4.0.3 (2018-07-16)
------------------

- Allow patching registry with new shcema fields


4.0.2 (2018-06-22)
------------------

- Support for extra values on Field properties
  [bloodbare]

- Don't fail on read-only pg

- Fix nested schema null value deserialization error
  [vangheem]

- Fix use of AllowSingle with children overriding the same permission
  [bloodbare]


4.0.1 (2018-06-07)
------------------

- Implement minimal passing mypy compatibility
  [vangheem]

- Rename `BaseObject.__annotations__` to `BaseObject.__gannotations__` to prevent
  namespace clashes with mypy and other things
  [vangheem]


4.0.0 (2018-06-05)
------------------

- `guillotina.browser.Response` moved to `guillotina.response.Response`
- move `guillotina.browser.ErrorResponse` to `guillotina.response.ErrorResponse`
- `guillotina.browser.UnauthorizedResponse` removed
- `guillotina.response.Response` no longer supports wrapping aiohttp responses
- `guillotina.response.Response` can now be raised as an exception
- returned or raised aiohttp responses now bypass guillotina renderer framework
- raising any Response as an exception aborts current transaction
- remove `IFrameFormatsJson`
- remove `IRenderFormats`, `IRendered` is now a named adapter lookup
- remove `app_settings.renderers` setting. Use the lookups
- remove `IDownloadView`
- remove `TraversableDownloadService`
- remove `IForbiddenAttribute`
- remove `ISerializableException`
- remove `IForbidden`
- by default, provide an async queue utility
- move `guillotina.files.CloudFileField` to `guillotina.fields.CloudFileField`
- fix deserialization with BucketListField
- fix required field of PatchField
