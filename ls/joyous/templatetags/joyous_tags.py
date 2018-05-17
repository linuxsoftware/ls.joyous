# ------------------------------------------------------------------------------
# Joyous template tags
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from django import template
from ..utils.telltime import timeFormat, dateFormat
from ..models import getAllEventsByDay
from ..models import getAllUpcomingEvents
from ..models import getGroupUpcomingEvents
from ..models import getAllEventsByWeek
from ..models import CalendarPage
from ..utils.weeks import weekday_abbr, weekday_name

register = template.Library()

@register.inclusion_tag("joyous/tags/events_this_week.html",
                        takes_context=True)
def events_this_week(context):
    request = context['request']
    today = dt.date.today()
    begin_ord = today.toordinal()
    if today.weekday() != 6:
        # Start week with Monday, unless today is Sunday
        begin_ord -= today.weekday()
    end_ord = begin_ord + 6
    date_from = dt.date.fromordinal(begin_ord)
    date_to   = dt.date.fromordinal(end_ord)
    events = getAllEventsByDay(request, date_from, date_to)
    return {'events': events, 'today':  today }

@register.inclusion_tag("joyous/tags/minicalendar.html",
                        takes_context=True)
def minicalendar(context):
    today = dt.date.today()
    request = context['request']
    home = request.site.root_page
    cal = CalendarPage.objects.live().descendant_of(home).first()
    calUrl = cal.get_url(request) if cal else None
    return {'today':       today,
            'year':        today.year,
            'month':       today.month,
            'calendarUrl': calUrl,
            'monthName':   calendar.month_name[today.month],
            'weekdayInfo': zip(weekday_abbr, weekday_name),
            'events':      getAllEventsByWeek(request, today.year, today.month)}

@register.inclusion_tag("joyous/tags/upcoming_events_detailed.html",
                        takes_context=True)
def all_upcoming_events(context):
    request = context['request']
    return {'events': getAllUpcomingEvents(request)}

@register.inclusion_tag("joyous/tags/upcoming_events_detailed.html",
                        takes_context=True)
def subsite_upcoming_events(context):
    request = context['request']
    home = request.site.root_page
    return {'events': getAllUpcomingEvents(request, home)}

@register.inclusion_tag("joyous/tags/upcoming_events_list.html",
                        takes_context=True)
def group_upcoming_events(context):
    page = context.get('page')
    if page:
        request = context['request']
        events = getGroupUpcomingEvents(request, page)
    else:
        events = []
    return {'events': events}

@register.inclusion_tag("joyous/tags/future_exceptions_list.html",
                        takes_context=True)
def future_exceptions(context, event):
    exceptions = event._futureExceptions(context['request'])
    return {'exceptions': exceptions}

@register.simple_tag(takes_context=True)
def next_on(context, event):
    eventNextOn = getattr(event, '_nextOn', lambda _:None)
    return eventNextOn(context['request'])

# Format times and dates e.g. on event page
@register.filter
def time_display(time):
    return timeFormat(time)

@register.filter
def at_time_display(time):
    return timeFormat(time, prefix="at ")

@register.filter
def date_display(date):
    return dateFormat(date)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
