# ------------------------------------------------------------------------------
# Formatting weeks
# Use "Monday" as the first day of the week following European convention
# and ISO 8601, OR use "Sunday" as the first day of the week following Jewish 
# tradition
#     https://en.wikipedia.org/wiki/Week#Week_numbering
#     http://www.cjvlang.com/Dow/SunMon.html
# Keep this the same as the JQueryDatePicker to avoid confusion
# see  http://xdsoft.net/jqplugins/datetimepicker
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from django.conf import settings
from django.utils.formats import get_format
from .names import (MONDAY_TO_SUNDAY, MON_TO_SUN,
                    SUNDAY_TO_SATURDAY, SUN_TO_SAT)

# ------------------------------------------------------------------------------
# Start weeks on Monday
# https://stackoverflow.com/questions/304256/
def _iso_year_start(iso_year):
    "The gregorian calendar date of the first day of the given ISO year"
    fourth_jan = dt.date(iso_year, 1, 4)
    delta = dt.timedelta(fourth_jan.isoweekday()-1)
    return fourth_jan - delta

def _iso_to_gregorian(iso_year, iso_week, iso_day):
    "Gregorian calendar date for the given ISO year, week and day"
    year_start = _iso_year_start(iso_year)
    return year_start + dt.timedelta(days=iso_day-1, weeks=iso_week-1)

def _iso_num_weeks(iso_year):
    "Get the number of ISO-weeks in this year"
    year_start = _iso_year_start(iso_year)
    next_year_start = _iso_year_start(iso_year+1)
    year_num_weeks = ((next_year_start - year_start).days) // 7
    return year_num_weeks

def _iso_info(iso_year, iso_week):
    "Give all the iso info we need from one calculation"
    prev_year_start = _iso_year_start(iso_year-1)
    year_start = _iso_year_start(iso_year)
    next_year_start = _iso_year_start(iso_year+1)
    first_day = year_start + dt.timedelta(weeks=iso_week-1)
    last_day = first_day + dt.timedelta(days=6)
    prev_year_num_weeks = ((year_start - prev_year_start).days) // 7
    year_num_weeks = ((next_year_start - year_start).days) // 7
    return (first_day, last_day, prev_year_num_weeks, year_num_weeks)

def _gregorian_to_iso(date_value):
    "ISO year, week and day for the given Gregorian calendar date"
    return date_value.isocalendar()

def _iso_week_of_month(date_value):
    "0-starting index which ISO-week in the month this date is"
    weekday_of_first = date_value.replace(day=1).weekday()
    return (date_value.day + weekday_of_first - 1) // 7

# ------------------------------------------------------------------------------
# Start weeks on Sunday
def _ssweek_year_start(ssweek_year):
    "The gregorian calendar date of the first day of the given Sundaystarting-week year"
    fifth_jan = dt.date(ssweek_year, 1, 5)
    delta = dt.timedelta(fifth_jan.weekday()+1)
    return fifth_jan - delta

def _ssweek_to_gregorian(ssweek_year, ssweek_week, ssweek_day):
    "Gregorian calendar date for the given Sundaystarting-week year, week and day"
    year_start = _ssweek_year_start(ssweek_year)
    return year_start + dt.timedelta(days=ssweek_day-1, weeks=ssweek_week-1)

def _ssweek_num_weeks(ssweek_year):
    "Get the number of Sundaystarting-weeks in this year"
    year_start = _ssweek_year_start(ssweek_year)
    next_year_start = _ssweek_year_start(ssweek_year+1)
    year_num_weeks = ((next_year_start - year_start).days) // 7
    return year_num_weeks

def _ssweek_info(ssweek_year, ssweek_week):
    "Give all the ssweek info we need from one calculation"
    prev_year_start = _ssweek_year_start(ssweek_year-1)
    year_start = _ssweek_year_start(ssweek_year)
    next_year_start = _ssweek_year_start(ssweek_year+1)
    first_day = year_start + dt.timedelta(weeks=ssweek_week-1)
    last_day = first_day + dt.timedelta(days=6)
    prev_year_num_weeks = ((year_start - prev_year_start).days) // 7
    year_num_weeks = ((next_year_start - year_start).days) // 7
    return (first_day, last_day, prev_year_num_weeks, year_num_weeks)

def _gregorian_to_ssweek(date_value):
    "Sundaystarting-week year, week and day for the given  Gregorian calendar date"
    nextYear = date_value.year+1
    nextYearStart = _ssweek_year_start(nextYear)
    if date_value >= nextYearStart:
        year = nextYear
        yearStart = nextYearStart
    else:
        year = date_value.year
        yearStart = _ssweek_year_start(date_value.year)
    weekNum = ((date_value - yearStart).days) // 7 + 1
    dayOfWeek = date_value.weekday()+1
    return (year, weekNum, dayOfWeek)

def _ssweek_of_month(date_value):
    "0-starting index which Sundaystarting-week in the month this date is"
    weekday_of_first = (date_value.replace(day=1).weekday() + 1) % 7
    return (date_value.day + weekday_of_first - 1) // 7

# ------------------------------------------------------------------------------
def getFirstDayOfWeek():
    return getattr(settings, "JOYOUS_FIRST_DAY_OF_WEEK",
                   get_format("FIRST_DAY_OF_WEEK"))

if getFirstDayOfWeek() == 1:
    calendar.setfirstweekday(calendar.MONDAY)

    #: Give all the info we need from one calculation
    #: (first_day, last_day, prev_year_num_weeks, year_num_weeks)
    week_info = _iso_info

    #: Get the number of weeks in this year
    num_weeks_in_year = _iso_num_weeks

    #: year, week and day for the given Gregorian calendar date
    gregorian_to_week_date = _gregorian_to_iso

    #: Returns a 0-starting index of which week in the month this date is
    week_of_month = _iso_week_of_month

    #: Abbreviations of the days of the week
    weekday_abbr = MON_TO_SUN

    #: Names of the days of the week
    weekday_name = MONDAY_TO_SUNDAY
else:
    calendar.setfirstweekday(calendar.SUNDAY)
    week_info = _ssweek_info
    num_weeks_in_year = _ssweek_num_weeks
    gregorian_to_week_date = _gregorian_to_ssweek
    week_of_month = _ssweek_of_month
    weekday_abbr = SUN_TO_SAT
    weekday_name = SUNDAY_TO_SATURDAY

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
