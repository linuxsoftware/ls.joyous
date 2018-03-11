# ------------------------------------------------------------------------------
# Recurrence
# ------------------------------------------------------------------------------
# Somewhat based upon RFC5545 RRules, implemented using dateutil.rrule
# Does not support timezones ... and probably never will
# Does not support a frequency of by hour, by minute or by second
#
# See also:
#   https://github.com/django-recurrence/django-recurrence
#   https://github.com/dakrauth/django-swingtime

import sys
from operator import attrgetter
import calendar
import datetime as dt
from django.db.models import Field
from django.core.exceptions import ValidationError
from django.forms.fields import Field as FormField
from dateutil.rrule import rrule, rrulestr, rrulebase
from dateutil.rrule import DAILY, WEEKLY, MONTHLY, YEARLY
from dateutil.rrule import weekday as rrweekday
from .utils.telltime import dateFormatDMY
from .utils.manythings import toOrdinal, hrJoin

# ------------------------------------------------------------------------------
class Weekday(rrweekday):
    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "{:+d}{}".format(self.n, s)

    def __str__(self):
        s = calendar.day_name[self.weekday]
        if not self.n:
            return s
        else:
            return "{} {}".format(toOrdinal(self.n), s)

MO, TU, WE, TH, FR, SA, SU = map(Weekday, range(7))
WEEKDAYS = [MO, TU, WE, TH, FR]
WEEKEND = [SA, SU]
EVERYDAY = WEEKDAYS + WEEKEND

# ------------------------------------------------------------------------------
class Recurrence(rrulebase):
    def __init__(self, *args, **kwargs):
        super().__init__()
        arg0 = args[0] if len(args) else None
        if isinstance(arg0, str):
            self.rule = rrulestr(arg0, **kwargs)
            if not isinstance(self.rule, rrule):
                raise ValueError("Only support simple RRules for now")
        elif isinstance(arg0, Recurrence):
            self.rule = arg0.rule
        elif isinstance(arg0, rrule):
            self.rule = arg0
        else:
            self.rule = rrule(*args, **kwargs)

    # expose all
    dtstart     = property(attrgetter("rule._dtstart"))
    freq        = property(attrgetter("rule._freq"))
    interval    = property(attrgetter("rule._interval"))
    wkst        = property(attrgetter("rule._wkst"))
    until       = property(attrgetter("rule._until"))
    count       = property(attrgetter("rule._count"))
    bymonth     = property(attrgetter("rule._bymonth"))
    byweekno    = property(attrgetter("rule._byweekno"))
    byyearday   = property(attrgetter("rule._byyearday"))
    byeaster    = property(attrgetter("rule._byeaster"))
    bysetpos    = property(attrgetter("rule._bysetpos"))

    @property
    def byweekday(self):
        retval = []
        if self.rule._byweekday:
            retval += [Weekday(day) for day in self.rule._byweekday]
        if self.rule._bynweekday:
            retval += [Weekday(day, n) for day, n in self.rule._bynweekday]
        return retval

    @property
    def bymonthday(self):
        retval = []
        if self.rule._bymonthday:
            retval += self.rule._bymonthday
        if self.rule._bynmonthday:
            retval += self.rule._bynmonthday
        return retval

    def _iter(self):
        return self.rule._iter()

    def getCount(self):
        return self.rule.count()

    def __repr__(self):
        freqOptions = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY")
        if self.freq >= len(freqOptions): return ""
        parts = ["FREQ={}".format(freqOptions[self.freq])]
        if self.interval and self.interval != 1:
            parts.append("INTERVAL={}".format(self.interval))
        if self.wkst:
            parts.append("WKST={!r}".format(Weekday(self.wkst)))
        if self.count:
            parts.append("COUNT={}".format(self.count))
        if self.until:
            parts.append("UNTIL={:%Y%m%d}".format(self.until))
        for name, value in [('BYSETPOS',   self.bysetpos),
                            ('BYDAY',      self.byweekday),
                            ('BYMONTH',    self.bymonth),
                            ('BYMONTHDAY', self.bymonthday),
                            ('BYYEARDAY',  self.byyearday),
                            ('BYWEEKNO',   self.byweekno)]:
            if value:
                parts.append("{}={}".format(name,
                                            ",".join(repr(v) for v in value)))
        rrule = "RRULE:{}".format(";".join(parts))
        dtstart = ""
        if self.dtstart:
            dtstart = "DTSTART:{:%Y%m%d}\n".format(self.dtstart)
        retval = dtstart + rrule
        return retval

    def __str__(self):
        retval = ""
        if self.freq == DAILY:
            if self.interval > 1:
                retval = "Every {} days".format(self.interval)
            else:
                retval = "Daily"
        elif self.freq == WEEKLY:
            days = ["{}s".format(d) for d in self.byweekday]
            retval = hrJoin(days)
            if self.interval == 2:
                retval = "Fortnightly on {}".format(retval)
            elif self.interval > 2:
                retval = "Every {} weeks on {}".format(self.interval, retval)
        elif self.freq in (MONTHLY, YEARLY):
            if self.freq == MONTHLY:
                of = " of the month"
            else:
                months = [calendar.month_name[m] for m in self.bymonth]
                of = " of {}".format(hrJoin(months))
            days = []
            if self.byweekday:
                if len(self.byweekday) == 7 and all(not day.n for day in self.byweekday):
                    retval = "Everyday"
                    of = ""
                else:
                    days = ["{}".format(d) for d in self.byweekday]
                    retval = hrJoin(days)
                    if not self.byweekday[0].n:
                        retval = "Every "+retval
                        of = ""
                    else:
                        retval = "The {}".format(retval)
            elif self.bymonthday:
                days = [toOrdinal(d) for d in self.bymonthday]
                retval = "The {} day".format(hrJoin(days))
            retval += of
            if self.interval >= 2:
                if self.freq == MONTHLY:
                    retval = "{}, every {} months".format(retval, self.interval)
                else:
                    retval = "{}, every {} years".format(retval, self.interval)
        if self.until:
            # TODO make format configurable
            retval += " (until {})".format(dateFormatDMY(self.until))
        return retval

# ------------------------------------------------------------------------------
class RecurrenceField(Field):
    description = "The rule for recurring events"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 255
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, Recurrence):
            return value
        try:
            return Recurrence(value)
        except (TypeError, ValueError, UnboundLocalError) as err:
            raise ValidationError("Invalid input for recurrence {}".format(err))

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def get_prep_value(self, rule):
        return repr(rule)

    def get_prep_lookup(self, lookup_type, value):
        raise TypeError('Lookup type %r not supported.' % lookup_type)

    def formfield(self, **kwargs):
        defaults = {'form_class': RecurrenceFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def get_internal_type(self):
        return "CharField"

# ------------------------------------------------------------------------------
from .widgets import RecurrenceWidget
class RecurrenceFormField(FormField):
    widget = RecurrenceWidget

# ------------------------------------------------------------------------------
from wagtail import VERSION as _wt_version
if _wt_version[0] < 2:
    from .edit_handlers1 import ExceptionDatePanel
else:
    from .edit_handlers2 import ExceptionDatePanel

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
