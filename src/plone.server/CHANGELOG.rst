1.0a7 (unreleased)
------------------

- Add to finalize an AsyncUtil when its finishing the software
  [ramon]

- Remove `AUTH_USER_PLUGINS` and `AUTH_EXTRACTION_PLUGINS`. Authentication now
  consists of auth policies, user identifiers and token checkers.
  [vangheem]

- Correctly check parent object for allowed addable types
  [vangheem]

- Get default values from schema when attribute on object is not set
  [bloodbare]


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
