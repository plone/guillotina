from plone.server import configure


app_settings = {
    # provide custom application settings here...
}

configure.addon(
    name="{{cookiecutter.package_name}}",
    title="{{cookiecutter.project_short_description}}",
    handler="{{cookiecutter.package_name}}.install.ManageAddon")


def includeme(root):
    """
    custom application initialization here
    """
    configure.scan('{{cookiecutter.package_name}}.api')
