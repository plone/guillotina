CHANGELOG
=========

6.0.0a5 (unreleased)
--------------------

- Added `IIDChecker` adapter
  [vangheem]

- Schema fields default value for `required` is now `False`
  [vangheem]

- Denormalized group info when user is added to a group throught users endpoint (issue #806)
  [jordic]

- Add `Range` header support
  [vangheem]

- Be able to disable supporting range headers in `IFileManager.download`
  [vangheem]

- Fix validating None values in required fields
  [vangheem]

- Add localroles to @available-roles
  [jordic]

- Add `no-install-recommends` to Dockerfile (apt options)
  [svx]

6.0.0a4 (2019-12-23)
--------------------

- Improving ValidationErrors messages
  [masipcat]

- Fix error with requeued async queue tasks

- Added `valid_id_characters` app setting
  [vangheem]

- Better CancelledError handling in resolving a request
  [vangheem]

- Fix duplicate behaviors interfaces in get_all_behavior_interfaces()
  [qiwn]

- Fix adding duplicate behaviors
  [qiwn]


6.0.0a3 (2019-12-18)
--------------------

- Added back support for Guillotina/aiohttp middlewares
  [masipcat]

- Improved server command and added 'server_settings'
  [masipcat]

- Added property 'status' to Response
  [masipcat]


6.0.0a2 (2019-12-17)
--------------------

- Adapt to HTTP1.1 protocol on uvicorn by default
  [bloodbare]

- PatchField: added operation "multi"
  [masipcat]

- @duplicate: added option to reset acl

- Make pytest.mark.app_settings work in older pytest versions too [lferran]

- @move: destination id conflict should return 409 error, not 412
  [inaki]

- Explicit loop to execute on tests
  [bloodbare]

- Fix IAbsoluteUrl() returns request query
  [masipcat]

- Added attribute cookies to class Request()
  [masipcat]

- Added uvicorn as a guillotina requirement
  [masipcat]

- Added endpoint @available-roles on container
  [jordic]

- Add configurable expiration for jwt.tokens
  [jordic]


6.0.0a1 (2019-12-09)
--------------------

- Move tags to a context property to make it indexable on json
  [bloodbare]

- Added async property `Request.body_exists`
  [masipcat]

- Fixed fixture 'guillotina'
  [masipcat]

- Make sure that guillotina uses uvloop on starting if its installed
  [bloodbare]

- Make sure uvicorn uses the same loop as guillotina startup
  [bloodbare]

- Fix tests in 'test_cache_txn.py' and 'test_setup.py' being skipped
  [masipcat]

- Replaced aiohttp with ASGI (running with uvicorn by default)
  [dmanchon,masipcat,vangheem]
