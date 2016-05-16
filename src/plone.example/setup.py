# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

version = '0.1'

short_description = """\
Example for content types
"""
long_description = open('README.rst').read() + '\n'
long_description += open('CHANGES.rst').read()

setup(
    name='plone.example',
    version=version,
    description=short_description,
    long_description=long_description,
    classifiers=[
        'Framework :: Plone',
        'Framework :: Plone :: 7.0',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='plone example contenttypes',
    url='https://pypi.python.org/pypi/plone.example',
    license='GPL version 3',
    packages=find_packages(exclude=['ez_setup']),
    namespace_packages=['plone'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'setuptools',
        'plone.server'
    ],
    extras_require={
    },
    entry_points="""
    # -*- Entry points: -*-
    [plone.server]
    include = plone.example
    """,
)
