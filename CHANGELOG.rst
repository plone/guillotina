1.1.0a14 (2017-06-14)
---------------------

- Proxy params values from cloud file manager to field manager
  [vangheem]


1.1.0a13 (2017-06-10)
---------------------

- Manually rollback transaction if pg thinks we're in one that isn't managed by us
  [vangheem]


1.1.0a12 (2017-06-10)
---------------------

- Make sure we do not have an existing transaction set when starting a new
  transaction
  [vangheem]


1.1.0a11 (2017-06-09)
---------------------

- Move fixtures in conftest.py to fixtures.py. This might break your tests
  that depend on guillotina folks!
  [vangheem]


1.1.0a10 (2017-06-08)
---------------------

- Handle deadlocks at conflict errors
  [vangheem]


1.1.0a9 (2017-06-08)
--------------------

- Fix issue where new annotations would not get registered as new objects on
  transaction and added objects on the transaction would get registered twice
  and cause conflicts
  [vangheem]

1.1.0a8 (2017-06-07)
--------------------

- Fix AttributeError on commit
  [vangheem]


1.1.0a7 (2017-05-29)
--------------------

- Make sure etcd docker containers do not conflict
  [vangheem]

1.1.0a6 (2017-05-29)
--------------------

- Do not name etcd docker image in tests
  [vangheem]


1.1.0a5 (2017-05-27)
--------------------

- Group objects should not get reindexing triggered on them
  [vangheem]


1.1.0a4 (2017-05-26)
--------------------

- Add more special characters for valid id
  [vangheem]


1.1.0a3 (2017-05-26)
--------------------

- Put restrictions on what valid ids for content are
  [vangheem]


1.1.0a2 (2017-05-26)
--------------------

- Significant performance fixes to lock implementation with etcd
  [vangheem]

- Provide more helper utilities for shell, so it's less error-prone
  [vangheem]

- Fix `tidonly` transaction strategy
  [vangheem]


1.1.0a1 (2017-05-24)
--------------------

- Provide payload on container creation
  [vangheem]

- Fix type check on creating container
  [vangheem]

- Provide async task for cockroach to cleanup children since there is no cascade support
  [vangheem]

- Fix cockroachdb transaction support as it behaves differently than postgresql
  [vangheem]

- Include cockroachdb in our CI testing
  [vangheem]

- Simplify docker testing infrastructure
  [vangheem]

- Fix cockroachdb integration
  [vangheem]


1.0.0a28 (2017-05-18)
---------------------

- managed_transaction context manager can now adopt modified objects from
  outer transaction
  [vangheem]


1.0.0a27 (2017-05-17)
---------------------

- add new `guillotina.transactions.managed_transaction` context manager
  [vangheem]


1.0.0a26 (2017-05-17)
---------------------

- Only initialize database if needed instead of running initialize statements
  on every app startup
  [vangheem]

- rename get_class_dotted_name to get_dotted_name
  [vangheem]

1.0.0a25 (2017-05-15)
---------------------

- Handle connection is closed error when starting transaction
  [vangheem]


1.0.0a24 (2017-05-13)
---------------------

- Fix transaction conflict retry handle
  [vangheem]

- fix scenario where prepared statements would get cached with wrong db connection
  [vangheem]

- Enforce transaction ids match when updating objects and throw a ConflictError
  when there is a mismatch. This can happen in cases where there is stale cache
  being pulled.
  [vangheem]

- Remove use of `merge` transaction strategy. Better to just abort and retry
  instead of costly merge resolution issues
  [vangheem]


1.0.0a23 (2017-05-11)
---------------------

- Fix get_container test utility
  [vangheem]


1.0.0a22 (2017-05-11)
---------------------

- Fix QueueUtility to properly get transaction object before working on view
  [vangheem]

- Update storage caching interfaces to make them easier to use
  [vangheem]


1.0.0a21 (2017-05-09)
---------------------

- Reuse transaction object if same request object is provided. This helps when
  working with the same persistent objects across one request object.
  [vangheem]


1.0.0a20 (2017-05-09)
---------------------

- Tie every request to one transaction instead of trying to juggle pool of
  transactions in transaction manager.
  [vangheem]

- Only issue transaction id for write operations
  [vangheem]

- Use sequence for transaction id for postgresql and serial for cockroachdb
  [vangheem]


1.0.0a19 (2017-05-08)
---------------------

- Fix conflict error retries and make tests for it
  [vangheem]


1.0.0a18 (2017-05-08)
---------------------

- Make sure to be able to handle int, float responses as well
  [vangheem]


1.0.0a17 (2017-05-05)
---------------------

- Implement locks on pg connections for everything except cursors
  [vangheem]


1.0.0a16 (2017-05-04)
---------------------

- Be careful with locks on transaction to prevent deadlocks
  [vangheem]


1.0.0a15 (2017-05-04)
---------------------

- Make sure to lock access to queries on the pg database per connection. This
  fixes asyncpg errors when you attempted to do actions async actions on
  one transaction. Where it was easiest to have problem was asyncio.gather
  [vangheem]

- add creators/contributors as context properties for the IDublinCore behavior
  instead of trying to get the data from the annotation
  [vangheem]

- utils.get_content_path should be based from root of container, not root of database
  [vangheem]

- Fix another memory leak in get_current_request and add test for it
  [vangheem]

- Provide more robust conflict resolution on fields of content and annotations
  [vangheem]


1.0.0a14 (2017-04-25)
---------------------

- Fix issue where annotations would get duplicated
  [vangheem]

- rename __annotations_data_key to __annotations_data_key__ in Annotation behavior
  [vangheem]

- Prevent aiohttp sessions from not closing by using context managers everywhere
  [vangheem]


1.0.0a13 (2017-04-24)
---------------------

- root ThreadPoolExecutor was removed in previous release. Some packages use this
  feature
  [vangheem]

- Rename PServerJSONEncoder to GuillotinaJSONEncoder
  [vangheem]


1.0.0a12 (2017-04-24)
---------------------

- Provide conflict resolution across transactions
  [vangheem]

- Be able to query storage for total number of objects
  [vangheem]

- Provide basic async blob support interface
  [vangheem]

- Fix annotation behaviors that use __local__properties__ not storing data
  properly on content object
  [vangheem]

- Do not re-load behavior data if it's already been loaded from db
  [vangheem]

- Provide new IObjectLoadedEvent to do things with object when it's loaded
  from the database
  [vangheem]


1.0.0a11 (2017-04-15)
---------------------

- Fix memory leak in get_current_request C implementation
  [vangheem]

- use asyncio.shield in commit and abort handlers to make sure they finish
  even if task is cancelled
  [vangheem]

- Fix case where abort would cause asyncio CancelledError to occur
  [vangheem]


1.0.0a10 (2017-04-13)
---------------------

- Provide ability to configure logging with json config
  [vangheem]


1.0.0a9 (2017-04-12)
--------------------

- Be able to provide `aiohttp_settings` in config.json to configure parts of
  aiohttp application
  [vangheem]

- async_keys on database type did not await
  [vangheem]


1.0.0a8 (2017-04-11)
--------------------

- Fix annotation data not getting indexed properly. Getting index data needs
  to be async.
  [vangheem]


1.0.0a7 (2017-04-10)
--------------------

- be able to configure __allow_access__ with service function by using
  the `allow_access` configuration option

- rename modified to modification_date and created to creation_date
  [vangheem]


1.0.0a6 (2017-04-06)
--------------------

- Fix container objects not having current transaction when new objects are
  registered for them
  [vangheem]


1.0.0a5 (2017-04-04)
--------------------

- Be able to override base configuration in addon applications
  [vangheem]

- Fix use of default layer in app_settings
  [vangheem]


1.0.0a4 (2017-04-03)
--------------------

- json schema support in service definitions
  [vangheem]

- rename `subjects` to `tags` for IDublinCore behavior
  [vangheem]

- rename permissions:
  `guillotina.AddPortal` -> `guillotina.AddContainer`
  `guillotina.DeletePortals` -> `guillotina.DeleteContainers`
  `guillotina.GetPortals` -> `guillotina.GetContainers`
  [vangheem]

- You can now reference modules in your static file configuration: `mymodule:static`
  [vangheem]

- Static directories will now serve default index.html files
  [vangheem]

- Fix static directory support
  [vangheem]

- Add auto reload support with the aiohttp_autoreload library
  [vangheem]

- Upgrade to aiohttp 2
  [vangheem]

- Remove the dependencies six and requests
  [vangheem]

- Rename `portal_type` to `type_name` as "portal" does not make sense anymore
  [vangheem]


1.0.0a3 (2017-03-23)
--------------------

- Fix automatically creating id when none provided for content creation
  [vangheem]

1.0.0a2 (2017-03-23)
--------------------

- Change guillotina commands to be sub-commands of main `bin/guillotina`
  command runner so developer do not need to register separate scripts
  for each command. Fixes #27
  [vangheem]

- Change Site portal type to Container
  [vangheem]

- Fix get_current_request to correctly look for python None object when finding
  the request object
  [vangheem]

- Fix `gshell` command to work with aysncio loop so you can run `await` statements
  with the shell. Compatibility done with aioconsole.
  [vangheem]

- Provide support for utilizing `middlewares` option for aiohttp server
  [vangheem]


1.0.0a1 (2017-03-17)
--------------------

- move zope.schema, zope.component, zope.configuration into guillotina
  [vangheem]

- move get_current_request to guillotina.utils
  [vangheem]

- create_content and create_content_in_container are not async functions
  [vangheem]

- remove zope.security, zope.location, zope.dublincore, plone.behavior,
  zope.dottedname, zope.lifecycleevent
  [vangheem]

- rename to guillotina
  [vangheem]

- Remove plone:api zcml directive
  [vangheem]


1.0a14 (unreleased)
-------------------

- Rename "address" option to "port" and add "host" option to bind something different
  than the default 0.0.0.0
  [vangheem]


1.0a13 (2017-02-27)
-------------------

Fixes:

- Fix static file configuration
  [vangheem]


1.0a12 (2017-02-27)
-------------------

Fixes:

- HTML renderer can now handle html responses correctly
  [vangheem]

- Renamed settingsForObject to settings_for_object
  [vangheem]


1.0a11 (2017-02-22)
-------------------

Fixes:

- Handle NotADirectoryError error when attempting to load b/w compat zcml
  [vangheem]

Breaking changes:

- ACL is now in the object itself so the permission will not be maintained
  [ramonnb]

New features:

- Executing pending tasks after requests has returned
  [ramonnb]

- Adding the payload on the events that modifies the objects
  [ramonnb]

- Defining local and global roles so they can be used to define @sharing
  On indexing security information we only get the AccessContent permission.
  [ramonnb]

- Install addons can have the context
  [ramonnb]

- Merging zope.securitypolicy
  [ramonnb]

- Adding C optimization for get_current_request
  [ramonnb]


1.0a10 (2017-02-01)
-------------------

Fixes:

- Fix issue where correct aiohttp response would not be generated always
  [vangheem]

New features:

- be able provide your own database factories by providing named utilities for
  the IDatabaseConfigurationFactory interface
  [vangheem]

- install, uninstall methods for addon class can now be async
  [vangheem]

- Support for newt.db
  [ramonnb]

- Be able to define adapters, subscribers, permissions, roles, grant
  with decorators, not zcml
  [vangheem]

- No more zcml in core
  [vangheem]


1.0a9 (2017-01-18)
------------------

Fixes:

- Use guillotina.schema getter and setter to set attributes
  [ramonnb]

New features:

- Be able to define addons using decorators, not zcml
  [vangheem]

- Be able to define behaviors using decorators, not zcml
  [vangheem]

- Be able to define content types using decorators, not zcml
  [vangheem]

- Catalog reindex as async operation
  [ramonnb]

- RelStorage Support (postgres)
  [ramonnb]

- Adding HTTP Precondition exception
  [ramonnb]

- New way to create services with decorators instead of zcml/json configuration
  [vangheem]

- Add functionality like virtualhost monster to define the urls
  [ramonnb]

- Add new pcreate command
  [vangheem]

- Add new pmigrate command and migration framework
  [vangheem]

- Provide base guillotina.commands.Command class to provide your own commands.
  Commands have been moved in code so you'll need to re-run buildout to get
  pserver to work after this update.
  [vangheem]

- Automatically give authenticated users new `guillotina.Authenticated` role
  [vangheem]

- Handle error when deserializing content when not authenticated and checking
  permissions
  [vangheem]

- add `pshell` command
  [vangheem]

- Role member for Manager group
  [ramonnb]


Breaking changes:

- plone:api zcml directive deprecated in favor of decorator variant
  [vangheem]


1.0a8 (2016-12-18)
------------------

- On deserialization errors, provide error info on what fields could not be
  deserialized in the api response.
  [vangheem]

- Be able to provide data from serializable exception data to be used with
  ErrorResponse objects with Exceptions that implement ISerializableException.
  [vangheem]

- Add Events to enable audit of activity
  [ramonnb]

- Add the JSON Field
  [ramonnb]

- Fix various function naming standard issues to not use camel case.
  [vangheem]

- Fix imports with isort.
  [gforcada]

- remove local component registry
  [vangheem]

- GET @search(plone.SearchContent) passed to search method and
  POST @search(plone.RawSearchContent) passed to query method
  on ICatalogUtility. GET is now meant to be query the search utility will
  do something clever with and POST is meant to be a raw query passed to utility
  [vangheem]

- provide new `plone.SearchContent`, `plone.RawSearchContent` and
  `plone.ManageCatalog` permissions
  [vangheem]

- provide IConstrainTypes adapter interface to override allowed types in a folder
  [vangheem]

- provide dynamic behavior for objects
  [ramonnb]

- provide basic command line utility to interact with APIs
  [vangheem]

- fix fallback cors check
  [vangheem]

- Added zope.event async version on guillotina.events (notify and async handlers)
  [ramonnb]

- Improve code analysis, add configurations for it and remove all tabs.
  [gforcada]

1.0a7 (2016-11-24)
------------------

- add jwt token validator
  [vangheem]

- Add to finalize an AsyncUtil when its finishing the software
  [ramonnb]

- Remove `AUTH_USER_PLUGINS` and `AUTH_EXTRACTION_PLUGINS`. Authentication now
  consists of auth extractors, user identifiers and token validators.
  [vangheem]

- Correctly check parent object for allowed addable types
  [vangheem]

- Get default values from schema when attribute on object is not set
  [ramonnb]


1.0a6 (2016-11-21)
------------------

- Move authorization to after traversal
  [vangheem]

- Fix issue where you could not save data with the API
  [vangheem]


1.0a5 (2016-11-21)
------------------

- Adding zope.event compatible async handlers for ElasticSearch and other events handlers [@bloodbare]
- Adding PostCommit and PreCommit Hooks that can be async operations [@bloodbare]


1.0a4 (2016-11-19)
------------------
