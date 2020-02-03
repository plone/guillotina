from concurrent.futures import ThreadPoolExecutor
from functools import partial
from guillotina import app_settings
from guillotina.contrib.templates.interfaces import IJinjaTemplate
from guillotina.utils import get_current_container
from guillotina.utils import navigate_to
from jinja2 import BaseLoader
from jinja2 import Environment
from jinja2 import PackageLoader
from jinja2 import select_autoescape
from jinja2.exceptions import TemplateNotFound
from lru import LRU

import logging


logger = logging.getLogger("guillotina")


class JinjaUtility:
    def __init__(self, settings):
        self.envs = []
        self._loop = None
        self._cache_size = settings.get("cache_size", 20)
        self._max_workers = settings.get("max_workers", 10)
        self.cache = LRU(self._cache_size)
        self.executor = ThreadPoolExecutor(max_workers=self._max_workers)

    @property
    def templates(self):
        return app_settings.get("templates", [])

    async def initialize(self, app=None):
        self._loop = app.loop
        for template in self.templates:
            package, folder = template.split(":")
            env = Environment(
                loader=PackageLoader(package, folder), autoescape=select_autoescape(["html", "xml", "pt"])
            )
            self.envs.append(env)

    async def finalize(self):
        pass

    async def render(self, name, **options):
        if name in self.cache:
            func = partial(self.cache[name].render, **options)
            return await self._loop.run_in_executor(self.executor, func)
        else:
            template = None
            if name.startswith("/"):
                container = get_current_container()
                try:
                    template_obj = await navigate_to(container, name)
                except KeyError:
                    template_obj = None

                if template_obj is not None and IJinjaTemplate.providedBy(template_obj):
                    template_string: str = template_obj.template
                    template = Environment(loader=BaseLoader()).from_string(template_string)
                else:
                    raise KeyError(f"Wrong traversal template object {name}")
            else:
                for env in self.envs:
                    try:
                        template = env.get_template(name)
                    except TemplateNotFound:
                        pass
                    if template is not None:
                        break

            if template is None:
                raise KeyError(f"Invalid template id {name}")
            else:
                self.cache[name] = template
                func = partial(template.render, **options)
                return await self._loop.run_in_executor(self.executor, func)
