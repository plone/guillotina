# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

setup(
    name='plone.server',
    version=open('VERSION').read().strip(),
    long_description=(open('README.rst').read() + '\n' +
                      open('CHANGELOG.rst').read()),
    py_modules=[
        'plone.server',
    ],
    setup_requires=[
    ],
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['plone'],
    include_package_data=True,
    install_requires=[
        'aiohttp',
        'BTrees',
        'cchardet',
        'plone.dexterity',
        'plone.supermodel',
        'plone.registry',
        'plone.jsonserializer',
        'setuptools',
        'transaction',
        'ZODB',
        'zope.component',
        'zope.component',
        'zope.configuration',
        'zope.configuration',
        'zope.dottedname',
        'zope.event',
        'zope.i18n',
        'zope.i18nmessageid',
        'zope.interface',
        'zope.location',
        'zope.schema',
        'zope.security',
        'pyjwt'
    ],
    tests_require=[
    ],
    entry_points={
        'console_scripts': [
            'sandbox = plone.server.server:main',
        ]
    }
)
