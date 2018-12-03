import json
import os
from tempfile import mkstemp

import pytest
from guillotina import testing
from guillotina.commands import get_settings
from guillotina.commands.run import RunCommand


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


def test_get_settings():
    settings = get_settings('doesnotexist.json', [
        'foobar=foobar',
        'foo.bar=foobar'
    ])
    assert settings['foobar'] == 'foobar'
    assert settings['foo']['bar'] == 'foobar'


def test_get_settings_with_environment_variables():
    os.environ.update({
        'G_foobar': 'foobar',
        'G_foo__bar': 'foobar',
        'G_foo__bar1__bar2': json.dumps({
            'foo': 'bar'
        })
    })
    settings = get_settings('doesnotexist.json')
    assert settings['foobar'] == 'foobar'
    assert settings['foo']['bar'] == 'foobar'
    assert settings['foo']['bar1']['bar2'] == {'foo': 'bar'}
