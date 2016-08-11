import importlib


def get_param_names(func):
    # TODO: test this
    return func.__code__.co_varnames[:func.__code__.co_argcount]


def get_param_types(func):
    out = []
    for param in get_param_names(func):
        assert param in func.__annotations__, "Unannotated parameter %s on %s" % (param, func)
        out.append(func.__annotations__[param])
    return out


def get_return_type(func):
    assert "return" in func.__annotations__, \
        "No return type found for function: %s.%s" % (func.__module__, func.__name__)
    return func.__annotations__["return"]


def get_types(func):
    return get_param_types(func), get_return_type(func)


def get_global_ref(func):
    mod, name = func.__module__, func.__name__
    assert getattr(importlib.import_module(mod), name) == func
    return mod, name
