# Commands

You can provide your own CLI commands for guillotina through a simple interface.


## Available commands

* serve: run the http rest api server(this is default command if none given)
* shell: drop into a shell with root object to manually work with
* create: use cookiecutter to generate guillotina applications
* initialize-db: databases are automatically initialized; however, you can use this command to manually do it
* testdata: populate the database with test data from wikipedia
* run: run a script


## Command Options

- *
  - `--config`: path to configuration file. `defaults to config.(yaml|json)`
- serve:
  - `--host`: host to bind to
  - `--port`: port to bind to
  - `--reload`: auto reload on code changes. `requires aiohttp_autoreload`
  - `--profile`: profile Guillotina while it's running
  - `--profile-output`: where to save profiling output
  - `--monitor`: run with aiomonitor. `requires aiomonitor`
- shell
- create
  - `--template`: name of template to use
  - `--overwrite`: overwrite existing file
  - `--output`: where to save the file
- initialize-db
- testdata
  - `--per-node`: How many items to import per node
  - `--depth`: How deep to make the nodes
- run
  - `--script`: path to script to run with `run` async function


## Running commands

Guillotina provides two binaries to run commands through, `bin/guillotina` and
a shortcut, `bin/g`.

To run a command, it's just a positional argument on the running command::

```
bin/g shell
```


## Creating commands

guillotina provides a simple API to write your own CLI commands.


Here is a minimalistic example:

```python

from guillotina.commands import Command
class MyCommand(Command):

    def get_parser(self):
        parser = super(MyCommand, self).get_parser()
        # add command arguments here...
        return parser

    def run(self, arguments, settings, app):
        pass

```

Then, just add your command to your application's app_settings in the `__init__.py`:

```python

app_settings = {
    "commands": {
        "mycommand": "my.package.commands.MyCommand"
    }
}
```
