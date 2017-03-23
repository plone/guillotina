# Commands

You can provide your own CLI commands for guillotina through a simple interface.


## Available commands

* serve: run the http rest api server(this is default command if none given)
* cli: command line utility to run manually RUN API requests with
* shell: drop into a shell with root object to manually work with
* create: use cookiecutter to generate guillotina applications


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
