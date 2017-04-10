1.0.0a7 (unreleased)
--------------------

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
