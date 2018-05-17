# ------------------------------------------------------------------------------
# Many things utilities
# ------------------------------------------------------------------------------
import inflect
from itertools import chain

# ------------------------------------------------------------------------------
__inflection = inflect.engine()

def toOrdinal(n):
    ordinal = ""
    if n == -1:
        ordinal = "last"
    elif n == -2:
        ordinal = "penultimate"
    elif n > 0:
        ordinal = __inflection.ordinal(n)
        if 1 <= n <= 5:
            # use first, second etc up to fifth
            ordinal = __inflection.number_to_words(ordinal)
    return ordinal

# ------------------------------------------------------------------------------
def hrJoin(items):
    if len(items) <= 2:
        return " and ".join(items)
    else:
        return ", ".join(items[:-1]) + " and " + items[-1]

# ------------------------------------------------------------------------------
def pile(*iters):
    return list(chain(*iters))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
