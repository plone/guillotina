from guillotina import configure


app_settings = {
    # provide custom application settings here...
}


def includeme(root):
    """
    custom application initialization here
    """
    configure.scan('{{cookiecutter.package_name}}.api')
    configure.scan('{{cookiecutter.package_name}}.install')
