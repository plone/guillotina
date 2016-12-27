# COMMAND

You can provide your own CLI commands for plone.server through a simple interface.


## CREATING THE COMMAND

plone.server provides a simple API to write your own CLI commands.


Here is a minimalistic example:

```python

from plone.server.commands import Command
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
