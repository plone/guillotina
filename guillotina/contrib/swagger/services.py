from guillotina import app_settings
from guillotina import configure
from guillotina.api.service import Service
from guillotina.utils import get_authenticated_user
from guillotina.utils import get_full_content_path
from guillotina.utils import get_request_scheme
from guillotina.utils import get_security_policy
from guillotina.utils import get_url
from guillotina.utils import resolve_dotted_name
from urllib.parse import urlparse
from zope.interface import Interface

import copy
import json
import os
import pkg_resources


here = os.path.dirname(os.path.realpath(__file__))


@configure.service(
    method="GET", context=Interface, name="@swagger", permission="guillotina.swagger.View", ignore=True
)
class SwaggerDefinitionService(Service):
    __allow_access__ = True

    def get_data(self, data):
        if callable(data):
            data = data(self.context)
        return data

    def load_swagger_info(self, api_def, path, method, tags, service_def):
        path = path.rstrip("/")
        if path not in api_def:
            api_def[path or "/"] = {}
        desc = self.get_data(service_def.get("description", ""))
        swagger_conf = service_def.get("swagger", {})
        if swagger_conf.get("display_permission", True):
            perms = service_def.get("permission", "")
            if desc:
                desc += f" 〜 permission: {perms}"
            else:
                desc += f"permission: {perms}"

        api_def[path or "/"][method.lower()] = {
            "tags": swagger_conf.get("tags", [""]) or tags,
            "parameters": self.get_data(service_def.get("parameters", {})),
            "requestBody": self.get_data(service_def.get("requestBody", "")),
            "produces": self.get_data(service_def.get("produces", [])),
            "summary": self.get_data(service_def.get("summary", "")),
            "description": desc,
            "responses": self.get_data(service_def.get("responses", {})),
            "security": "",
        }

    def get_endpoints(self, iface_conf, base_path, api_def, tags=None):
        tags = tags or []
        for method in iface_conf.keys():
            if method == "endpoints":
                for name in iface_conf["endpoints"]:
                    self.get_endpoints(
                        iface_conf["endpoints"][name],
                        os.path.join(base_path, name),
                        api_def,
                        tags=[name.strip("@")],
                    )
            else:
                if method.lower() == "options":
                    continue

                service_def = iface_conf[method]
                swagger_conf = service_def.get("swagger", {})
                if (
                    service_def.get("ignore")
                    or service_def.get("swagger_ignore")
                    or swagger_conf.get("ignore")
                ):
                    continue

                if not self.policy.check_permission(
                    service_def.get("permission", app_settings["default_permission"]), self.context
                ):
                    continue

                for sub_path in [""] + swagger_conf.get("extra_paths", []):
                    path = os.path.join(base_path, sub_path)
                    if "traversed_service_definitions" in service_def:
                        trav_defs = service_def["traversed_service_definitions"]
                        if isinstance(trav_defs, dict):
                            for sub_path, sub_service_def in trav_defs.items():
                                sub_service_def["permission"] = service_def["permission"]
                                self.load_swagger_info(
                                    api_def, os.path.join(path, sub_path), method, tags, sub_service_def
                                )
                    else:
                        self.load_swagger_info(api_def, path, method, tags, service_def)

    async def __call__(self):
        user = get_authenticated_user()
        self.policy = get_security_policy(user)
        definition = copy.deepcopy(app_settings["swagger"]["base_configuration"])
        vhm = self.request.headers.get("X-VirtualHost-Monster")

        if not app_settings["swagger"].get("base_url"):
            if vhm:
                parsed_url = urlparse(vhm)
                host = parsed_url.netloc
                scheme = parsed_url.scheme
                base_path = parsed_url.path
            else:
                host = self.request.host
                scheme = get_request_scheme(self.request)
                base_path = ""
            url = os.path.join(f"{scheme}://{host}", base_path)
        else:
            url = app_settings["swagger"]["base_url"]

        definition["servers"][0]["url"] = url

        if "version" not in definition["info"]:
            definition["info"]["version"] = pkg_resources.get_distribution("guillotina").version

        api_defs = app_settings["api_definition"]

        path = get_full_content_path(self.context)

        for dotted_iface in api_defs.keys():
            iface = resolve_dotted_name(dotted_iface)
            if iface.providedBy(self.context):
                iface_conf = api_defs[dotted_iface]
                self.get_endpoints(iface_conf, path, definition["paths"])

        definition["components"]["schemas"] = app_settings["json_schema_definitions"]
        return definition


@configure.service(
    method="GET", context=Interface, name="@docs", permission="guillotina.swagger.View", ignore=True
)
async def render_docs_index(context, request):
    if app_settings["swagger"].get("index_html"):
        index_file = app_settings["swagger"]["index_html"]
    else:
        index_file = os.path.join(here, "index.html")
    with open(index_file) as fi:
        html = fi.read()

    swagger_settings = copy.deepcopy(app_settings["swagger"])
    url = get_url(request, "")
    swagger_settings["initial_swagger_url"] = url
    return html.format(
        swagger_settings=json.dumps(swagger_settings),
        static_url="{}/swagger_static/".format(url if url != "/" else ""),
        title=swagger_settings["base_configuration"]["info"]["title"],
    )
