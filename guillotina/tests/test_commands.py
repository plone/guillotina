from guillotina import testing
from guillotina.commands.run import RunCommand
from tempfile import mkstemp

import os
import pytest


DATABASE = os.environ.get('DATABASE', 'DUMMY')


def test_run_command(command_arguments):
    _, filepath = mkstemp(suffix='.py')
    _, filepath2 = mkstemp()
    with open(filepath, 'w') as fi:
        fi.write(f'''
async def run(app):
    with open("{filepath2}", 'w') as fi:
        fi.write("foobar")
''')

    command_arguments.script = filepath
    command = RunCommand(command_arguments)
    settings = testing.get_settings()
    command.run_command(settings=settings)
    with open(filepath2) as fi:
        assert fi.read() == 'foobar'


@pytest.mark.skipif(DATABASE != 'postgres', reason="Cockroach does not have cascade support")
def test_run_command_with_container(command_arguments, container_command):
    _, filepath = mkstemp(suffix='.py')
    _, filepath2 = mkstemp()
    with open(filepath, 'w') as fi:
        fi.write(f'''
async def run(container):
    with open("{filepath2}", 'w') as fi:
        fi.write('foobar')
''')

    command_arguments.script = filepath
    command = RunCommand(command_arguments)
    command.run_command(settings=container_command['settings'])
    with open(filepath2) as fi:
        assert fi.read() == 'foobar'
