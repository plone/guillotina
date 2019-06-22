import copy
import json
import os
from urllib.parse import urlparse

import pkg_resources

from guillotina import app_settings
from guillotina import configure
from guillotina.api.service import Service
from guillotina.component import getMultiAdapter
from guillotina.interfaces import IAbsoluteURL
from guillotina.utils import get_authenticated_user
from guillotina.utils import get_full_content_path
from guillotina.utils import get_request_scheme
from guillotina.utils import get_security_policy
from guillotina.utils import resolve_dotted_name
from zope.interface import Interface
from zope.interface.interfaces import ComponentLookupError


here = os.path.dirname(os.path.realpath(__file__))


@configure.service(
    method="GET",
    context=Interface,
    name="@swagger",
    permission="guillotina.swagger.View",
    ignore=True,
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
            if desc:
                desc += f" 〜 permission: {service_def['permission']}"
            else:
                desc += f"permission: {service_def['permission']}"

        api_def[path or "/"][method.lower()] = {
            "tags": swagger_conf.get("tags", [""]) or tags,
            "parameters": self.get_data(service_def.get("parameters", {})),
            "produces": self.get_data(service_def.get("produces", [])),
            "summary": self.get_data(service_def.get("summary", "")),
            "description": desc,
            "responses": self.get_data(service_def.get("responses", {})),
        }

    def get_endpoints(self, iface_conf, base_path, api_def, tags=[]):
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
                if (service_def.get("ignore") or
                        service_def.get("swagger_ignore") or swagger_conf.get("ignore")):
                    continue

                if not self.policy.check_permission(
                    service_def["permission"], self.context
                ):
                    continue

                for sub_path in [""] + swagger_conf.get("extra_paths", []):
                    path = os.path.join(base_path, sub_path)
                    if "traversed_service_definitions" in service_def:
                        trav_defs = service_def[
                            "traversed_service_definitions"
                        ]
                        if isinstance(trav_defs, dict):
                            for sub_path, sub_service_def in trav_defs.items():
                                sub_service_def["permission"] = service_def[
                                    "permission"
                                ]
                                self.load_swagger_info(
                                    api_def,
                                    os.path.join(path, sub_path),
                                    method,
                                    tags,
                                    sub_service_def,
                                )
                    else:
                        self.load_swagger_info(
                            api_def, path, method, tags, service_def
                        )

    async def __call__(self):
        user = get_authenticated_user()
        self.policy = get_security_policy(user)
        definition = copy.deepcopy(
            app_settings["swagger"]["base_configuration"]
        )
        vhm = self.request.headers.get("X-VirtualHost-Monster")
        if vhm:
            parsed_url = urlparse(vhm)
            definition["host"] = parsed_url.netloc
            definition["schemes"] = [parsed_url.scheme]
            definition["basePath"] = parsed_url.path
        else:
            definition["host"] = self.request.host
            definition["schemes"] = [get_request_scheme(self.request)]
        if 'version' not in definition['info']:
            definition["info"]["version"] = pkg_resources.get_distribution(
                "guillotina"
            ).version

        api_defs = app_settings["api_definition"]

        path = get_full_content_path(self.context)

        for dotted_iface in api_defs.keys():
            iface = resolve_dotted_name(dotted_iface)
            if iface.providedBy(self.context):
                iface_conf = api_defs[dotted_iface]
                self.get_endpoints(iface_conf, path, definition["paths"])

        definition["definitions"] = app_settings["json_schema_definitions"]
        return definition


AUTH_HTML = '''
    <form id='api_selector'>
      <div id="auth_container">
        <div>
          <a class="authorize__btn" href="#">Authorize</a>
        </div>
      </div>
    </form>
'''


@configure.service(
    method="GET",
    context=Interface,
    name="@docs",
    permission="guillotina.swagger.View",
    ignore=True,
)
async def render_docs_index(context, request):
    if app_settings['swagger'].get('index_html'):
        index_file = app_settings['swagger']['index_html']
    else:
        index_file = os.path.join(here, "index.html")
    with open(index_file) as fi:
        html = fi.read()

    swagger_settings = app_settings["swagger"]
    url = swagger_settings["base_url"] or request.headers.get(
        "X-VirtualHost-Monster"
    )
    if url is None:
        try:
            url = getMultiAdapter((context, request), IAbsoluteURL)()
        except ComponentLookupError:
            url = "{}://{}".format(get_request_scheme(request), request.host)
    swagger_settings["initial_swagger_url"] = url

    if swagger_settings['authentication_allowed']:
        auth = AUTH_HTML
    else:
        auth = ''
    return html.format(
        app_settings=app_settings,
        request=request,
        swagger_settings=json.dumps(swagger_settings),
        base_url=url,
        static_url="{}/swagger_static/".format(url if url != "/" else ""),
        auth=auth,
        title=swagger_settings['base_configuration']['info']['title']
    )
