# -*- coding: utf-8 -*-
from guillotina import configure
from guillotina.addons import Addon


@configure.addon(
    name="{{cookiecutter.package_name}}",
    title="{{cookiecutter.project_short_description}}")
class ManageAddon(Addon):

    @classmethod
    def install(cls, container, request):
        registry = request.container_settings  # noqa
        # install logic here...

    @classmethod
    def uninstall(cls, container, request):
        registry = request.container_settings  # noqa
        # uninstall logic here...
