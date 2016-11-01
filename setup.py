# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

setup(
    name='plone.server',
    version=open('src/plone.server/VERSION').read().strip(),
    long_description=(open('src/plone.server/README.rst').read() + '\n' +
                      open('src/plone.server/CHANGELOG.rst').read()),
    classifiers=[
        'Framework :: Plone :: 7.0',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    url='https://pypi.python.org/pypi/plone.server',
    license='GPL version 3',
    setup_requires=[
        'pytest-runner',
    ],
    zip_safe=True,
    include_package_data=True,
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['plone'],
    install_requires=[
        'aiohttp',
        'ujson',
        'pycrypto',
        'BTrees',
        'cchardet',
        'plone.dexterity',
        'plone.jsonserializer',
        'plone.registry',
        'plone.supermodel',
        'plone.i18n',
        'plone.indexer',
        'repoze.workflow',
        'setuptools',
        'transaction',
        'ZODB',
        'ZEO',
        'zope.component',
        'zope.configuration',
        'zope.copy',
        'zope.dottedname',
        'zope.event',
        'zope.i18n',
        'zope.i18nmessageid',
        'zope.interface',
        'zope.location',
        'zope.proxy',
        'zope.schema',
        'zope.security'
    ],
    extras_require={
        'test': [
            'pytest',
            'requests'
        ]
    },
    entry_points={
        'console_scripts': [
            'server = plone.server.server:main',
        ]
    }
)
