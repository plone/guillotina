from setuptools import setup

setup(
    name='sandbox',
    version=open('VERSION').read().strip(),
    long_description=(open('README.rst').read() + '\n' +
                      open('CHANGELOG.rst').read()),
    py_modules=[
        'sandbox',
    ],
    setup_requires=[
    ],
    install_requires=[
        'aiohttp',
        'aiohttp_traversal',
        'BTrees',
        'cchardet',
        'setuptools',
        'transaction',
        'venusianconfiguration',
        'ZODB',
        'zope.component',
        'zope.configuration',
        'zope.interface',
        'zope.event',
        'zope.dottedname',
        'zope.i18nmessageid',
        'zope.i18n',
        'zope.location',
        'zope.security',
        'zope.schema',
        'plone.dexterity',
    ],
    tests_require=[
    ],
    entry_points = {
        'console_scripts': [
            'sandbox = sandbox:main',
        ]
    }
)
