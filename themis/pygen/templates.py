def apply(op):
    if type(op) == tuple:
        return op[0](*op[1:])
    elif hasattr(op, "_instant"):
        return op._instant
    elif hasattr(op, "_box"):
        return op._box
    else:
        assert type(op) == str
        return op


def indent(x):
    return "\t" + x.replace("\n", "\n\t")


def invoke_nullary(target) -> str:
    return "%s()" % (apply(target),)


def invoke_unary(target, param: str) -> str:
    return "%s(%s)" % (apply(target), apply(param))


def invoke_poly(target, args: list) -> str:
    return "%s(%s)" % (apply(target), ", ".join(apply(arg) for arg in args))


def set(variable, value: str) -> str:
    return "%s = %s" % (apply(variable), value)


def if_then(condition, body) -> str:
    return "if %s:\n%s" % (apply(condition), indent(apply(body)))


def if_else(condition, body_true, body_false) -> str:
    return "if %s:\n%s\nelse:\n%s" % (apply(condition), indent(apply(body_true)), indent(apply(body_false)))


def equals(a, b) -> str:
    return "%s == %s" % (a, b)


def not_equals(a, b) -> str:
    return "%s != %s" % (a, b)


def nop() -> str:
    return "pass"