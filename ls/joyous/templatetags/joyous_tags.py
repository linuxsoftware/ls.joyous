from datetime import date
from django import template
from ..utils.telltime import timeFormat, dateFormat
from ..models import getAllEventsByDay
from ..models import getAllUpcomingEvents
from ..models import getGroupUpcomingEvents

register = template.Library()

@register.inclusion_tag('joyous/tags/events_this_week.html')
def events_this_week():
    today = date.today()
    begin_ord = today.toordinal()
    if today.weekday() != 6:
        # Start week with Monday, unless today is Sunday
        begin_ord -= today.weekday()
    end_ord = begin_ord + 6
    date_from = date.fromordinal(begin_ord)
    date_to   = date.fromordinal(end_ord)
    events = getAllEventsByDay(date_from, date_to)
    return {'events': events, 'today':  today }

@register.inclusion_tag('joyous/tags/upcoming_events_detailed.html')
def all_upcoming_events():
    return {'events': getAllUpcomingEvents()}

@register.inclusion_tag('joyous/tags/upcoming_events_list.html',
                        takes_context=True)
def group_upcoming_events(context):
    page = context.get('page')
    events = getGroupUpcomingEvents(page) if page is not None else []
    return {'events': events}

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

