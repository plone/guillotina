# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

import os


setup(
    name='plone.server',
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
    url='https://github.com/plone/plone.server',
    license='GPL version 3',
    setup_requires=[
        'pytest-runner',
    ],
    zip_safe=True,
    include_package_data=True,
    package_dir=None if os.path.isdir('plone') else {'': os.path.join('src', 'plone.server')},  # noqa
    packages=find_packages('./' if os.path.isdir('plone') else os.path.join('src', 'plone.server'), exclude=['ez_setup']),  # noqa
    namespace_packages=['plone'],
    install_requires=[
        'aiohttp==1.0.5',
        'jsonschema',
        'python-dateutil',
        'BTrees',
        'persistent',
        'plone.behavior',
        'pycrypto',
        'setuptools',
        'six',
        'transaction',
        'ujson',
        'ZEO',
        'ZODB',
        'zope.authentication',
        'zope.component',
        'zope.configuration',
        'zope.dottedname',
        'zope.dublincore',
        'zope.event',
        'zope.i18n',
        'zope.i18nmessageid',
        'zope.interface',
        'zope.lifecycleevent',
        'zope.location',
        'zope.proxy',
        'zope.schema',
        'zope.security',
        'zope.securitypolicy',
        'pyjwt',
        'requests'
    ],
    extras_require={
        'test': [
            'pytest',
            'requests',
            'zope.testing',
        ]
    },
    entry_points={
        'console_scripts': [
            'pserver = plone.server.commands.server:ServerCommand',
            'pcli = plone.server.commands.cli:CliCommand',
            'pshell = plone.server.commands.shell:ShellCommand',
            'pmigrate = plone.server.commands.migrate:MigrateCommand',
            'pcreate = plone.server.commands.create:CreateCommand'
        ]
    }
)
