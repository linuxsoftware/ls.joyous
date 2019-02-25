# ------------------------------------------------------------------------------
# Names for i18n
# ------------------------------------------------------------------------------
import sys
from django.utils.translation import gettext_lazy as _
from django.utils import dates

# ------------------------------------------------------------------------------
class _Names(tuple):
    def __getitem__(self, i):
        return str(super().__getitem__(i))

# ------------------------------------------------------------------------------
MONDAY_TO_SUNDAY = WEEKDAY_NAMES = _Names(dates.WEEKDAYS[k] for k in range(7))
SUNDAY_TO_SATURDAY = _Names(dates.WEEKDAYS[k%7] for k in range(6,13))
MON_TO_SUN = WEEKDAY_ABBRS = _Names(dates.WEEKDAYS_ABBR[k] for k in range(7))
SUN_TO_SAT = _Names(dates.WEEKDAYS_ABBR[k%7] for k in range(6,13))

# ------------------------------------------------------------------------------
WEEKDAY_NAMES_PLURAL = _Names((_("Mondays"),
                               _("Tuesdays"),
                               _("Wednesdays"),
                               _("Thursdays"),
                               _("Fridays"),
                               _("Saturdays"),
                               _("Sundays")))

# ------------------------------------------------------------------------------
MONTH_NAMES = _Names(dates.MONTHS.get(k,"") for k in range(13))
WRAPPED_MONTH_NAMES = _Names(dates.MONTHS[k%12+1] for k in range(11,25))
MONTH_ABBRS = _Names(dates.MONTHS_3.get(k, "") for k in range(13))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
