# ------------------------------------------------------------------------------
# Joyous template tags
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from django import template
from django.utils import timezone
from django.utils.translation import gettext
from ..utils.telltime import timeFormat, dateFormat
from ..models import getAllEventsByDay
from ..models import getAllUpcomingEvents
from ..models import getGroupUpcomingEvents
from ..models import getAllEventsByWeek
from ..models import CalendarPage
from ..utils.weeks import weekday_abbr, weekday_name
from ..edit_handlers import MapFieldPanel

register = template.Library()

@register.inclusion_tag("joyous/tags/events_this_week.html",
                        takes_context=True)
def events_this_week(context):
    """
    Displays a week's worth of events.   Starts week with Monday, unless today is Sunday.
    """
    request = context['request']
    home = request.site.root_page
    cal = CalendarPage.objects.live().descendant_of(home).first()
    calUrl = cal.get_url(request) if cal else None
    calName = cal.title if cal else None
    today = timezone.localdate()
    beginOrd = today.toordinal()
    if today.weekday() != 6:
        # Start week with Monday, unless today is Sunday
        beginOrd -= today.weekday()
    endOrd = beginOrd + 6
    dateFrom = dt.date.fromordinal(beginOrd)
    dateTo   = dt.date.fromordinal(endOrd)
    if cal:
        events = cal._getEventsByDay(request, dateFrom, dateTo)
    else:
        events = getAllEventsByDay(request, dateFrom, dateTo)
    return {'request':      request,
            'today':        today,
            'calendarUrl':  calUrl,
            'calendarName': calName,
            'events':       events }

@register.inclusion_tag("joyous/tags/minicalendar.html",
                        takes_context=True)
def minicalendar(context):
    """
    Displays a little ajax version of the calendar.
    """
    today = timezone.localdate()
    request = context['request']
    home = request.site.root_page
    cal = CalendarPage.objects.live().descendant_of(home).first()
    calUrl = cal.get_url(request) if cal else None
    if cal:
        events = cal._getEventsByWeek(request, today.year, today.month)
    else:
        events = getAllEventsByWeek(request, today.year, today.month)
    return {'request':     request,
            'today':       today,
            'year':        today.year,
            'month':       today.month,
            'calendarUrl': calUrl,
            'monthName':   calendar.month_name[today.month],
            'weekdayInfo': zip(weekday_abbr, weekday_name),
            'events':      events}

@register.inclusion_tag("joyous/tags/upcoming_events_detailed.html",
                        takes_context=True)
def all_upcoming_events(context):
    """
    Displays a list of all upcoming events.
    """
    request = context['request']
    return {'request': request,
            'events':  getAllUpcomingEvents(request)}

@register.inclusion_tag("joyous/tags/upcoming_events_detailed.html",
                        takes_context=True)
def subsite_upcoming_events(context):
    """
    Displays a list of all upcoming events in this site.
    """
    request = context['request']
    home = request.site.root_page
    return {'request': request,
            'events':  getAllUpcomingEvents(request, home=home)}

@register.inclusion_tag("joyous/tags/group_upcoming_events.html",
                        takes_context=True)
def group_upcoming_events(context, group=None):
    """
    Displays a list of all upcoming events that are assigned to a specific
    group.  If the group is not specified it is assumed to be the current page.
    """
    request = context.get('request')
    if group is None:
        group = context.get('page')
    if group:
        events = getGroupUpcomingEvents(request, group)
    else:
        events = []
    return {'request': request,
            'events':  events}

@register.inclusion_tag("joyous/tags/future_exceptions_list.html",
                        takes_context=True)
def future_exceptions(context, rrevent=None):
    """
    Displays a list of all the future exceptions (extra info, cancellations and
    postponements) for a recurring event.  If the recurring event is not
    specified it is assumed to be the current page.
    """
    request = context['request']
    if rrevent is None:
        rrevent = context.get('page')
    if rrevent and hasattr(rrevent, '_futureExceptions'):
        exceptions = rrevent._futureExceptions(request)
    else:
        exceptions = []
    return {'request':    request,
            'exceptions': exceptions}

@register.simple_tag(takes_context=True)
def next_on(context, rrevent=None):
    """
    Displays when the next occurence of a recurring event will be.  If the
    recurring event is not specified it is assumed to be the current page.
    """
    request = context['request']
    if rrevent is None:
        rrevent = context.get('page')
    eventNextOn = getattr(rrevent, '_nextOn', lambda request:None)
    return eventNextOn(request)

@register.inclusion_tag("joyous/tags/location_gmap.html",
                        takes_context=True)
def location_gmap(context, location):
    """Display a link to Google maps iff we are using WagtailGMaps"""
    gmapq = None
    if getattr(MapFieldPanel, "UsingWagtailGMaps", False):
        gmapq = location
    return {'gmapq': gmapq}

# ------------------------------------------------------------------------------
# Format times and dates e.g. on event page
@register.filter
def time_display(time):
    """format the time in a readable way"""
    return timeFormat(time)

@register.filter
def at_time_display(time):
    """format as being "at" some time"""
    return timeFormat(time, prefix=gettext("at "))

@register.filter
def date_display(date):
    """format the date in a readable way"""
    return dateFormat(date)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
