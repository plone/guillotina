# Commands

You can provide your own CLI commands for guillotina through a simple interface.


## Available commands

* `serve`: run the HTTP REST API server (this is the default command if none given)
* `shell`: drop into a shell with root object to manually work with
* `create`: use cookiecutter to generate guillotina applications
* `initialize-db`: databases are automatically initialized; however, you can use this command to manually do it
* `testdata`: populate the database with test data from wikipedia
* `run`: run a python script. The file must have a function `async def run(container):`


## Command Options

- *
  - `--config`: path to configuration file. `defaults to config.(yaml|json)`
  - `--profile`: profile Guillotina while it's running
  - `--profile-output`: where to save profiling output
  - `--monitor`: run with aiomonitor `requires aiomonitor`
  - `--line-profiler`: use line_profiler `requires line_profiler`
  - `--line-profiler-matcher`: fnmatch of module/function to profile `requires line_profiler`
  - `--line-profiler-output`: to store output in a file `requires line_profiler`
  - `--override`: Override configuration values, Example: `--override="root_user.password=foobar"`
- serve:
  - `--host`: host to bind to
  - `--port`: port to bind to
  - `--reload`: auto reload on code changes. `requires aiohttp_autoreload`
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

Then, just add your command to your application's `app_settings` in the `__init__.py`:

```python

app_settings = {
    "commands": {
        "mycommand": "my.package.commands.MyCommand"
    }
}
```


## Overridding configuration

First off, you can use the `--override` setting for all commands to provide
setting overrides in files. For example, `--override="root_user.password=foobar"`.

Additionally, you can override configuration with environment variables. To override
the root password like above, you would do: `G_root_user__password=foobar`.

You can also override json data structures as well:

```bash
export G_cors__allow_origin='["http://localhost:8080"]'
```

Use the double underscore(`__`) to designate nested json structure to assign values.
