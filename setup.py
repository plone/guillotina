# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup
from distutils.core import Extension
import os
import sys
import platform


py_impl = getattr(platform, 'python_implementation', lambda: None)
pure_python = os.environ.get('PURE_PYTHON', False)
is_pypy = py_impl() == 'PyPy'
is_jython = 'java' in sys.platform


if pure_python or is_pypy or is_jython:
    ext_modules = []
else:
    optimization_path = os.path.join('guillotina', 'optimizations.c')
    ext_modules = [
        Extension(
            'guillotina.optimizations',
            sources=[optimization_path]),
    ]

setup(
    name='guillotina',
    version=open('VERSION').read().strip(),
    description='asyncio transactional server to build REST API / Websocket with ZODB',  # noqa
    long_description=(open('README.rst').read() + '\n' +
                      open('CHANGELOG.rst').read()),
    keywords=['asyncio', 'ZODB', 'REST', 'Framework', 'transactional'],
    author='Ramon & Asko & Nathan',
    author_email='ramon@plone.org',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Framework :: ZODB',
        'Framework :: Zope3',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    url='https://github.com/plone/guillotina',
    license='GPL version 3',
    setup_requires=[
        'pytest-runner',
    ],
    zip_safe=True,
    include_package_data=True,
    packages=find_packages(),
    ext_modules=ext_modules,
    install_requires=[
        'guillotinadb',
        'aiohttp',
        'jsonschema',
        'python-dateutil',
        'pycrypto',
        'setuptools',
        'six',
        'ujson',
        'zope.component',
        'zope.configuration',
        'zope.i18n',
        'zope.i18nmessageid',
        'zope.interface',
        'zope.schema',
        'zope.annotation',
        'pyjwt',
        'requests'
    ],
    extras_require={
        'test': [
            'pytest',
            'requests',
            'zope.testing'
        ]
    },
    entry_points={
        'console_scripts': [
            'guillotina = guillotina.commands.server:ServerCommand',
            'gcli = guillotina.commands.cli:CliCommand',
            'gshell = guillotina.commands.shell:ShellCommand',
            'gmigrate = guillotina.commands.migrate:MigrateCommand',
            'gcreate = guillotina.commands.create:CreateCommand'
        ]
    }
)
