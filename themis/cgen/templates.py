def apply(op):
    if type(op) == tuple:
        return op[0](*op[1:])
    elif hasattr(op, "_instant"):
        return op._instant
    elif hasattr(op, "_box"):
        return op._box
    else:
        assert type(op) == str, "bad application type: %s" % op
        return op


def indent(x):
    return "\t" + x.replace("\n", "\n\t")


def invoke_nullary(target) -> str:
    return "%s();" % (apply(target),)


def invoke_unary(target, param: str) -> str:
    # TODO: find a better way to handle semicolons than stripping them off
    return "%s(%s);" % (apply(target), apply(param).rstrip(";"))


def invoke_poly(target, args: list) -> str:
    return "%s(%s);" % (apply(target), ", ".join(apply(arg).rstrip(";") for arg in args))


def set(variable, value: str) -> str:
    return "%s = %s;" % (apply(variable), apply(value).rstrip(";"))


def set_decl(var_type: str, variable, value: str) -> str:
    return "%s %s = %s;" % (var_type, apply(variable), apply(value).rstrip(";"))


def if_then(condition, body) -> str:
    return "if (%s) {\n%s\n}" % (apply(condition), indent(apply(body)))


def if_else(condition, body_true, body_false) -> str:
    return "if (%s) {\n%s\n} else {\n%s\n}" % (apply(condition), indent(apply(body_true)), indent(apply(body_false)))


def operator(a, op: str, b) -> str:
    return "%s %s %s" % (apply(a), op, apply(b))


def equals(a, b) -> str:
    return "%s == %s" % (apply(a), apply(b))


def not_equals(a, b) -> str:
    return "%s != %s" % (apply(a), apply(b))


def nop() -> str:
    return ";"
