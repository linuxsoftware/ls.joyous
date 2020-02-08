# ------------------------------------------------------------------------------
# Many things utilities
# ------------------------------------------------------------------------------
from django.utils.translation import get_language
from django.utils.translation import to_locale
from django.utils.translation import gettext as _, gettext_noop
from num2words import num2words

# ------------------------------------------------------------------------------
def _n2w(n, to):
    try:
        return num2words(n, lang=to_locale(get_language()), to=to)
    except NotImplementedError:
        # fall back to gettext for these words
        gettext_noop("first")
        gettext_noop("second")
        gettext_noop("third")
        gettext_noop("fourth")
        gettext_noop("fifth")
        return _(num2words(n, lang="en", to=to))

# ------------------------------------------------------------------------------
def toOrdinal(n):
    """
    Returns the ordinal name of a number
    e.g. 'first'
    """
    if n == -1:
        retval = _("last")
    elif n == -2:
        retval = _("penultimate")
    elif 1 <= n <= 5:
        retval = _n2w(n, to="ordinal")
    else:
        retval = _n2w(n, to="ordinal_num")
    return retval

# ------------------------------------------------------------------------------
def toTheOrdinal(n, inTitleCase=True):
    """
    Returns the definite article with the ordinal name of a number
    e.g. 'the second'
    Becomes important for languages with multiple definite articles (e.g. French)
    """
    if n == -1:
        retval = _("the last")
    elif n == -2:
        retval = _("the penultimate")
    elif n == 1:
        retval = _("the first")
    elif n == 2:
        retval = _("the second")
    elif n == 3:
        retval = _("the third")
    elif n == 4:
        retval = _("the fourth")
    elif n == 5:
        retval = _("the fifth")
    else:
        retval = _("the")
        if inTitleCase:
            retval = retval.title()
        retval += " "+_n2w(n, to="ordinal_num")
        return retval
    if inTitleCase:
        retval = retval.title()
    return retval

# ------------------------------------------------------------------------------
def toDaysOffsetStr(offset):
    retval = ""
    if offset <= -2:
        n = num2words(-offset, lang=to_locale(get_language()), to="cardinal")
        retval = _("{N} days before").format(N=n.capitalize())
    elif offset == -1:
        retval = _("The day before")
    elif offset == 1:
        retval = _("The day after")
    elif offset >= 2:
        n = num2words(offset, lang=to_locale(get_language()), to="cardinal")
        retval = _("{N} days after").format(N=n.capitalize())
    return retval

# ------------------------------------------------------------------------------
def hrJoin(items):
    """
    Joins items together in a human readable string
    e.g. 'wind, ice and fire'
    """
    conjuction = " "+_("and")+" "
    if len(items) <= 2:
        return conjuction.join(items)
    else:
        return ", ".join(items[:-1]) + conjuction + items[-1]

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
