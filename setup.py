# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


long_description = open('README.rst').read() + '\n'
changelog = open('CHANGELOG.rst').read()
found = 0
for line in changelog.splitlines():
    if len(line) > 15 and line[-1] == ')' and line[-4] == '-':
        found += 1
        if found >= 20:
            break
    long_description += '\n' + line


long_description += '''...

You are seeing a truncated changelog.

You can read the `changelog file <https://github.com/plone/guillotina/blob/master/CHANGELOG.rst>`_
for a complete list.

'''

setup(
    name='guillotina',
    version=open('VERSION').read().strip(),
    description='asyncio REST API Resource database',  # noqa
    long_description=long_description,
    keywords=['asyncio', 'REST', 'Framework', 'transactional'],
    author='Ramon & Asko & Nathan',
    author_email='ramon@plone.org',
    classifiers=[
        'License :: OSI Approved :: BSD License',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
    url='https://github.com/plone/guillotina',
    license='BSD',
    setup_requires=[
        'pytest-runner',
    ],
    zip_safe=True,
    include_package_data=True,
    package_data={'': ['*.txt', '*.rst', 'guillotina/documentation/meta/*.json']},
    packages=find_packages(),
    install_requires=[
        'aiohttp>=2.3.6,<2.4.0',
        'jsonschema',
        'python-dateutil',
        'pycryptodome',
        'setuptools',
        'ujson',
        'zope.interface',
        'aioconsole',
        'pyjwt',
        'asyncpg',
        'cffi',
        'PyYAML',
        'aiotask_context'
    ],
    extras_require={
        'test': [
            'pytest<=3.1.0',
            'docker',
            'backoff',
            'psycopg2',
            'pytest-asyncio>=0.8.0',
            'pytest-aiohttp',
            'pytest-cov',
            'coverage==4.0.3',
            'pytest-docker-fixtures'
        ]
    },
    entry_points={
        'console_scripts': [
            'guillotina = guillotina.commands:command_runner',
            'g = guillotina.commands:command_runner'
        ]
    }
)
