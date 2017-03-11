import os


_this = os.path.dirname(os.path.realpath(__file__))
DIR = os.path.join(
    os.sep.join(_this.split(os.sep)[:-2]), 'docs/rest-dumps')
URL = 'http://localhost:8080'
