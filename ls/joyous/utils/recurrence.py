# ------------------------------------------------------------------------------
# Recurrence
# ------------------------------------------------------------------------------
# Somewhat based upon RFC 5545 RRules, implemented using dateutil.rrule
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
from dateutil.rrule import rrule, rrulestr, rrulebase
from dateutil.rrule import DAILY, WEEKLY, MONTHLY, YEARLY
from dateutil.rrule import weekday as rrweekday
from django.utils.translation import gettext as _
from .telltime import dateShortFormat
from .manythings import toOrdinal, toTheOrdinal, toDaysOffsetStr, hrJoin
from .names import (WEEKDAY_NAMES, WEEKDAY_NAMES_PLURAL,
                    MONTH_NAMES, WRAPPED_MONTH_NAMES)

# ------------------------------------------------------------------------------
class Weekday(rrweekday):
    """
    Represents a day of the week, for every occurence of the week
    or for a specific week in the period.  e.g. The first Friday of the month.
    """
    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "{:+d}{}".format(self.n, s)

    def __str__(self):
        return self._getWhen(0)

    def _getWhen(self, offset, names=WEEKDAY_NAMES):
        weekday = names[self.weekday]
        if offset == 0:
            if not self.n:
                return weekday
            else:
                ordinal = toOrdinal(self.n)
                return _("{ordinal} {weekday}").format(**locals())

        localWeekday = names[(self.weekday + offset) % 7]
        if not self.n:
            return localWeekday
        else:
            theOrdinal = toTheOrdinal(self.n, inTitleCase=False)
            if offset < 0:
                return _("{localWeekday} before "
                         "{theOrdinal} {weekday}").format(**locals())
            else:
                return _("{localWeekday} after "
                         "{theOrdinal} {weekday}").format(**locals())

    def _getPluralWhen(self, offset):
        return self._getWhen(offset, WEEKDAY_NAMES_PLURAL)

MO, TU, WE, TH, FR, SA, SU = EVERYWEEKDAY = map(Weekday, range(7))

# ------------------------------------------------------------------------------
class Recurrence(rrulebase):
    """
    Implementation of the recurrence rules somewhat based upon
    `RFC 5545 <https://tools.ietf.org/html/rfc5545>`_ RRules,
    implemented using dateutil.rrule.

    Does not support timezones ... and probably never will.
    Does not support a frequency of by-hour, by-minute or by-second.
    """
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

    # expose all rrule properties
    #: How often the recurrence repeats. (0,1,2,3)
    freq = property(attrgetter("rule._freq"))

    #: The interval between each freq iteration.
    interval = property(attrgetter("rule._interval"))

    #: Limit on the number of occurrences.
    count = property(attrgetter("rule._count"))

    #: The week numbers to apply the recurrence to.
    byweekno = property(attrgetter("rule._byweekno"))

    #: The year days to apply the recurrence to.
    byyearday = property(attrgetter("rule._byyearday"))

    #: An offset from Easter Sunday.
    byeaster = property(attrgetter("rule._byeaster"))

    #: The nth occurrence of the rule inside the frequency period.
    bysetpos = property(attrgetter("rule._bysetpos"))

    @property
    def dtstart(self):
        """
        The recurrence start date.
        """
        return self.rule._dtstart.date()

    @property
    def frequency(self):
        """
        How often the recurrence repeats.
        ("YEARLY", "MONTHLY", "WEEKLY", "DAILY")
        """
        freqOptions = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY")
        if self.rule._freq < len(freqOptions):
            return freqOptions[self.rule._freq]
        else:
            return "unsupported_frequency_{}".format(self.rule._freq)

    @property
    def until(self):
        """
        The last occurence in the rule is the greatest date that is
        less than or equal to the value specified in the until parameter.
        """
        if self.rule._until is not None:
            return self.rule._until.date()

    @property
    def wkst(self):
        """
        The week start day.  The default week start is got from
        calendar.firstweekday() which Joyous sets based on the Django
        FIRST_DAY_OF_WEEK format.
        """
        return Weekday(self.rule._wkst)

    @property
    def byweekday(self):
        """
        The weekdays where the recurrence will be applied.  In RFC5545 this is
        called BYDAY, but is renamed by dateutil to avoid ambiguity.
        """
        retval = []
        if self.rule._byweekday:
            retval += [Weekday(day) for day in self.rule._byweekday]
        if self.rule._bynweekday:
            retval += [Weekday(day, n) for day, n in self.rule._bynweekday]
        return retval

    @property
    def bymonthday(self):
        """
        The month days where the recurrence will be applied.
        """
        retval = []
        if self.rule._bymonthday:
            retval += self.rule._bymonthday
        if self.rule._bynmonthday:
            retval += self.rule._bynmonthday
        return retval

    @property
    def bymonth(self):
        """
        The months where the recurrence will be applied.
        """
        if self.rule._bymonth:
            return list(self.rule._bymonth)
        else:
            return []

    def _iter(self):
        for occurence in self.rule._iter():
            yield occurence.date()

    # __len__() introduces a large performance penality.
    def getCount(self):
        """
        How many occurrences will be generated.
        """
        return self.rule.count()

    def __eq__(self, other):
        my = self.rule
        if isinstance(other, Recurrence):
            their = other.rule
        elif isinstance(other, rrule):
            their = other
        else:
            return NotImplemented
        theirDtstart = their._dtstart.date()
        theirUntil = their._until
        if theirUntil is not None:
            theirUntil = theirUntil.date()
        return (my._freq        == their._freq        and
                my._interval    == their._interval    and
                my._count       == their._count       and
                my._byweekno    == their._byweekno    and
                my._byyearday   == their._byyearday   and
                my._byeaster    == their._byeaster    and
                my._bysetpos    == their._bysetpos    and
                self.dtstart    == theirDtstart       and
                self.until      == theirUntil         and
                my._wkst        == their._wkst        and
                my._byweekday   == their._byweekday   and
                my._bynweekday  == their._bynweekday  and
                my._bymonthday  == their._bymonthday  and
                my._bynmonthday == their._bynmonthday and
                my._bymonth     == their._bymonth)

    def __repr__(self):
        dtstart = ""
        if self.dtstart:
            dtstart = "DTSTART:{:%Y%m%d}\n".format(self.dtstart)
        rrule = "RRULE:{}".format(self._getRrule())
        retval = dtstart + rrule
        return retval

    def _getRrule(self, untilDt=None):
        # untilDt is the UTC datetime version of self.until
        if untilDt and untilDt.utcoffset() != dt.timedelta(0):
            raise TypeError("untilDt must be a UTC datetime")
        parts = ["FREQ={}".format(self.frequency)]
        if self.interval and self.interval != 1:
            parts.append("INTERVAL={}".format(self.interval))
        if self.wkst:
            parts.append("WKST={!r}".format(self.wkst))
        if self.count:
            parts.append("COUNT={}".format(self.count))
        if untilDt:
            parts.append("UNTIL={:%Y%m%dT%H%M%SZ}".format(untilDt))
        elif self.until:
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
        return ";".join(parts)

    def __str__(self):
        return self._getWhen(0)

    def _getWhen(self, offset, numDays=1):
        retval = ""
        if self.freq == DAILY:
            retval = self.__getDailyWhen()

        elif self.freq == WEEKLY:
            retval = self.__getWeeklyWhen(offset)

        elif self.freq == MONTHLY:
            retval = self.__getMonthlyWhen(offset)

        elif self.freq == YEARLY:
            retval = self.__getYearlyWhen(offset)

        if numDays >= 2:
            retval += " "+_("for {n} days").format(n=numDays)
        if self.until:
            until = self.until + dt.timedelta(days=offset)
            retval += " "+_("(until {when})").format(when=dateShortFormat(until))
        return retval

    def __getDailyWhen(self):
        if self.interval > 1:
            retval = _("Every {n} days").format(n=self.interval)
        else:
            retval = _("Daily")
        return retval

    def __getWeeklyWhen(self, offset):
        retval = hrJoin([d._getPluralWhen(offset) for d in self.byweekday])
        if self.interval == 2:
            retval = _("Fortnightly on {days}").format(days=retval)
        elif self.interval > 2:
            retval = _("Every {n} weeks on {days}").format(n=self.interval,
                                                           days=retval)
        return retval

    def __getMonthlyWhen(self, offset):
        of = " "+_("of the month")
        retval = self.__getMonthlyYearlyWhen(offset, of)
        if self.interval >= 2:
            retval = _("{when}, every {n} months")  \
                     .format(when=retval, n=self.interval)
        return retval

    def __getYearlyWhen(self, offset):
        months = hrJoin([MONTH_NAMES[m] for m in self.bymonth])
        of = " "+_("of {months}").format(months=months)
        retval = self.__getMonthlyYearlyWhen(offset, of)
        if self.interval >= 2:
            retval = _("{when}, every {n} years")   \
                         .format(when=retval, n=self.interval)
        return retval

    def __getMonthlyYearlyWhen(self, offset, of):
        if self.byweekday:
            retval = self.__getWhenByWeekday(offset, of)

        elif len(self.bymonthday) == 1:
            retval = self.__getWhenByMonthday(offset, of)

        else:
            retval = self.__getWhenWithOffsetMonthdays(offset, of)
        return retval

    def __getWhenByWeekday(self, offset, of):
        if (len(self.byweekday) == 7 and
            all(not day.n for day in self.byweekday)):
            retval = _("Everyday")
        else:
            retval = hrJoin([d._getWhen(offset) for d in self.byweekday])
            if not self.byweekday[0].n:
                retval = _("Every {when}").format(when=retval)
            else:
                retval = _("The {when}").format(when=retval)
                retval += of
        return retval

    def __getWhenByMonthday(self, offset, of):
        daysOffset = ""
        d = self.bymonthday[0]
        if d == 1 and offset < 0:
            # bump first day to previous month
            d = offset
            if self.freq != MONTHLY:
                months = [WRAPPED_MONTH_NAMES[m-1] for m in self.bymonth]
                of = " "+_("of {months}").format(months=hrJoin(months))

        elif d == -1 and offset > 0:
            # bump last day to next month
            d = offset
            if self.freq != MONTHLY:
                months = [WRAPPED_MONTH_NAMES[m+1] for m in self.bymonth]
                of = " "+_("of {months}").format(months=hrJoin(months))

        elif 0 < d + offset <= 28:
            # adjust within the month
            d += offset

        else:
            # too complicated don't adjust for any offset
            daysOffset = toDaysOffsetStr(offset)

        theOrdinal = toTheOrdinal(d, inTitleCase=False)
        if daysOffset:
            retval = _("{DaysOffset} {theOrdinal} day")  \
                     .format(DaysOffset=daysOffset, theOrdinal=theOrdinal)
        else:
            TheOrdinal = theOrdinal[0].upper() + theOrdinal[1:]
            retval = _("{TheOrdinal} day").format(TheOrdinal=TheOrdinal)
        retval += of
        return retval

    def __getWhenWithOffsetMonthdays(self, offset, of):
        theOrdinal = hrJoin([toTheOrdinal(d, False) for d in self.bymonthday])
        if offset != 0:
             retval = _("{DaysOffset} {theOrdinal} day")  \
                      .format(DaysOffset=toDaysOffsetStr(offset),
                              theOrdinal=theOrdinal)
        else:
             TheOrdinal = theOrdinal[0].upper() + theOrdinal[1:]
             retval = _("{TheOrdinal} day").format(TheOrdinal=TheOrdinal)
        retval += of
        return retval

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
