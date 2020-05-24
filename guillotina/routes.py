from guillotina.response import InvalidRoute

import re


URL_MATCH_RE = re.compile(r"\{[a-zA-Z0-9\_\-]+\}")
_EXACT = object()


class RoutePart:
    def __init__(self, name):
        self.name = name

    def matches(self, other):
        return self.name == other

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.name}>"

    def __str__(self):
        return self.name


class PathRoutePart(RoutePart):
    def matches(self, other):
        return True

    def __str__(self):
        return "{" + self.name + ":path}"


class VariableRoutePart(RoutePart):
    def matches(self, other):
        return True

    def __str__(self):
        return "{" + self.name + "}"


class Route:
    """
    In order to mix and match routing with traversal, we need to impose
    some restrictions/compromises.

    - routes are designed for the case when you have a traversal miss
      on a context, then we'll convert the tail to a route lookup
    - routes are registered as key lookups
    - conversions to lookup key need to be done in predictable way
      but still provide usefullness
    - the key lookup needs to be something that a path can be converted
      and matched against
    - multiple variable routes against the same context will not work
    - @ is a special case that short-circuits the traversal machinery

    Examples(route -> lookup key):

    - @foobar -> @foobar
    - @foo/{bar} -> @foo/
    - foo/bar -> foo/
    - foo/{bar} -> foo/

    Notes in the example set, "foo/bar" and "foo/{bar}" translate to the
    same key lookup? This is because there is no way to do the reverse
    conversion from a path lookup.
    """

    service_configuration = None

    def __init__(self, raw_route):
        self.raw = raw_route.strip("/")
        self.route_parts = []

        if not raw_route:
            self.view_name = raw_route
        else:
            parts = self.raw.split("/")
            if URL_MATCH_RE.match(parts[0]):
                # first part of route should not be variable
                raise InvalidRoute(content={"reason": f"First part of route can not be variable {raw_route}"})
            self.view_name = parts[0]
            self.route_parts.append(RoutePart(parts[0]))
            for part in parts[1:]:
                if part.endswith(":path}"):
                    self.view_name = parts[0] + "?"
                    name = part.replace(":path", "").strip("{").strip("}")
                    self.route_parts.append(PathRoutePart(name))
                    break
                else:
                    self.view_name += "/"
                    if URL_MATCH_RE.match(part):
                        self.route_parts.append(VariableRoutePart(part.strip("{").strip("}")))
                    else:
                        self.route_parts.append(RoutePart(part))

    def matches(self, request, path_parts):
        matchdict = {"__parts": path_parts}
        for idx, route_part in enumerate(self.route_parts):
            if isinstance(route_part, PathRoutePart):
                matchdict[route_part.name] = "/".join(path_parts[idx:])
            elif route_part.matches(path_parts[idx]):
                matchdict[route_part.name] = path_parts[idx]
            else:
                raise KeyError(route_part.name)
        request.matchdict = matchdict

    def __repr__(self):
        return "<Route {}>".format(self.raw)


def path_to_view_name(path_parts):
    if isinstance(path_parts, str):
        path_parts = path_parts.split("/")

    return path_parts[0] + ("/" * (len(path_parts) - 1))
