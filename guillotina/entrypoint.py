from guillotina.factory import make_app

import os


if "G_CONFIG_FILE" not in os.environ:
    raise Exception("You must provide the envar G_CONFIG_FILE")

config_file = os.environ["G_CONFIG_FILE"]
app = make_app(config_file=config_file)
