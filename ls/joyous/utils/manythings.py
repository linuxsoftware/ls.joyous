# ------------------------------------------------------------------------------
# Many things utilities
# ------------------------------------------------------------------------------
from django.utils.translation import get_language
from django.utils.translation import to_locale
from django.utils.translation import gettext as _
from num2words import num2words

# ------------------------------------------------------------------------------
def _num(n, to):
    try:
        return num2words(n, lang=to_locale(get_language()), to=to)
    except NotImplementedError:
        return _(num2words(n, lang="en", to=to))

def toOrdinal(n):
    if n == -1:
        return _("last")
    elif n == -2:
        return _("penultimate")
    elif 1 <= n <= 5:
        return _(_num(n, to="ordinal"))
    else:
        return _(_num(n, to="ordinal_num"))

# ------------------------------------------------------------------------------
def hrJoin(items):
    if len(items) <= 2:
        return _(" and ").join(items)
    else:
        return ", ".join(items[:-1]) + _(" and ") + items[-1]

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
