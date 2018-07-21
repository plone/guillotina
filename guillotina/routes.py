from guillotina.response import InvalidRoute

import re


URL_MATCH_RE = re.compile('\{[a-zA-Z\_\-]+\}')


class Route:
    service_configuration = None

    def __init__(self, raw_route):
        self.raw = raw_route
        self.part_names = []

        if not raw_route or raw_route[0] != '@':
            for part in raw_route.split('/'):
                if not part:
                    continue
                if URL_MATCH_RE.match(part):
                    raise InvalidRoute(content={
                        'reason': f'You are trying to mix non-route urls with routing: {raw_route}'  # noqa
                    })
            self.view_name = raw_route
        else:
            # only @ provides potential routing
            self.view_name = raw_route.split('/')[0] + ('/' * raw_route.count('/'))
            route = '/'.join(raw_route.split('/')[1:])

            # check route is valid
            for part in route.split('/'):
                if not part:
                    continue
                if not URL_MATCH_RE.match(part):
                    raise InvalidRoute(content={
                        'reason': f'The route {raw_route} is invalid'
                    })
                self.part_names.append(part.strip('{').strip('}'))

    def matches(self, request, path_parts):
        matchdict = {
            '__parts': path_parts
        }
        for idx, part_name in enumerate(self.part_names):
            matchdict[part_name] = path_parts[idx + 1]
        request.matchdict = matchdict

    def __repr__(self):
        return '<guillotina.routes.Route {}>'.format(self.raw)


def path_to_view_name(path_parts):
    if isinstance(path_parts, str):
        path_parts = path_parts.split('/')

    if path_parts[0][0] != '@':
        return '/'.join(path_parts)
    return path_parts[0] + ('/' * (len(path_parts) - 1))
