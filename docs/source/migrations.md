# MIGRATIONS

plone.server provides an interface to run migrations for itself and the applications
it currently has activated.

Migrations are run against applications. If applications define addons for sites,
those application migration steps need to check for the installation of their
addon in the migration step.


## RUNNING MIGRATIONS

plone.server provides a command line utility to manage and run migrations
against your entire install or against a particular site.


Here is a minimalistic example using the command:

```
./bin/pmigrate
```

By default, the `pmigrate` command will migrate all sites on all available
databases.


## PMIGRATE COMMAND OPTIONS

* dry-run: do test running the migration but not commit to the database
* site: path to site to run the command against
* report: report current versions site(s) are migrated to and see available migrations
* app: run command for a particular application
* to-version: run migrations to a provided version


Complicated command usages example:

```
./bin/pmigrate --site=/zodb/plone --app=pserver.elasticsearch --to-version=1.0.1 --dry-run
```


## DEFINING MIGRATIONS

To define migrations in your own applications, `plone.server` provides a simple
decorator::

```python
from plone.server.migrations import migration
@migration('my.app', to_version='1.0.1')
def migrate_stub(site):
    # my migration code...
    pass
```
