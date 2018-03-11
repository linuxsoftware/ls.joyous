# ------------------------------------------------------------------------------
# Date/time utilities
# ------------------------------------------------------------------------------
import datetime as dt
from django.utils import dateformat

# ------------------------------------------------------------------------------
def getDatetime(date_value, time_value, time_default):
    if time_value is None:
        time_value = time_default
    return dt.datetime.combine(date_value, time_value)

def timeFrom(time_from):
    return time_from if time_from is not None else dt.time.min

def timeTo(time_to):
    return time_to if time_to is not None else dt.time.max

def datetimeFrom(date_from, time_from):
    return dt.datetime.combine(date_from, timeFrom(time_from))

def datetimeTo(date_to, time_to):
    return dt.datetime.combine(date_to, timeTo(time_to))

# ------------------------------------------------------------------------------
def timeFormat(time_from, time_to=None, prefix="", infix="to "):
    # e.g. 10am
    retval = ""
    if time_from != "" and time_from is not None:
        retval += prefix
        retval += dateformat.time_format(time_from, "fA ").lower()
    if time_to != "" and time_to is not None:
        retval += infix
        retval += format(dateformat.time_format(time_to, "fA").lower())
    return retval

def dateFormat(when):
    # e.g. Friday, 14th of April 2011
    retval = ""
    if when is not None:
        retval = dateformat.format(when, "l jS \\o\\f F")
        if when.year != dt.date.today().year:
            retval += " {}".format(when.year)
    return retval

def dateFormatDMY(when):
    # e.g. 14 April 2017
    if when is not None:
        return dateformat.format(when, "j F Y")
    else:
        return ""

# ------------------------------------------------------------------------------
