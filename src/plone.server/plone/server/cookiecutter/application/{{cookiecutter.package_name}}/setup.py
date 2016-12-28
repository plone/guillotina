from setuptools import setup, find_packages

try:
    README = open('README.rst').read()
except:
    README = None

setup(
    name='{{cookiecutter.package_name}}',
    version="1.0.0",
    description='{{cookiecutter.project_short_description}}',
    long_description=README,
    install_requires=[
        'plone.server'
    ],
    author='{{cookiecutter.full_name}}',
    author_email='{{cookiecutter.email}}',
    url='',
    packages=find_packages(exclude=['demo']),
    include_package_data=True,
    tests_require=[
        'pytest',
    ],
    extras_require={
        'test': [
            'pytest',
            'requests',
            'zope.testing'
        ]
    },
    classifiers=[],
    entry_points={
        'plone.server': [
            'include = {{cookiecutter.package_name}}',
        ]
    }
)
