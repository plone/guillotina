# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup


setup(
    name='guillotina',
    version=open('VERSION').read().strip(),
    description='asyncio REST API Resource database',  # noqa
    long_description=(open('README.rst').read() + '\n' +
                      open('CHANGELOG.rst').read()),
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
        'pycrypto',
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
            'coverage==4.0.3'
        ]
    },
    entry_points={
        'console_scripts': [
            'guillotina = guillotina.commands:command_runner',
            'g = guillotina.commands:command_runner'
        ]
    }
)
