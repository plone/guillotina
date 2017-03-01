# Migrations

guillotina provides an interface to run migrations for itself and the applications
it currently has activated.

Migrations are run against applications. If applications define addons for sites,
those application migration steps need to check for the installation of their
addon in the migration step.


## Running migrations

guillotina provides a command line utility to manage and run migrations
against your entire install or against a particular site.


Here is a minimalistic example using the command:

```
./bin/pmigrate
```

By default, the `pmigrate` command will migrate all sites on all available
databases.


## pmigrate command options

* dry-run: do test running the migration but not commit to the database
* site: path to site to run the command against
* report: report current versions site(s) are migrated to and see available migrations
* app: run command for a particular application
* to-version: run migrations to a provided version


Advanced command usages example:

```
./bin/pmigrate --site=/zodb/guillotina --app=guillotina_elasticsearch --to-version=1.0.1 --dry-run
```


## Defining migrations

To define migrations in your own applications, `guillotina` provides a simple
decorator::

```python
from guillotina.migrations import migration
@migration('my.app', to_version='1.0.1')
def migrate_stub(site):
    # my migration code...
    pass
```
