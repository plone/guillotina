# Commands

You can provide your own CLI commands for guillotina through a simple interface.


## Available commands

* guillotina: run the http rest api server
* gmigrate: run available migration steps
* gcli: command line utility to run manually RUN API requests with
* gshell: drop into a shell with root object to manually work with
* gcreate: use cookiecutter to generate guillotina applications


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

Then, in your setup.py file, include an entry point like this for your command:

```python
  setup(
    entry_points={
      'console_scripts': [
            'mycommand = my.package.commands:MyCommand'
      ]
  })
```
