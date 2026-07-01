# Retrieval Benchmark Report

- Total queries: 12
- Hits in top-5: 11
- Coverage: 91.67%
- Target: 90%

| query | expected_doc | top_docs | hit |
|---|---|---|---|
| guillotina quickstart setup virtual environment | docs/source/quickstart.md | docs/source/quickstart.md<br>docs/source/developer/roles.md<br>docs/source/contrib/mcp.md<br>docs/source/installation/configuration.md<br>docs/source/index.md | yes |
| how url traversal resolves context in guillotina | docs/source/concepts/traversal.md | docs/source/contrib/mcp.md<br>docs/source/concepts/traversal.md<br>docs/source/installation/configuration.md<br>docs/source/how-to/index.md<br>docs/source/developer/roles.md | yes |
| object hierarchy database container content model | docs/source/concepts/object-model.md | docs/source/concepts/object-model.md<br>docs/source/rest/container.rst<br>docs/source/rest/item.rst<br>docs/source/concepts/security-model.md<br>docs/source/rest/folder.rst | yes |
| request response lifecycle metadata id field | docs/source/concepts/request-response.md | docs/source/concepts/request-response.md<br>docs/source/_llm/page-metadata-pattern.md<br>docs/source/api/request.rst<br>docs/source/api/response.rst<br>docs/source/rest/folder.rst | yes |
| transactions commit rollback consistency | docs/source/concepts/transactions.md | docs/source/concepts/transactions.md<br>docs/source/api/transactions.rst<br>docs/source/installation/configuration.md<br>docs/source/developer/persistence.md<br>docs/source/migration/5.0.rst | yes |
| storage backend postgres cockroach persistence | docs/source/concepts/storage.md | docs/source/concepts/storage.md<br>docs/source/developer/persistence.md<br>docs/source/installation/configuration.md<br>docs/source/concepts/transactions.md<br>docs/source/contrib/cache.md | yes |
| search indexing catalog query endpoint | docs/source/concepts/catalog.md | docs/source/rest/search.rst<br>docs/source/concepts/catalog.md<br>docs/source/contrib/mcp.md<br>docs/source/contrib/jsonbcatalog.md<br>docs/source/migration/5.0.rst | yes |
| middleware pipeline for requests and responses | docs/source/concepts/middleware.md | docs/source/concepts/middleware.md<br>docs/source/developer/security.md<br>docs/source/contrib/mcp.md<br>docs/source/installation/configuration.md<br>docs/source/about.rst | yes |
| context task variables async flow | docs/source/concepts/task-vars.md | docs/source/concepts/task-vars.md<br>docs/source/developer/async_utils.md<br>docs/source/training/extending/utilities.md<br>docs/source/contrib/mcp.md<br>docs/source/migration/5.0.rst | yes |
| role permission hierarchical security model | docs/source/concepts/security-model.md | docs/source/concepts/security-model.md<br>docs/source/developer/security.md<br>docs/source/concepts/object-model.md<br>docs/source/about.rst<br>docs/source/training/extending/permissions.md | yes |
| deployment logging configuration and proxy | docs/source/installation/index.rst | docs/source/installation/configuration.md<br>docs/source/training/configuration.md<br>docs/source/installation/logging.md<br>docs/source/training/extending/configuration.md<br>docs/source/installation/index.rst | yes |
| rest api endpoints application db container | docs/source/rest/index.rst | docs/source/rest/container.rst<br>docs/source/rest/item.rst<br>docs/source/rest/folder.rst<br>docs/source/rest/application.rst<br>docs/source/rest/db.rst | no |
