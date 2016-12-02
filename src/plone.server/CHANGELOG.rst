1.0a8 (unreleased)
------------------

- provide IConstrainTypes adapter interface to override allowed types in a folder
  [vangheem]

- provide dynamic behavior for objects
  [ramonnb]

- provide basic command line utility to interact with APIs
  [vangheem]

- fix fallback cors check
  [vangheem]

- Added zope.event async version on plone.server.events (notify and async handlers)
  [ramonnb]


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
