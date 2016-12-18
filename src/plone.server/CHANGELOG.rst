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

- Added zope.event async version on plone.server.events (notify and async handlers)
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
