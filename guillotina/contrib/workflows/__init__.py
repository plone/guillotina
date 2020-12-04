from guillotina import configure

import glob
import logging
import typing
import yaml


logger = logging.getLogger("guillotina.contrib.workflows")


app_settings = {
    "workflows": {},
    "workflows_content": {},
    "load_utilities": {
        "workflows": {
            "provides": "guillotina.contrib.workflows.interfaces.IWorkflowUtility",
            "factory": "guillotina.contrib.workflows.utility.WorkflowUtility",
            "settings": {},
        }
    },
    "post_serialize": ["guillotina.contrib.workflows.post_serialize.apply_review"],
}

path = "/".join(__file__.split("/")[:-1])

workflows: typing.Any = app_settings["workflows"]
for workflow_file in glob.glob(path + "/base/*.yaml"):
    with open(workflow_file, "r") as f:
        workflow_content = yaml.load(f, Loader=yaml.FullLoader)
    ident = workflow_file.split("/")[-1].rstrip(".yaml")
    workflows[ident] = workflow_content


def includeme(root, settings):
    configure.scan("guillotina.contrib.workflows.permissions")
    configure.scan("guillotina.contrib.workflows.api")
    configure.scan("guillotina.contrib.workflows.behavior")
    configure.scan("guillotina.contrib.workflows.events")
    configure.scan("guillotina.contrib.workflows.utility")
    configure.scan("guillotina.contrib.workflows.subscriber")
    configure.scan("guillotina.contrib.workflows.vocabularies")
