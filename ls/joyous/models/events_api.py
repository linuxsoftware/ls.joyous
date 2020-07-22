# ------------------------------------------------------------------------------
# Joyous Events API
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from contextlib import suppress
from functools import partial
from itertools import chain, groupby
from operator import attrgetter
from django.conf import settings
from django.core.exceptions import (MultipleObjectsReturned, ObjectDoesNotExist,
        PermissionDenied)
from django.utils.translation import gettext_lazy as _
from ..utils.weeks import week_of_month
from .event_base import EventsOnDay
from .one_off_events import SimpleEventPage, MultidayEventPage
from .recurring_events import (RecurringEventPage, MultidayRecurringEventPage,
        PostponementPage, RescheduleMultidayEventPage, ExtraInfoPage,
        CancellationPage, ClosedForHolidaysPage, ExtCancellationPage)

# ------------------------------------------------------------------------------
# API get functions
# ------------------------------------------------------------------------------
def getAllEventsByDay(request, fromDate, toDate, *, home=None, holidays=None):
    """
    Return all the events (under home if given) for the dates given, grouped by
    day.

    :param request: Django request object
    :param fromDate: starting date (inclusive)
    :param toDate: finish date (inclusive)
    :param home: only include events that are under this page (if given)
    :param holidays: the holidays that are celebrated for these dates
    :rtype: list of :class:`EventsOnDay <ls.joyous.models.events.EventsOnDay>` objects
    """
    qrys = [SimpleEventPage.events(request).byDay(fromDate, toDate),
            MultidayEventPage.events(request).byDay(fromDate, toDate),
            RecurringEventPage.events(request, holidays).byDay(fromDate, toDate),
            PostponementPage.events(request).byDay(fromDate, toDate)]
    # Cancellations and ExtraInfo pages are returned by RecurringEventPage.byDay
    if home is not None:
        qrys = [qry.descendant_of(home) for qry in qrys]
    evods = _getEventsByDay(fromDate, qrys, holidays)
    return evods

def getAllEventsByWeek(request, year, month, *, home=None, holidays=None):
    """
    Return all the events (under home if given) for the given month, grouped by
    week.

    :param request: Django request object
    :param year: the year
    :type year: int
    :param month: the month
    :type month: int
    :param home: only include events that are under this page (if given)
    :param holidays: the holidays that are celebrated for these dates
    :returns: a list of sublists (one for each week) each of 7 elements which are either None for days outside of the month, or the events on the day.
    :rtype: list of lists of None or :class:`EventsOnDay <ls.joyous.models.events.EventsOnDay>` objects
    """
    return _getEventsByWeek(year, month,
                            partial(getAllEventsByDay, request,
                                    home=home, holidays=holidays))

def getAllUpcomingEvents(request, *, home=None, holidays=None):
    """
    Return all the upcoming events (under home if given).

    :param request: Django request object
    :param home: only include events that are under this page (if given)
    :param holidays: holidays that may affect these events
    :rtype: list of the namedtuple ThisEvent (title, page, url)
    """
    qrys = [SimpleEventPage.events(request).upcoming().this(),
            MultidayEventPage.events(request).upcoming().this(),
            RecurringEventPage.events(request, holidays).upcoming().this(),
            PostponementPage.events(request).upcoming().this(),
            ExtraInfoPage.events(request).exclude(extra_title="")
                            .upcoming().this(),
            CancellationPage.events(request).exclude(cancellation_title="")
                            .upcoming().this(),
            ExtCancellationPage.events(request).exclude(cancellation_title="")
                            .upcoming().this(),
            ClosedForHolidaysPage.events(request, holidays)
                            .exclude(cancellation_title="").upcoming().this()]
    if home is not None:
        qrys = [qry.descendant_of(home) for qry in qrys]
    events = sorted(chain.from_iterable(qrys), key=_getUpcomingSort())
    return events

def getGroupUpcomingEvents(request, group, holidays=None):
    """
    Return all the upcoming events that are assigned to the specified group.

    :param request: Django request object
    :param group: for this group page
    :param holidays: holidays that may affect these events
    :rtype: list of the namedtuple ThisEvent (title, page, url)
    """
    if not hasattr(group, 'recurringeventpage_set'):
        # This is not a group page
        return []

    # Get events that are a child of a group page, or a postponement or extra
    # info a child of the recurring event child of the group
    rrEvents = RecurringEventPage.events(request, holidays)                  \
                                        .exclude(group_page=group)           \
                                        .upcoming().child_of(group).this()
    qrys = [SimpleEventPage.events(request).exclude(group_page=group)
                                        .upcoming().child_of(group).this(),
            MultidayEventPage.events(request).exclude(group_page=group)
                                        .upcoming().child_of(group).this(),
            rrEvents]
    for rrEvent in rrEvents:
        qrys += [PostponementPage.events(request).child_of(rrEvent.page)
                                         .upcoming().this(),
                 ExtraInfoPage.events(request).exclude(extra_title="")
                                 .child_of(rrEvent.page).upcoming().this(),
                 CancellationPage.events(request).exclude(cancellation_title="")
                                 .child_of(rrEvent.page).upcoming().this(),
                 ExtCancellationPage.events(request).exclude(cancellation_title="")
                                 .child_of(rrEvent.page).upcoming().this(),
                 ClosedForHolidaysPage.events(request, holidays)
                                 .exclude(cancellation_title="")
                                 .child_of(rrEvent.page).upcoming().this()]

    # Get events that are linked to a group page, or a postponement or extra
    # info child of the recurring event linked to a group
    rrEvents = group.recurringeventpage_set(manager='events').auth(request)  \
                                 .hols(holidays).upcoming().this()
    qrys += [group.simpleeventpage_set(manager='events').auth(request)
                                 .upcoming().this(),
             group.multidayeventpage_set(manager='events').auth(request)
                                 .upcoming().this(),
             rrEvents]
    for rrEvent in rrEvents:
        qrys += [PostponementPage.events(request).child_of(rrEvent.page)
                                 .upcoming().this(),
                 ExtraInfoPage.events(request).exclude(extra_title="")
                                 .child_of(rrEvent.page).upcoming().this(),
                 CancellationPage.events(request).exclude(cancellation_title="")
                                 .child_of(rrEvent.page).upcoming().this(),
                 ExtCancellationPage.events(request).exclude(cancellation_title="")
                                 .child_of(rrEvent.page).upcoming().this(),
                 ClosedForHolidaysPage.events(request, holidays)
                                 .exclude(cancellation_title="")
                                 .child_of(rrEvent.page).upcoming().this()]
    events = sorted(chain.from_iterable(qrys), key=_getUpcomingSort())
    return events

def getAllPastEvents(request, *, home=None, holidays=None):
    """
    Return all the past events (under home if given).

    :param request: Django request object
    :param home: only include events that are under this page (if given)
    :param holidays: holidays that may affect these events
    :rtype: list of the namedtuple ThisEvent (title, page, url)
    """
    qrys = [SimpleEventPage.events(request).past().this(),
            MultidayEventPage.events(request).past().this(),
            RecurringEventPage.events(request, holidays).past().this(),
            PostponementPage.events(request).past().this(),
            ExtraInfoPage.events(request).exclude(extra_title="").past().this(),
            CancellationPage.events(request).exclude(cancellation_title="")
                            .past().this(),
            ExtCancellationPage.events(request).exclude(cancellation_title="")
                            .past().this(),
            ClosedForHolidaysPage.events(request, holidays)
                            .exclude(cancellation_title="")
                            .past().this()]
    if home is not None:
        qrys = [qry.descendant_of(home) for qry in qrys]
    events = sorted(chain.from_iterable(qrys),
                    key=attrgetter('page._past_datetime_from'), reverse=True)
    return events

def getEventFromUid(request, uid):
    """
    Get the event by its UID
    (raises PermissionDenied if we have no authority, ObjectDoesNotExist if it
    is not found).

    :param request: Django request object
    :param uid: iCal unique identifier
    :rtype: list of event pages
    """
    events = []
    with suppress(ObjectDoesNotExist):
        events.append(SimpleEventPage.objects.get(uid=uid))
    with suppress(ObjectDoesNotExist):
        events.append(MultidayEventPage.objects.get(uid=uid))
    with suppress(ObjectDoesNotExist):
        events.append(RecurringEventPage.objects.get(uid=uid))
    # Exceptions do not have uids and are not returned by this function

    if len(events) == 1:
        if events[0].isAuthorized(request):
            return events[0]
        else:
            raise PermissionDenied("No authority for uid={}".format(uid))
    elif len(events) == 0:
        raise ObjectDoesNotExist("No event with uid={}".format(uid))
    else:
        raise MultipleObjectsReturned("Multiple events with uid={}".format(uid))

def getAllEvents(request, *, home=None, holidays=None):
    """
    Return all the events (under home if given).

    :param request: Django request object
    :param home: only include events that are under this page (if given)
    :rtype: list of event pages
    """
    qrys = [SimpleEventPage.events(request).all(),
            MultidayEventPage.events(request).all(),
            RecurringEventPage.events(request, holidays).all()]
    # Does not return exceptions
    if home is not None:
        qrys = [qry.descendant_of(home) for qry in qrys]
    events = sorted(chain.from_iterable(qrys),
                    key=attrgetter('_first_datetime_from'))
    return events

# ------------------------------------------------------------------------------
# API UI functions
# ------------------------------------------------------------------------------
def removeContentPanels(*args):
    """
    Remove the panels and so hide the fields named.
    """
    remove = []
    for arg in args:
        if type(arg) is str:
            remove.append(arg)
        else:
            remove.extend(arg)

    SimpleEventPage._removeContentPanels(remove)
    MultidayEventPage._removeContentPanels(remove)
    RecurringEventPage._removeContentPanels(remove)
    MultidayRecurringEventPage._removeContentPanels(remove)
    PostponementPage._removeContentPanels(remove)
    RescheduleMultidayEventPage._removeContentPanels(remove)

# ------------------------------------------------------------------------------
# Private
# ------------------------------------------------------------------------------
def _getEventsByDay(date_from, eventsByDaySrcs, holidays):
    if holidays is None:
        holidays = {}
    evods = []
    day = date_from
    # TODO would izip be better?
    for srcs in zip(*eventsByDaySrcs):
        days_events       = []
        continuing_events = []
        for src in srcs:
            days_events += src.days_events
            continuing_events += src.continuing_events
        def sortByTime(thisEvent):
            fromTime = thisEvent.page._getFromTime(atDate=day)
            if fromTime is None:
                fromTime = dt.time.max
            return fromTime
        days_events.sort(key=sortByTime)
        holiday = holidays.get(day)
        evods.append(EventsOnDay(day, holiday, days_events, continuing_events))
        day += dt.timedelta(days=1)
    return evods

def _getEventsByWeek(year, month, eventsByDaySrc):
    weeks = []
    firstDay = dt.date(year, month, 1)
    lastDay  = dt.date(year, month, calendar.monthrange(year, month)[1])
    def calcWeekOfMonth(evod):
        return week_of_month(evod.date)
    events = eventsByDaySrc(firstDay, lastDay)
    for weekOfMonth, group in groupby(events, calcWeekOfMonth):
        week = list(group)
        if len(week) < 7:
            padding = [None] * (7 - len(week))
            if weekOfMonth == 0:
                week = padding + week
            else:
                week += padding
        weeks.append(week)
    return weeks

def _getUpcomingSort():
    if getattr(settings, "JOYOUS_UPCOMING_INCLUDES_STARTED", False):
        return attrgetter('page._current_datetime_from')
    else:
        return attrgetter('page._future_datetime_from')

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
