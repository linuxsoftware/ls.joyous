# ------------------------------------------------------------------------------
# Names for i18n
# ------------------------------------------------------------------------------
import sys
from django.utils.translation import gettext_lazy as _
from django.utils import dates

# ------------------------------------------------------------------------------
class _Names(tuple):
    """
    Holds internationalized names and only translates them at the last possible
    moment, when they are accessed.
    """
    def __getitem__(self, i):
        item = super().__getitem__(i)
        if isinstance(i, slice):
            return item
        return str(item)

# ------------------------------------------------------------------------------
#: Names of days of the week, from Monday to Sunday
MONDAY_TO_SUNDAY = WEEKDAY_NAMES = _Names(dates.WEEKDAYS[k] for k in range(7))

#: Names of days of the week, from Sunday to Saturday
SUNDAY_TO_SATURDAY = _Names(dates.WEEKDAYS[k%7] for k in range(6,13))

#: Abbreviations of days of the week, from Mon to Sun
MON_TO_SUN = WEEKDAY_ABBRS = _Names(dates.WEEKDAYS_ABBR[k] for k in range(7))

#: Abbreviations of days of the week, from Sun to Sat
SUN_TO_SAT = _Names(dates.WEEKDAYS_ABBR[k%7] for k in range(6,13))

# ------------------------------------------------------------------------------

#: The names of days of the week in plural, Mondays to Sundays
WEEKDAY_NAMES_PLURAL = _Names((_("Mondays"),
                               _("Tuesdays"),
                               _("Wednesdays"),
                               _("Thursdays"),
                               _("Fridays"),
                               _("Saturdays"),
                               _("Sundays")))

# ------------------------------------------------------------------------------
#: Names of the months, with January at index 1
MONTH_NAMES = _Names(dates.MONTHS.get(k,"") for k in range(13))

#: Names of the months, December, January, ...December, January
WRAPPED_MONTH_NAMES = _Names(dates.MONTHS[k%12+1] for k in range(11,25))

#: Abbreviations of the months, with Jan at index 1
MONTH_ABBRS = _Names(dates.MONTHS_AP.get(k, "") for k in range(13))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
