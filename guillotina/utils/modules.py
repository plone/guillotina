from guillotina.gtypes import ResolvableType
from typing import Any
from zope.interface.interfaces import IInterface

import importlib
import inspect
import os
import pathlib
import sys
import types


def import_class(import_string: str) -> types.ModuleType:
    """
    Import class from string

    :param import_string: dotted class name
    """
    t = import_string.rsplit(".", 1)
    return getattr(importlib.import_module(t[0]), t[1], None)


def resolve_dotted_name(name: str) -> Any:
    """
    import the provided dotted name

    >>> resolve_dotted_name('guillotina.interfaces.IRequest')
    <InterfaceClass guillotina.interfaces.IRequest>

    :param name: dotted name
    """
    if not isinstance(name, str):
        return name  # already an object
    names = name.split(".")
    used = names.pop(0)
    found = __import__(used)
    for n in names:
        used += "." + n
        try:
            found = getattr(found, n)
        except AttributeError:
            __import__(used)
            found = getattr(found, n)

    return found


def get_caller_module(
    level: int = 2, sys: types.ModuleType = sys
) -> types.ModuleType:  # pylint: disable=W0621
    """
    Pulled out of pyramid
    """
    module_globals = sys._getframe(level).f_globals  # type: ignore
    module_name = module_globals.get("__name__") or "__main__"
    module = sys.modules[module_name]  # type: ignore
    return module


def resolve_module_path(path: str) -> str:
    if len(path) > 0 and path[0] == ".":
        caller_mod = get_caller_module()
        caller_path = get_module_dotted_name(caller_mod)
        caller_path = ".".join(caller_path.split(".")[: -path.count("..")])
        path = caller_path + "." + path.split("..")[-1].strip(".")
    return path


def get_module_dotted_name(ob) -> str:
    return getattr(ob, "__module__", None) or getattr(ob, "__name__", None)


def get_dotted_name(ob: ResolvableType) -> str:
    """
    Convert a module/class/function to dotted path string

    :param ob: the object you'd like to convert
    """
    if inspect.isclass(ob) or IInterface.providedBy(ob) or isinstance(ob, types.FunctionType):
        name = ob.__name__
    else:
        name = ob.__class__.__name__
    return ob.__module__ + "." + name


# get_class_dotted_name is deprecated
get_class_dotted_name = get_dotted_name


def resolve_path(file_path: str) -> pathlib.Path:
    """
    Resolve path to file inside python module

    >>> resolve_path('guillotina:__init__.py')
    PosixPath('/Users/user/guillotina/guillotina/__init__.py')

    :param file_path: `module:path` string
    """
    if ":" in file_path:
        # referencing a module
        dotted_mod_name, _, rel_path = file_path.partition(":")
        module = resolve_dotted_name(dotted_mod_name)
        if module is None:
            raise Exception("Invalid module for static directory {}".format(file_path))
        file_path = os.path.join(os.path.dirname(os.path.realpath(module.__file__)), rel_path)
    return pathlib.Path(file_path)
