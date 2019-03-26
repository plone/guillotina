import json
import os
from tempfile import mkstemp

import pytest
from guillotina import testing
from guillotina.commands import get_settings
from guillotina.commands.migrate import MigrateCommand
from guillotina.commands.run import RunCommand
from guillotina.commands.vacuum import VacuumCommand
from guillotina.commands.crypto import CryptoCommand
import io
from contextlib import redirect_stdout


DATABASE = os.environ.get('DATABASE', 'DUMMY')
DB_SCHEMA = os.environ.get('DB_SCHEMA', 'public')


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


@pytest.mark.skipif(DATABASE != 'postgres', reason="Only works with pg")
@pytest.mark.skipif(DB_SCHEMA != 'public',
                    reason="Fixture 'container_command' does not support 'db_schema'")
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


@pytest.mark.skipif(DATABASE != 'postgres', reason="Only works with pg")
@pytest.mark.skipif(DB_SCHEMA != 'public',
                    reason="Fixture 'container_command' does not support 'db_schema'")
def test_run_vacuum_with_container(command_arguments, container_command):
    command = VacuumCommand(command_arguments)
    command.run_command(settings=container_command['settings'])


@pytest.mark.skipif(DATABASE != 'postgres', reason="Only works with pg")
@pytest.mark.skipif(DB_SCHEMA != 'public',
                    reason="Fixture 'container_command' does not support 'db_schema'")
def test_run_migration(command_arguments, container_command):
    command = MigrateCommand(command_arguments)
    command.run_command(settings=container_command['settings'])


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


def test_gen_key_command(command_arguments):
    command_arguments.key_type = 'oct'
    command_arguments.key_size = 256
    command = CryptoCommand(command_arguments)
    settings = testing.get_settings()
    f = io.StringIO()
    with redirect_stdout(f):
        command.run_command(settings=settings)
    out = f.getvalue()
    key = json.loads(out)
    assert 'k' in key
    assert 'kty' in key
