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
        'ZODB',
    ],
    tests_require=[
    ],
    entry_points = {
        'console_scripts': [
            'sandbox = sandbox:main',
        ]
    }
)
