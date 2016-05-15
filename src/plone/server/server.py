# -*- coding: utf-8 -*-
import logging

from aiohttp import web

from plone.server.factory import make_app


logger = logging.getLogger('plone.server')


def main():
    logging.basicConfig(level=logging.DEBUG)
    web.run_app(make_app(), port=8080)


if __name__ == "__main__":
    main()
