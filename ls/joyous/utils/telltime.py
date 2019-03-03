# ------------------------------------------------------------------------------
# Date/time utilities
# ------------------------------------------------------------------------------
import datetime as dt
from functools import wraps
from inspect import signature
from django.conf import settings
from django.utils import dateformat
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
def timeFrom(time_from):
    """
    Return time_from if it is set, otherwise return the start of the day
    """
    return time_from if time_from is not None else dt.time.min

def timeTo(time_to):
    """
    Return time_to if it is set, otherwise return the end of the day
    """
    return time_to if time_to is not None else dt.time.max

# ------------------------------------------------------------------------------
def timeFormat(time_from, time_to=None, prefix="", infix=None):
    """
    Format the times time_from and optionally time_to, e.g. 10am
    """
    retval = ""
    if time_from != "" and time_from is not None:
        retval += prefix
        retval += dateformat.time_format(time_from, "fA").lower()
    if time_to != "" and time_to is not None:
        to = format(dateformat.time_format(time_to, "fA").lower())
        if infix is not None:
            retval = "{} {} {}".format(retval, infix, to)
        else:
            retval = _("{fromTime} to {toTime}").format(fromTime=retval,
                                                        toTime=to)
    return retval.strip()

def dateFormat(when):
    """
    Format the date when, e.g. Friday 14th of April 2011
    """
    retval = ""
    if when is not None:
        dow = dateformat.format(when, "l")
        dom = dateformat.format(when, "jS")
        month = dateformat.format(when, "F")
        if when.year != dt.date.today().year:
            retval = _("{weekday} {day} of {month} {year}")  \
                    .format(weekday=dow, day=dom, month=month, year=when.year)
        else:
            retval = _("{weekday} {day} of {month}")  \
                    .format(weekday=dow, day=dom, month=month)
    return retval

def dateFormatDMY(when):
    """
    Format when as day month year, e.g. 14 April 2017
    """
    if when is not None:
        return dateformat.format(when, "j F Y")
    else:
        return ""

# ------------------------------------------------------------------------------
