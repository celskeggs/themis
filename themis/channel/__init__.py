from themis.channel.float import *
from themis.channel.boolean import *
from themis.channel.event import *
from themis.channel.discrete import *

def always(value):
    if isinstance(value, (int, float)):
        return always_float(value)
    elif isinstance(value, bool):
        return always_boolean(value)
    else:
        raise Exception("Not a float or boolean: %s" % value)
