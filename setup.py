# -*- coding: utf-8 -*-
from setuptools import Extension
from setuptools import find_packages
from setuptools import setup


long_description = open("README.rst").read() + "\n"
changelog = open("CHANGELOG.rst").read()
found = 0
for line in changelog.splitlines():
    if len(line) > 15 and line[-1] == ")" and line[-4] == "-":
        found += 1
        if found >= 20:
            break
    long_description += "\n" + line


long_description += """

...

You are seeing a truncated changelog.

You can read the `changelog file <https://github.com/plone/guillotina/blob/master/CHANGELOG.rst>`_
for a complete list.

"""

lru_module = Extension("guillotina.contrib.cache.lru", sources=["guillotina/contrib/cache/lru.c"])

setup(
    name="guillotina",
    python_requires=">=3.7.0",
    version=open("VERSION").read().strip(),
    description="asyncio REST API Resource database",  # noqa
    long_description=long_description,
    keywords=["asyncio", "REST", "Framework", "transactional"],
    author="Ramon Navarro Bosch & Nathan Van Gheem",
    author_email="ramon@plone.org",
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    url="https://github.com/plone/guillotina",
    license="BSD",
    setup_requires=["pytest-runner"],
    zip_safe=False,
    include_package_data=True,
    ext_modules=[lru_module],
    package_data={"": ["*.txt", "*.rst", "guillotina/documentation/meta/*.json"], "guillotina": ["py.typed"]},
    packages=find_packages(),
    install_requires=[
        'aiohttp>=3.0.0,<3.6.0;python_version<"3.8"',
        'aiohttp>=3.6.0,<4.0.0;python_version>="3.8"',
        "jsonschema",
        "python-dateutil",
        "pycryptodome",
        "jwcrypto",
        "setuptools",
        "ujson",
        "zope.interface",
        "pyjwt",
        "asyncpg",
        "cffi",
        "PyYAML>=5.1",
        "lru-dict",
        "mypy_extensions",
        "argon2-cffi",
        "backoff",
    ],
    extras_require={
        "test": [
            "pytest>=3.8.0<=5.0.0",
            "docker",
            "backoff",
            "psycopg2-binary",
            "pytest-asyncio==0.10.0",
            "pytest-cov",
            "coverage>=4.0.3",
            "pytest-docker-fixtures",
            "pytest-rerunfailures<=7.0",
            "openapi-spec-validator",
        ],
        "docs": [
            "sphinx",
            "recommonmark",
            "sphinxcontrib-httpdomain",
            "sphinxcontrib-httpexample",
            "sphinx-guillotina-theme",
            "sphinx-autodoc-typehints",
        ],
        "redis": ['aioredis>=1.2.0;python_version<"3.8"', 'aioredis>=1.3.0;python_version>="3.8"'],
        "mailer": ["html2text>=2018.1.9", "aiosmtplib>=1.0.6"],
    },
    entry_points={
        "console_scripts": [
            "guillotina = guillotina.commands:command_runner",
            "g = guillotina.commands:command_runner",
        ]
    },
)
