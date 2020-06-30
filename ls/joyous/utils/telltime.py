# ------------------------------------------------------------------------------
# Date/time utilities
# ------------------------------------------------------------------------------
import datetime as dt
import re
from functools import wraps
from inspect import signature
from django.conf import settings
from django.utils import dateformat
from django.utils import formats
from django.utils import timezone
from django.utils.translation import gettext as _

# ------------------------------------------------------------------------------
def getLocalDate(*args, **kwargs):
    """
    Get the date in the local timezone from date and optionally time
    """
    return getLocalDateAndTime(*args, **kwargs)[0]

def getLocalTime(date, time, *args, **kwargs):
    """
    Get the time in the local timezone from date and time
    """
    if time is not None:
        return getLocalDateAndTime(date, time, *args, **kwargs)[1]

def getLocalTimeAtDate(atDate, time, *args, **kwargs):
    """
    Get the time at a certain date in the local timezone
    """
    if time is not None:
        # I don't know what date to use to get the correct atDate, so
        # try all the possibilities until we get it.
        for offset in (0, 1, -1, 2, -2):
            date = atDate + dt.timedelta(days=offset)
            retval = getLocalDateAndTime(date, time, *args, **kwargs)
            if retval[0] == atDate:
                return retval[1]

def getLocalDateAndTime(date, time, *args, **kwargs):
    """
    Get the date and time in the local timezone from date and optionally time
    """
    localDt = getLocalDatetime(date, time, *args, **kwargs)
    if time is not None:
        return (localDt.date(), localDt.timetz())
    else:
        return (localDt.date(), None)

def getLocalDatetime(date, time, tz=None, timeDefault=dt.time.max):
    """
    Get a datetime in the local timezone from date and optionally time
    """
    localTZ = timezone.get_current_timezone()
    if tz is None or tz == localTZ:
        localDt = getAwareDatetime(date, time, tz, timeDefault)
    else:
        # create in event's time zone
        eventDt = getAwareDatetime(date, time, tz, timeDefault)
        # convert to local time zone
        localDt = eventDt.astimezone(localTZ)
        if time is None:
            localDt = getAwareDatetime(localDt.date(), None, localTZ, timeDefault)
    return localDt

def getAwareDatetime(date, time, tz, timeDefault=dt.time.max):
    """
    Get a datetime in the given timezone from date and optionally time.
    If time is not given it will default to timeDefault if that is given
    or if not then to the end of the day.
    """
    if time is None:
        time = timeDefault
    datetime = dt.datetime.combine(date, time)
    # arbitary rule to handle DST transitions:
    # if daylight savings causes an error then use standard time
    datetime = timezone.make_aware(datetime, tz, is_dst=False)
    return datetime

def todayUtc():
    """
    The current date in the UTC timezone
    """
    return dt.datetime.utcnow().date()

# ------------------------------------------------------------------------------
def getTimeFrom(time_from):
    """
    Return time_from if it is set, otherwise return the start of the day
    """
    return time_from if time_from is not None else dt.time.min

def getTimeTo(time_to):
    """
    Return time_to if it is set, otherwise return the end of the day
    """
    return time_to if time_to is not None else dt.time.max

# ------------------------------------------------------------------------------
re_formatchars = re.compile(r'(?<!\\)([aAbBcdDeEfFgGhHiIjlLmMnNoOPqrsStTUuwWXyYzZ])')
re_escaped = re.compile(r'\\(.)')

class _Formatter(dateformat.DateFormat):
    def format(self, formatstr):
        pieces = []
        for i, piece in enumerate(re_formatchars.split(str(formatstr))):
            if i % 2:
                pieces.append(str(getattr(self, piece)()))
            elif piece:
                pieces.append(re_escaped.sub(r'\1', piece))
        return ''.join(pieces)

    def q(self):
        "'am' or 'pm'"
        if self.data.hour > 11:
            return _('pm')
        return _('am')

    def X(self):
        "Year, if it is not the current year, 4 digits; e.g. '1999'"
        retval = ""
        if self.data.year != dt.date.today().year:
            retval = str(self.data.year)
        return retval

def _timeFormat(when, formatStr):
    """
    Format a single time, e.g. 10am
    """
    if formatStr:
        retval = _Formatter(when).format(formatStr)
    else:
        retval = formats.time_format(when)
    return retval

def timeFormat(time_from, time_to=None, prefix="", infix=None):
    """
    Format the times time_from and optionally time_to, e.g. 10am

    Uses the format given by JOYOUS_TIME_FORMAT if that is set, or otherwise
    the standard Django time format.
    """
    formatStr = getattr(settings, 'JOYOUS_TIME_FORMAT', None)   # e.g. "fq"
    retval = ""
    if time_from != "" and time_from is not None:
        retval += prefix
        retval += _timeFormat(time_from, formatStr)
    if time_to != "" and time_to is not None:
        to = _timeFormat(time_to, formatStr)
        if infix is None:
            infix = _("to")
        retval = "{} {} {}".format(retval, infix, to)
    return retval.strip()

def dateFormat(when):
    """
    Format the date when, e.g. Friday 14th of April 2011

    Uses the format given by JOYOUS_DATE_FORMAT if that is set, or otherwise
    the standard Django date format.
    """
    retval = ""
    if when is not None:
        formatStr = getattr(settings, 'JOYOUS_DATE_FORMAT', None)   # e.g. "l jS \\o\\f F X"
        if formatStr:
            retval = _Formatter(when).format(formatStr)
        else:
            retval = formats.date_format(when)
    return retval.strip()

def dateShortFormat(when):
    """
    Short version of the date when, e.g. 14 April 2017

    Uses the format given by JOYOUS_DATE_SHORT_FORMAT if that is set, or otherwise
    the standard Django date format.
    """
    retval = ""
    if when is not None:
        formatStr = getattr(settings, 'JOYOUS_DATE_SHORT_FORMAT', None)   # e.g. "j F Y"
        if formatStr:
            retval = _Formatter(when).format(formatStr)
        else:
            retval = formats.date_format(when, "SHORT_DATE_FORMAT")
    return retval.strip()

# ------------------------------------------------------------------------------
