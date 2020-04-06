# ------------------------------------------------------------------------------
# Joyous events models
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from collections import namedtuple
from contextlib import suppress
from functools import partial
from itertools import chain, groupby
from operator import attrgetter
from uuid import uuid4
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, PermissionDenied
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.query import ModelIterable
from django.forms import widgets
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils import translation
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext, gettext_noop
from timezone_field import TimeZoneField
from wagtail.core.query import PageQuerySet
from wagtail.core.models import Page, PageManager, PageViewRestriction
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import (FieldPanel, MultiFieldPanel,
        PageChooserPanel)
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images import get_image_model_string
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.search import index
from wagtail.admin.forms import WagtailAdminPageForm
from ..utils.mixins import ProxyPageMixin
from ..utils.telltime import (getAwareDatetime, getLocalDatetime,
        getLocalDateAndTime, getLocalDate, getLocalTime, todayUtc)
from ..utils.telltime import getTimeFrom, getTimeTo
from ..utils.telltime import timeFormat, dateFormat
from ..utils.weeks import week_of_month
from ..fields import RecurrenceField
from ..edit_handlers import ExceptionDatePanel, TimePanel, MapFieldPanel
from .groups import get_group_model_string, get_group_model


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
            RecurringEventPage.events(request).byDay(fromDate, toDate),
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

def getAllUpcomingEvents(request, *, home=None):
    """
    Return all the upcoming events (under home if given).

    :param request: Django request object
    :param home: only include events that are under this page (if given)
    :rtype: list of the namedtuple ThisEvent (title, page, url)
    """
    qrys = [SimpleEventPage.events(request).upcoming().this(),
            MultidayEventPage.events(request).upcoming().this(),
            RecurringEventPage.events(request).upcoming().this(),
            PostponementPage.events(request).upcoming().this(),
            ExtraInfoPage.events(request).exclude(extra_title="").upcoming()
                            .this(),
            CancellationPage.events(request).exclude(cancellation_title="")
                            .upcoming().this()]
    if home is not None:
        qrys = [qry.descendant_of(home) for qry in qrys]
    events = sorted(chain.from_iterable(qrys), key=__getUpcomingSort())
    return events

def getGroupUpcomingEvents(request, group):
    """
    Return all the upcoming events that are assigned to the specified group.

    :param request: Django request object
    :param group: for this group page
    :rtype: list of the namedtuple ThisEvent (title, page, url)
    """
    if not hasattr(group, 'recurringeventpage_set'):
        # This is not a group page
        return []

    # Get events that are a child of a group page, or a postponement or extra
    # info a child of the recurring event child of the group
    rrEvents = RecurringEventPage.events(request).exclude(group_page=group) \
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
                                 .child_of(rrEvent.page).upcoming().this()]

    # Get events that are linked to a group page, or a postponement or extra
    # info a child of the recurring event linked to a group
    rrEvents = group.recurringeventpage_set(manager='events').auth(request)  \
                                                        .upcoming().this()
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
                                 .child_of(rrEvent.page).upcoming().this()]
    events = sorted(chain.from_iterable(qrys), key=__getUpcomingSort())
    return events

def getAllPastEvents(request, *, home=None):
    """
    Return all the past events (under home if given).

    :param request: Django request object
    :param home: only include events that are under this page (if given)
    :rtype: list of the namedtuple ThisEvent (title, page, url)
    """
    qrys = [SimpleEventPage.events(request).past().this(),
            MultidayEventPage.events(request).past().this(),
            RecurringEventPage.events(request).past().this(),
            PostponementPage.events(request).past().this(),
            ExtraInfoPage.events(request).exclude(extra_title="").past().this(),
            CancellationPage.events(request).exclude(cancellation_title="")
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

def getAllEvents(request, *, home=None):
    """
    Return all the events (under home if given).

    :param request: Django request object
    :param home: only include events that are under this page (if given)
    :rtype: list of event pages
    """
    qrys = [SimpleEventPage.events(request).all(),
            MultidayEventPage.events(request).all(),
            RecurringEventPage.events(request).all()]
    # Does not return exceptions
    if home is not None:
        qrys = [qry.descendant_of(home) for qry in qrys]
    events = sorted(chain.from_iterable(qrys),
                    key=attrgetter('_first_datetime_from'))
    return events

# ------------------------------------------------------------------------------
# Private
# ------------------------------------------------------------------------------
def _getEventsByDay(date_from, eventsByDaySrcs, holidays):
    evods = []
    day = date_from
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
        holiday = holidays.get(day) if holidays else None
        evods.append(EventsOnDay(day, holiday, days_events, continuing_events))
        day += _1day
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

def __getUpcomingSort():
    if getattr(settings, "JOYOUS_UPCOMING_INCLUDES_STARTED", False):
        return attrgetter('page._current_datetime_from')
    else:
        return attrgetter('page._future_datetime_from')

# ------------------------------------------------------------------------------
# Helper types and constants
# ------------------------------------------------------------------------------
ThisEvent = namedtuple("ThisEvent", "title page url")

class EventsOnDay:
    """
    The events that occur on a certain day.  Both events that start on that day
    and events that are still continuing.
    """
    def __init__(self, date, holiday=None,
                 days_events=None, continuing_events=None):
        if days_events is None:
            days_events = []
        if continuing_events is None:
            continuing_events = []
        self.date = date
        self.holiday = holiday
        self.days_events = days_events
        self.continuing_events = continuing_events

    @property
    def all_events(self):
        """
        All the events that occur on this day,
        ``days_events + continuing_events``.
        """
        return self.days_events + self.continuing_events

    @property
    def preview(self):
        """
        A short description of some of the events on this day
        (limited to 100 characters).
        """
        return ", ".join(event.title for event in self.all_events)[:100]

    @property
    def weekday(self):
        """
        The weekday abbreviation for this days (e.g. "mon").
        """
        return calendar.day_abbr[self.date.weekday()].lower()

class EventsByDayList(list):
    def __init__(self, fromDate, toDate):
        self.fromOrd = fromDate.toordinal()
        self.toOrd   = toDate.toordinal()
        super().__init__(EventsOnDay(dt.date.fromordinal(ord))
                         for ord in range(self.fromOrd, self.toOrd+1))

    def add(self, thisEvent, pageFromDate, pageToDate):
        pageFromOrd = pageFromDate.toordinal()
        pageToOrd   = pageToDate.toordinal()
        dayNum = pageFromOrd - self.fromOrd
        if 0 <= dayNum <= self.toOrd - self.fromOrd:
            self[dayNum].days_events.append(thisEvent)

        for pageOrd in range(pageFromOrd + 1, pageToOrd + 1):
            dayNum = pageOrd - self.fromOrd
            if 0 <= dayNum <= self.toOrd - self.fromOrd:
                self[dayNum].continuing_events.append(thisEvent)

_1day  = dt.timedelta(days=1)
_2days = dt.timedelta(days=2)

# ------------------------------------------------------------------------------
# Event models
# ------------------------------------------------------------------------------
class EventCategory(models.Model):
    """The category type of an event."""
    class Meta:
        ordering = ["name"]
        verbose_name = _("event category")
        verbose_name_plural = _("event categories")

    code = models.CharField(_("code"), max_length=4, unique=True)
    name = models.CharField(_("name"), max_length=80)

    def __str__(self):
        return self.name

# ------------------------------------------------------------------------------
class EventManager(PageManager):
    def get_queryset(self):
        return self._queryset_class(self.model).live()

    def __call__(self, request):
        # a shortcut
        return self.get_queryset().auth(request)

class EventQuerySet(PageQuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request    = None
        self.postFilter = None

    def _clone(self):
        qs = super()._clone()
        qs.request    = self.request
        qs.postFilter = self.postFilter
        return qs

    def _fetch_all(self):
        super()._fetch_all()
        if self.postFilter:
            self._result_cache[:] = filter(self.postFilter, self._result_cache)

    def count(self):
        if self.postFilter and self._result_cache is None:
            # if we have a postFilter then force a call to _fetch_all
            self._fetch_all()
        return super().count()

    def upcoming(self):
        if getattr(settings, "JOYOUS_UPCOMING_INCLUDES_STARTED", False):
            return self.current()
        else:
            return self.future()

    def current(self):
        qs = self._clone()
        qs.postFilter = self.__predicateBasedOn('_current_datetime_from')
        return qs

    def future(self):
        qs = self._clone()
        qs.postFilter = self.__predicateBasedOn('_future_datetime_from')
        return qs

    def past(self):
        qs = self._clone()
        qs.postFilter = self.__predicateBasedOn('_past_datetime_from')
        return qs

    def __predicateBasedOn(self, attribute):
        def predicate(item):
            # If used after byDay [ e.g. qry.byDay(from, to).upcoming() ] then
            # this will reject the whole days_events if just one event does not
            # match the predicate.
            for event in getattr(item, 'days_events', [item]):
                page = getattr(event, 'page', event)
                if not getattr(page, attribute, False):
                    return False
            return True
        return predicate

    def this(self):
        request = self.request
        class ThisEventIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.title, page, page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisEventIterable
        return qs

    def authorized_q(self, request):
        PASSWORD = PageViewRestriction.PASSWORD
        LOGIN    = PageViewRestriction.LOGIN
        GROUPS   = PageViewRestriction.GROUPS
        KEY      = PageViewRestriction.passed_view_restrictions_session_key

        restrictions = PageViewRestriction.objects.all()
        passed = request.session.get(KEY, [])
        if passed:
            restrictions = restrictions.exclude(id__in=passed,
                                                restriction_type=PASSWORD)
        if request.user.is_authenticated:
            restrictions = restrictions.exclude(restriction_type=LOGIN)
        if request.user.is_superuser:
            restrictions = restrictions.exclude(restriction_type=GROUPS)
        else:
            membership = request.user.groups.all()
            if membership:
                restrictions = restrictions.exclude(groups__in=membership,
                                                    restriction_type=GROUPS)
        q = models.Q()
        for restriction in restrictions:
            q &= ~self.descendant_of_q(restriction.page, inclusive=True)
        return q

    def auth(self, request):
        self.request = request
        if request is None:
            return self
        else:
            return self.filter(self.authorized_q(request))

    # Possible Future feature redact unauthorized events??
    #def redact(self, request)

class EventPageForm(WagtailAdminPageForm):
    def clean(self):
        cleaned_data = super().clean()
        self._checkStartBeforeEnd(cleaned_data)
        return cleaned_data

    def _checkStartBeforeEnd(self, cleaned_data):
        startTime = getTimeFrom(cleaned_data.get('time_from'))
        endTime   = getTimeTo(cleaned_data.get('time_to'))
        if startTime > endTime:
            self.add_error('time_to', _("Event cannot end before it starts"))

# Cannot serialize: functools._lru_cache_wrapper object
# There are some values Django cannot serialize into migration files.
def _get_default_timezone():
    return timezone.get_default_timezone()

class EventBase(models.Model):
    class Meta:
        abstract = True

    uid = models.CharField(max_length=255, db_index=True, editable=False,
                           default=uuid4)
    category = models.ForeignKey(EventCategory,
                                 related_name="+",
                                 verbose_name=_("category"),
                                 on_delete=models.SET_NULL,
                                 blank=True, null=True)
    image = models.ForeignKey(get_image_model_string(),
                              null=True, blank=True,
                              related_name='+',
                              verbose_name=_("image"),
                              on_delete=models.SET_NULL)

    time_from = models.TimeField(_("start time"), null=True, blank=True)
    time_to = models.TimeField(_("end time"), null=True, blank=True)
    tz = TimeZoneField(verbose_name=_("time zone"),
                       default=_get_default_timezone)

    group_page  = models.ForeignKey(get_group_model_string(),
                                    null=True, blank=True,
                                    verbose_name=_("group page"),
                                    on_delete=models.SET_NULL)
    details  = RichTextField(_("details"), blank=True)
    location = models.CharField(_("location"), max_length=255, blank=True)
    website = models.URLField(_("website"), blank=True)

    search_fields = Page.search_fields + [
        index.SearchField('location'),
        index.SearchField('details'),
    ]

    content_panels1 = [
        FieldPanel('details', classname="full"),
        MapFieldPanel('location'),
        FieldPanel('website'),
    ]
    if getattr(settings, "JOYOUS_GROUP_SELECTABLE", False):
        content_panels1.append(PageChooserPanel('group_page'))

    @property
    def group(self):
        """
        The group this event belongs to.  Adding the event as a child of a
        group automatically assigns the event to that group.
        """
        retval = None
        parent = self.get_parent()
        Group = get_group_model()
        if issubclass(parent.specific_class, Group):
            retval = parent.specific
        if retval is None:
            retval = self.group_page
        return retval

    @property
    def _current_datetime_from(self):
        """
        The datetime this event will start or did start in the local timezone, or
        None if it is finished.
        """
        fromDt = self._getFromDt()
        toDt = self._getToDt()
        return fromDt if toDt >= timezone.localtime() else None

    @property
    def _future_datetime_from(self):
        """
        The datetime this event next starts in the local timezone, or None if
        in the past.
        """
        fromDt = self._getFromDt()
        return fromDt if fromDt >= timezone.localtime() else None

    @property
    def _past_datetime_from(self):
        """
        The datetime this event previously started in the local timezone, or
        None if it never did.
        """
        fromDt = self._getFromDt()
        return fromDt if fromDt < timezone.localtime() else None

    @property
    def _first_datetime_from(self):
        """
        The datetime this event first started in the local time zone, or None if
        it never did.
        """
        return self._getFromDt()

    @property
    def status(self):
        """
        The current status of the event (started, finished or pending).
        """
        raise NotImplementedError()

    @property
    def status_text(self):
        """
        A text description of the current status of the event.
        """
        status = self.status
        if status == "finished":
            return _("This event has finished.")
        elif status == "started":
            return _("This event has started.")
        else:
            return ""

    @classmethod
    def _removeContentPanels(cls, remove):
        """
        Remove the panels and so hide the fields named.
        """
        if type(remove) is str:
            remove = [remove]
        cls.content_panels = [panel for panel in cls.content_panels
                              if getattr(panel, "field_name", None) not in remove]

    def isAuthorized(self, request):
        """
        Is the user authorized for the requested action with this event?
        """
        restrictions = self.get_view_restrictions()
        if restrictions and request is None:
            return False
        else:
            return all(restriction.accept_request(request)
                       for restriction in restrictions)

    def get_context(self, request, *args, **kwargs):
        retval = super().get_context(request, *args, **kwargs)
        retval['themeCSS'] = getattr(settings, "JOYOUS_THEME_CSS", "")
        return retval

    def _getLocalWhen(self, date_from, date_to=None):
        """
        Returns a string describing when the event occurs (in the local time zone).
        """
        dateFrom, timeFrom = getLocalDateAndTime(date_from, self.time_from,
                                                 self.tz, dt.time.min)

        if date_to is not None:
            dateTo, timeTo = getLocalDateAndTime(date_to, self.time_to, self.tz)
        else:
            if self.time_to is not None:
                dateTo, timeTo = getLocalDateAndTime(date_from, self.time_to, self.tz)
            else:
                dateTo = dateFrom
                timeTo = None

        if dateFrom == dateTo:
            retval = _("{date} {atTime}").format(date=dateFormat(dateFrom),
                        atTime=timeFormat(timeFrom, timeTo, gettext("at ")))
        else:
            retval = _("{date} {atTime}").format(date=dateFormat(dateFrom),
                        atTime=timeFormat(timeFrom, prefix=gettext("at ")))
            retval = _("{dateTimeFrom} to {dateTo} {atTimeTo}").format(
                        dateTimeFrom=retval.strip(),
                        dateTo=dateFormat(dateTo),
                        atTimeTo=timeFormat(timeTo, prefix=gettext("at ")))
        return retval.strip()

    def _getFromTime(self, atDate=None):
        """
        Time that the event starts (in the local time zone) for the given date.
        """
        raise NotImplementedError()

    def _getFromDt(self):
        """
        Datetime that the event starts (in the local time zone).
        """
        raise NotImplementedError()

    def _getToDt(self):
        """
        Datetime that the event ends (in the local time zone).
        """
        raise NotImplementedError()

def removeContentPanels(remove):
    """
    Remove the panels and so hide the fields named.
    """
    SimpleEventPage._removeContentPanels(remove)
    MultidayEventPage._removeContentPanels(remove)
    RecurringEventPage._removeContentPanels(remove)
    MultidayRecurringEventPage._removeContentPanels(remove)
    PostponementPage._removeContentPanels(remove)

# ------------------------------------------------------------------------------
class SimpleEventQuerySet(EventQuerySet):
    def current(self):
        qs = super().current()
        return qs.filter(date__gte = todayUtc() - _1day)

    def future(self):
        qs = super().future()
        return qs.filter(date__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(date__lte = todayUtc() + _1day)

    def byDay(self, fromDate, toDate):
        request = self.request
        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = EventsByDayList(fromDate, toDate)
                for page in super().__iter__():
                    pageFromDate = getLocalDate(page.date,
                                                page.time_from, page.tz)
                    pageToDate   = getLocalDate(page.date,
                                                page.time_to, page.tz)
                    thisEvent = ThisEvent(page.title, page,
                                          page.get_url(request))
                    evods.add(thisEvent, pageFromDate, pageToDate)
                yield from evods

        qs = self._clone()
        qs._iterable_class = ByDayIterable
        return qs.filter(date__range=(fromDate - _2days, toDate + _2days))

class SimpleEventPage(EventBase, Page):
    events = EventManager.from_queryset(SimpleEventQuerySet)()

    class Meta:
        verbose_name = _("event page")
        verbose_name_plural = _("event pages")
        default_manager_name = "objects"

    parent_page_types = ["joyous.CalendarPage",
                         "joyous.SpecificCalendarPage",
                         "joyous.GeneralCalendarPage",
                         get_group_model_string()]
    subpage_types = []
    base_form_class = EventPageForm

    date    = models.DateField(_("date"), default=dt.date.today)

    content_panels = Page.content_panels + [
        FieldPanel('category'),
        ImageChooserPanel('image'),
        FieldPanel('date'),
        TimePanel('time_from'),
        TimePanel('time_to'),
        FieldPanel('tz'),
        ] + EventBase.content_panels1

    @property
    def status(self):
        """
        The current status of the event (started, finished or pending).
        """
        myNow = timezone.localtime(timezone=self.tz)
        if getAwareDatetime(self.date, self.time_to, self.tz) < myNow:
            return "finished"
        elif getAwareDatetime(self.date, self.time_from, self.tz) < myNow:
            return "started"

    @property
    def when(self):
        """
        A string describing when the event occurs (in the local time zone).
        """
        return self._getLocalWhen(self.date)

    @property
    def at(self):
        """
        A string describing what time the event starts (in the local time zone).
        """
        return timeFormat(self._getFromTime())

    def _getFromTime(self, atDate=None):
        """
        Time that the event starts (in the local time zone).
        """
        return getLocalTime(self.date, self.time_from, self.tz)

    def _getFromDt(self):
        """
        Datetime that the event starts (in the local time zone).
        """
        return getLocalDatetime(self.date, self.time_from, self.tz)

    def _getToDt(self):
        """
        Datetime that the event ends (in the local time zone).
        """
        return getLocalDatetime(self.date, self.time_to, self.tz)

# ------------------------------------------------------------------------------
class MultidayEventQuerySet(EventQuerySet):
    def current(self):
        qs = super().current()
        return qs.filter(date_to__gte = todayUtc() - _1day)

    def future(self):
        qs = super().future()
        return qs.filter(date_from__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(date_from__lte = todayUtc() + _1day)

    def byDay(self, fromDate, toDate):
        request = self.request
        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = EventsByDayList(fromDate, toDate)
                for page in super().__iter__():
                    pageFromDate = getLocalDate(page.date_from,
                                                page.time_from, page.tz)
                    pageToDate   = getLocalDate(page.date_to,
                                                page.time_to, page.tz)
                    thisEvent = ThisEvent(page.title, page,
                                          page.get_url(request))
                    evods.add(thisEvent, pageFromDate, pageToDate)
                yield from evods

        qs = self._clone()
        qs._iterable_class = ByDayIterable
        return qs.filter(date_to__gte   = fromDate - _2days)   \
                 .filter(date_from__lte = toDate + _2days)

class MultidayEventPageForm(EventPageForm):
    def _checkStartBeforeEnd(self, cleaned_data):
        startDate = cleaned_data.get('date_from', dt.date.min)
        endDate   = cleaned_data.get('date_to', dt.date.max)
        if startDate > endDate:
            self.add_error('date_to', _("Event cannot end before it starts"))
        elif startDate == endDate:
            super()._checkStartBeforeEnd(cleaned_data)

class MultidayEventPage(EventBase, Page):
    events = EventManager.from_queryset(MultidayEventQuerySet)()

    class Meta:
        verbose_name = _("multiday event page")
        verbose_name_plural = _("multiday event pages")
        default_manager_name = "objects"

    parent_page_types = ["joyous.CalendarPage",
                         "joyous.SpecificCalendarPage",
                         "joyous.GeneralCalendarPage",
                         get_group_model_string()]
    subpage_types = []
    base_form_class = MultidayEventPageForm

    date_from = models.DateField(_("start date"), default=dt.date.today)
    date_to = models.DateField(_("end date"), default=dt.date.today)

    content_panels = Page.content_panels + [
        FieldPanel('category'),
        ImageChooserPanel('image'),
        FieldPanel('date_from'),
        TimePanel('time_from'),
        FieldPanel('date_to'),
        TimePanel('time_to'),
        FieldPanel('tz'),
        ] + EventBase.content_panels1

    @property
    def status(self):
        """
        The current status of the event (started, finished or pending).
        """
        myNow = timezone.localtime(timezone=self.tz)
        if getAwareDatetime(self.date_to, self.time_to, self.tz) < myNow:
            return "finished"
        elif getAwareDatetime(self.date_from, self.time_from, self.tz) < myNow:
            return "started"

    @property
    def when(self):
        """
        A string describing when the event occurs (in the local time zone).
        """
        return self._getLocalWhen(self.date_from, self.date_to)

    @property
    def at(self):
        """
        A string describing what time the event starts (in the local time zone).
        """
        return timeFormat(self._getFromTime())

    def _getFromTime(self, atDate=None):
        """
        Time that the event starts (in the local time zone).
        """
        return getLocalTime(self.date_from, self.time_from, self.tz)

    def _getFromDt(self):
        """
        Datetime that the event starts (in the local time zone).
        """
        return getLocalDatetime(self.date_from, self.time_from, self.tz)

    def _getToDt(self):
        """
        Datetime that the event ends (in the local time zone).
        """
        return getLocalDatetime(self.date_to, self.time_to, self.tz)

# ------------------------------------------------------------------------------
class RecurringEventQuerySet(EventQuerySet):
    def byDay(self, fromDate, toDate):
        request = self.request

        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = EventsByDayList(fromDate, toDate)
                for page in super().__iter__():
                    exceptions = self.__getExceptionsFor(page)
                    startDelta = dt.timedelta(days=page.num_days + 1)
                    for occurence in page.repeat.between(fromDate - startDelta,
                                                         toDate + _2days, True):
                        thisEvent = None
                        exception = exceptions.get(occurence)
                        if exception:
                            if exception.title:
                                thisEvent = exception
                        else:
                            thisEvent = ThisEvent(page.title, page,
                                                  page.get_url(request))
                        if thisEvent:
                            pageFromDate = getLocalDate(occurence,
                                                        page.time_from, page.tz)
                            daysDelta = dt.timedelta(days=page.num_days - 1)
                            pageToDate = getLocalDate(occurence + daysDelta,
                                                      page.time_to, page.tz)
                            evods.add(thisEvent, pageFromDate, pageToDate)
                yield from evods

            def __getExceptionsFor(self, page):
                dateRange = (fromDate - _2days, toDate + _2days)
                exceptions = {}
                for extraInfo in ExtraInfoPage.events(request).child_of(page)\
                                     .filter(except_date__range=dateRange):
                    title = extraInfo.extra_title or page.title
                    exceptDate = extraInfo.except_date
                    exceptions[exceptDate] = ThisEvent(title, extraInfo,
                                                       extraInfo.get_url(request))
                for cancellation in CancellationPage.events.child_of(page)   \
                                     .filter(except_date__range=dateRange):
                    url = cancellation.getCancellationUrl(request)
                    # The cancellation still affects the event, even if the
                    # user is not authorized to view the cancellation.
                    if cancellation.isAuthorized(request):
                        title = cancellation.cancellation_title
                    else:
                        title = None
                        url = None
                    exceptDate = cancellation.except_date
                    exceptions[exceptDate] = ThisEvent(title, cancellation, url)
                return exceptions

        qs = self._clone()
        qs._iterable_class = ByDayIterable
        return qs

# Panel trickery needed as editing proxy models doesn't work yet :-(
class HiddenNumDaysPanel(FieldPanel):
    class widget(widgets.NumberInput):
        def value_from_datadict(self, data, files, name):
            # validation doesn't like num_days disappearing
            return data.get(name, "1")

    def __init__(self, field_name="num_days", *args, **kwargs):
        super().__init__(field_name, *args, **kwargs)

    def render_as_object(self):
        return super().render_as_object() if self._show() else ""

    def render_as_field(self):
        return super().render_as_field() if self._show() else ""

    def _show(self):
        page = getattr(self, 'instance', None)
        if isinstance(page, (MultidayRecurringEventPage,
                             RescheduleMultidayEventPage)):
            retval = True
        else:
            numDays = getattr(page, 'num_days', 0)
            retval = numDays > 1
        return retval

class RecurringEventPageForm(EventPageForm):
    def _checkStartBeforeEnd(self, cleaned_data):
        numDays = cleaned_data.get('num_days', 1)
        if numDays == 1:
            super()._checkStartBeforeEnd(cleaned_data)

class RecurringEventPage(EventBase, Page):
    events = EventManager.from_queryset(RecurringEventQuerySet)()

    class Meta:
        verbose_name = _("recurring event page")
        verbose_name_plural = _("recurring event pages")
        default_manager_name = "objects"

    parent_page_types = ["joyous.CalendarPage",
                         "joyous.SpecificCalendarPage",
                         "joyous.GeneralCalendarPage",
                         get_group_model_string()]
    subpage_types = ['joyous.ExtraInfoPage',
                     'joyous.CancellationPage',
                     'joyous.PostponementPage']
    base_form_class = RecurringEventPageForm

    repeat   = RecurrenceField(_("repeat"))
    num_days = models.IntegerField(_("number of days"), default=1,
                                   validators=[MinValueValidator(1),
                                               MaxValueValidator(99)])

    content_panels0 = Page.content_panels + [
        FieldPanel('category'),
        ImageChooserPanel('image'),
        FieldPanel('repeat')]
    content_panels1 = [
        TimePanel('time_from'),
        TimePanel('time_to'),
        FieldPanel('tz'),
        ] + EventBase.content_panels1
    content_panels = content_panels0 + [HiddenNumDaysPanel()] + content_panels1

    @property
    def next_date(self):
        """
        Date when this event is next scheduled to occur in the local time zone
        (Does not include postponements, but does exclude cancellations)
        """
        nextDt = self.__localAfter(timezone.localtime(), dt.time.min)
        if nextDt is not None:
            return nextDt.date()

    @property
    def _current_datetime_from(self):
        """
        The datetime this event will start or did start in the local timezone, or
        None if it is finished.
        """
        myNow = timezone.localtime(timezone=self.tz)
        timeFrom = getTimeFrom(self.time_from)
        timeTo = getTimeTo(self.time_to)
        # Yes this ignores DST transitions and milliseconds
        timeDelta = dt.timedelta(days    = self.num_days - 1,
                                 hours   = timeTo.hour   - timeFrom.hour,
                                 minutes = timeTo.minute - timeFrom.minute,
                                 seconds = timeTo.second - timeFrom.second)
        nextDt = self.__after(myNow - timeDelta,
                              excludeCancellations=True,
                              excludeExtraInfo=True)
        if nextDt is not None:
            return getLocalDatetime(nextDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    @property
    def _future_datetime_from(self):
        """
        The datetime this event next starts in the local timezone, or None if
        in the past.
        """
        myNow = timezone.localtime(timezone=self.tz)
        nextDt = self.__after(myNow,
                              excludeCancellations=True,
                              excludeExtraInfo=True)
        if nextDt is not None:
            return getLocalDatetime(nextDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    @property
    def prev_date(self):
        """
        Date when this event last occurred in the local time zone
        (Does not include postponements, but does exclude cancellations)
        """
        prevDt = self.__localBefore(timezone.localtime(), dt.time.min)
        if prevDt is not None:
            return prevDt.date()

    @property
    def _past_datetime_from(self):
        """
        The datetime this event previously started in the local time zone, or
        None if it never did.
        """
        prevDt = self.__localBefore(timezone.localtime(), dt.time.max,
                                    excludeCancellations=True,
                                    excludeExtraInfo=True)
        # Exclude extra info pages as this is used for sorting and the extra
        # info pages sit alongside
        return prevDt

    @property
    def _first_datetime_from(self):
        """
        The datetime this event first started in the local time zone, or None if
        it never did.
        """
        myFromDt = self._getMyFirstDatetimeFrom()
        localTZ = timezone.get_current_timezone()
        return myFromDt.astimezone(localTZ)

    @property
    def status(self):
        """
        The current status of the event (started, finished or pending).
        """
        myNow = timezone.localtime(timezone=self.tz)
        myDaysDelta = dt.timedelta(days=self.num_days - 1)
        # NB: postponements can be created after the until date
        #     so ignore that
        todayStart = getAwareDatetime(myNow.date(), dt.time.min, self.tz)
        eventStart, event = self.__afterOrPostponedTo(todayStart - myDaysDelta)
        # Will miss any postponements that started more than myDaysDelta ago
        # which might still be active if their num_days is longer than that.
        if eventStart is None:
            return "finished"
        eventDaysDelta = dt.timedelta(days=event.num_days - 1)
        eventFinish = getAwareDatetime(eventStart.date() + eventDaysDelta,
                                       event.time_to, self.tz)
        if event.time_from is None:
            eventStart += _1day
        if eventStart < myNow < eventFinish:
            # if there are two occurences on the same day then we may miss
            # that one of them has started
            return "started"
        if (self.repeat.until and eventFinish < myNow and
            self.__afterOrPostponedTo(myNow)[0] is None):
            # only just wound up, the last occurence was earlier today
            return "finished"

    @property
    def status_text(self):
        """
        A text description of the current status of the event.
        """
        status = self.status
        if status == "finished":
            return _("These events have finished.")
        else:
            return super().status_text

    @property
    def when(self):
        """
        A string describing when the event occurs (in the local time zone).
        """
        offset   = 0
        timeFrom = dateFrom = timeTo = dateTo = None
        myFromDt = self.__getMyFromDt()
        if myFromDt is not None:
            offset = timezone.localtime(myFromDt).toordinal() - myFromDt.toordinal()
            dateFrom, timeFrom = getLocalDateAndTime(myFromDt.date(), self.time_from,
                                                     self.tz, dt.time.min)
            daysDelta = dt.timedelta(days=self.num_days - 1)
            dateTo, timeTo = getLocalDateAndTime(myFromDt.date() + daysDelta,
                                                 self.time_to, self.tz)
        if dateFrom == dateTo:
            retval = _("{repeat} {atTime}").format(
                    repeat=self.repeat._getWhen(offset),
                    atTime=timeFormat(timeFrom, timeTo, gettext("at ")))
        else:
            localNumDays = (dateTo - dateFrom).days + 1
            retval = _("{repeat} {startFinishTime}").format(
                    repeat=self.repeat._getWhen(offset, localNumDays),
                    startFinishTime=timeFormat(timeFrom, timeTo,
                                               prefix=gettext("starting at "),
                                               infix=gettext("finishing at")))
        return retval.strip()

    @property
    def at(self):
        """
        A string describing what time the event starts (in the local time zone).
        """
        return timeFormat(self._getFromTime())

    def _getFromTime(self, atDate=None):
        """
        What was the time of this event?  Due to time zones that depends what
        day we are talking about.  If no day is given, assume today.
        """
        if atDate is None:
            atDate = timezone.localdate(timezone=self.tz)
        return getLocalTime(atDate, self.time_from, self.tz)

    def _futureExceptions(self, request):
        """
        Returns all future extra info, cancellations and postponements created
        for this recurring event
        """
        retval = []
        # We know all future exception dates are in the parent time zone
        myToday = timezone.localdate(timezone=self.tz)

        for extraInfo in ExtraInfoPage.events(request).child_of(self)         \
                                      .filter(except_date__gte=myToday):
            retval.append(extraInfo)
        for cancellation in CancellationPage.events(request).child_of(self)   \
                                            .filter(except_date__gte=myToday):
            postponement = getattr(cancellation, "postponementpage", None)
            if postponement:
                retval.append(postponement)
            else:
                retval.append(cancellation)
        retval.sort(key=attrgetter('except_date'))
        # notice these are events not ThisEvents
        return retval

    def _nextOn(self, request):
        """
        Formatted date/time of when this event (including any postponements)
        will next be on
        """
        retval = None
        nextDt, event = self.__localAfterOrPostponedTo(timezone.localtime(),
                                                       dt.time.min)
        if nextDt is not None:
            timeFrom = nextDt.time() if event.time_from is not None else None
            retval = "{} {}".format(dateFormat(nextDt.date()),
                                    timeFormat(timeFrom, prefix=gettext("at ")))
            if event is not self and event.isAuthorized(request):
                retval = format_html('<a class="inline-link" href="{}">{}</a>',
                                     event.url, retval)
        return retval

    def _occursOn(self, myDate):
        """
        Returns true iff an occurence of this event starts on this date
        (given in the event's own timezone).

        (Does not include postponements, but does exclude cancellations.)
        """
        if myDate not in self.repeat:
            return False
        if CancellationPage.events.child_of(self)                            \
                           .filter(except_date=myDate).exists():
            return False
        return True

    def _getMyFirstDatetimeFrom(self):
        """
        The datetime this event first started, or None if it never did.
        """
        myStartDt = getAwareDatetime(self.repeat.dtstart, None,
                                     self.tz, dt.time.min)
        return self.__after(myStartDt, excludeCancellations=False)

    def _getMyFirstDatetimeTo(self):
        """
        The datetime this event first finished, or None if it never did.
        """
        myFirstDt = self._getMyFirstDatetimeFrom()
        if myFirstDt is not None:
            daysDelta = dt.timedelta(days=self.num_days - 1)
            return getAwareDatetime(myFirstDt.date() + daysDelta,
                                    self.time_to,
                                    self.tz, dt.time.max)

    def _getMyNextDate(self):
        """
        Date when this event is next scheduled to occur in my time zone
        (Does not include postponements, but does exclude cancellations)
        """
        myNow = timezone.localtime(timezone=self.tz)
        nextDt = self.__after(myNow)
        if nextDt is not None:
            return nextDt.date()

    def __getMyFromDt(self):
        """
        Get the datetime of the next event after or before now in my timezone.
        """
        myNow = timezone.localtime(timezone=self.tz)
        return self.__after(myNow) or self.__before(myNow)

    def __localAfterOrPostponedTo(self, fromDt, timeDefault=dt.time.min):
        myFromDt, event = self.__afterOrPostponedTo(fromDt.astimezone(self.tz))
        if myFromDt is not None:
            localFromDt = getLocalDatetime(myFromDt.date(), event.time_from,
                                           self.tz, timeDefault)
            return (localFromDt, event)
        else:
            return (None, event)

    def __afterOrPostponedTo(self, fromDt):
        after = self.__after(fromDt)
        # We know all postponement exception dates are in the parent time zone
        if after:
            # is there a postponed event before that?
            # nb: range is inclusive
            dateRange = (fromDt.date(), after.date())
            postponements = PostponementPage.events.child_of(self)           \
                                     .filter(date__range=(dateRange))        \
                                     .order_by('date', 'time_from')
            for postponement in postponements:
                postDt = getAwareDatetime(postponement.date,
                                          postponement.time_from,
                                          self.tz, dt.time.min)
                postDtMax = getAwareDatetime(postponement.date,
                                             postponement.time_from,
                                             self.tz, dt.time.max)
                if postDt < after and postDtMax >= fromDt:
                    return (postDt, postponement)
        else:
            # is there a postponed event then?
            postponements = PostponementPage.events.child_of(self)           \
                                     .filter(date__gte=fromDt.date())        \
                                     .order_by('date', 'time_from')
            for postponement in postponements:
                postDt = getAwareDatetime(postponement.date,
                                          postponement.time_from,
                                          self.tz, dt.time.min)
                postDtMax = getAwareDatetime(postponement.date,
                                             postponement.time_from,
                                             self.tz, dt.time.max)
                if postDtMax >= fromDt:
                    return (postDt, postponement)

        if after is not None:
            return (after, self)
        else:
            return (None, None)

    def __localAfter(self, fromDt, timeDefault=dt.time.min, **kwargs):
        myFromDt = self.__after(fromDt.astimezone(self.tz), **kwargs)
        if myFromDt is not None:
            return getLocalDatetime(myFromDt.date(), self.time_from,
                                    self.tz, timeDefault)

    def __after(self, fromDt, excludeCancellations=True, excludeExtraInfo=False):
        fromDate = fromDt.date()
        if self.time_from and self.time_from < fromDt.time():
            fromDate += _1day
        exceptions = set()
        if excludeCancellations:
            for cancelled in CancellationPage.events.child_of(self)          \
                                     .filter(except_date__gte=fromDate):
                exceptions.add(cancelled.except_date)
        if excludeExtraInfo:
            for info in ExtraInfoPage.events.child_of(self)                  \
                                     .filter(except_date__gte=fromDate)      \
                                     .exclude(extra_title=""):
                exceptions.add(info.except_date)
        for occurence in self.repeat.xafter(fromDate, inc=True):
            if occurence not in exceptions:
                return getAwareDatetime(occurence, self.time_from,
                                        self.tz, dt.time.min)

    def __localBefore(self, fromDt, timeDefault=dt.time.min, **kwargs):
        myFromDt = self.__before(fromDt.astimezone(self.tz), **kwargs)
        if myFromDt is not None:
            return getLocalDatetime(myFromDt.date(), self.time_from,
                                    self.tz, timeDefault)

    def __before(self, fromDt, excludeCancellations=True, excludeExtraInfo=False):
        fromDate = fromDt.date()
        if self.time_from and self.time_from > fromDt.time():
            fromDate -= _1day
        exceptions = set()
        if excludeCancellations:
            for cancelled in CancellationPage.events.child_of(self)          \
                                     .filter(except_date__lte=fromDate):
                exceptions.add(cancelled.except_date)
        if excludeExtraInfo:
            for info in ExtraInfoPage.events.child_of(self)                  \
                                     .filter(except_date__lte=fromDate)      \
                                     .exclude(extra_title=""):
                exceptions.add(info.except_date)
        last = None
        for occurence in self.repeat:
            if occurence > fromDate:
                break
            if occurence not in exceptions:
                last = occurence

        if last is not None:
            return getAwareDatetime(last, self.time_from, self.tz, dt.time.min)

# ------------------------------------------------------------------------------
class MultidayRecurringEventPage(ProxyPageMixin, RecurringEventPage):
    """
    A proxy of RecurringEventPage that exposes the hidden num_days field.
    """
    class Meta(ProxyPageMixin.Meta):
        verbose_name = _("multiday recurring event page")
        verbose_name_plural = _("multiday recurring event pages")

    subpage_types = ['joyous.ExtraInfoPage',
                     'joyous.CancellationPage',
                     'joyous.RescheduleMultidayEventPage']
    template = "joyous/recurring_event_page.html"

    content_panels = RecurringEventPage.content_panels0 + [
        FieldPanel('num_days'),
        ] + RecurringEventPage.content_panels1

# ------------------------------------------------------------------------------
class EventExceptionQuerySet(EventQuerySet):
    def current(self):
        qs = super().current()
        return qs.filter(except_date__gte = todayUtc() - _1day)

    def future(self):
        qs = super().future()
        return qs.filter(except_date__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(except_date__lte = todayUtc() + _1day)

class EventExceptionPageForm(WagtailAdminPageForm):
    def _checkSlugAvailable(self, cleaned_data, slugName=None):
        if slugName is None:
            slugName = self.instance.slugName
        description = getattr(self, 'description', "a {}".format(slugName))
        exceptDate = cleaned_data.get('except_date', "invalid")
        slug = "{}-{}".format(exceptDate, slugName)
        if not Page._slug_is_available(slug, self.parent_page, self.instance):
            self.add_error('except_date',
                           _("That date already has") + " " + description.lower())

class EventExceptionBase(models.Model):
    class Meta:
        abstract = True

    events = EventManager.from_queryset(EventExceptionQuerySet)()

    # overrides is also the parent, but parent is not set until the
    # child is saved and added.  (NB: is published version of parent)
    overrides = models.ForeignKey('joyous.RecurringEventPage',
                                  null=True, blank=False,
                                  related_name='+',
                                  verbose_name=_("overrides"),
                                  # can't set to CASCADE, so go with SET_NULL
                                  on_delete=models.SET_NULL)
    overrides.help_text = _("The recurring event that we are updating.")
    except_date = models.DateField(_("For Date"))
    except_date.help_text = _("For this date")

    # Original properties
    num_days    = property(attrgetter("overrides.num_days"))
    time_from   = property(attrgetter("overrides.time_from"))
    time_to     = property(attrgetter("overrides.time_to"))
    tz          = property(attrgetter("overrides.tz"))
    group       = property(attrgetter("overrides.group"))
    category    = property(attrgetter("overrides.category"))
    image       = property(attrgetter("overrides.image"))
    location    = property(attrgetter("overrides.location"))
    website     = property(attrgetter("overrides.website"))

    @property
    def overrides_repeat(self):
        """
        The recurrence rule of the event being overridden.
        """
        return getattr(self.overrides, 'repeat', None)

    @property
    def local_title(self):
        """
        Localised version of the human-readable title of the page.
        """
        name = self.title.partition(" for ")[0]
        exceptDate = getLocalDate(self.except_date, self.time_from, self.tz)
        title = _("{exception} for {date}").format(exception=_(name),
                                                   date=dateFormat(exceptDate))
        return title

    @property
    def when(self):
        """
        A string describing when the event occurs (in the local time zone).
        """
        return self._getLocalWhen(self.except_date, self.num_days)

    @property
    def at(self):
        """
        A string describing what time the event starts (in the local time zone).
        """
        return timeFormat(self._getFromTime())

    def get_context(self, request, *args, **kwargs):
        retval = super().get_context(request, *args, **kwargs)
        retval['overrides'] = self.overrides
        retval['themeCSS'] = getattr(settings, "JOYOUS_THEME_CSS", "")
        return retval

    def _getLocalWhen(self, date_from, num_days=1):
        """
        Returns a string describing when the event occurs (in the local time zone).
        """
        dateFrom, timeFrom = getLocalDateAndTime(date_from, self.time_from,
                                                 self.tz, dt.time.min)
        if num_days > 1 or self.time_to is not None:
            daysDelta = dt.timedelta(days=self.num_days - 1)
            dateTo, timeTo = getLocalDateAndTime(date_from + daysDelta,
                                                 self.time_to, self.tz)
        else:
            dateTo = dateFrom
            timeTo = None

        if dateFrom == dateTo:
            retval = _("{date} {atTime}").format(
                    date=dateFormat(dateFrom),
                    atTime=timeFormat(timeFrom, timeTo, gettext("at ")))
        else:
            # Friday the 10th of April for 3 days at 1pm to 10am
            localNumDays = (dateTo - dateFrom).days + 1
            retval = _("{date} for {n} days {startTime}").format(
                    date=dateFormat(dateFrom),
                    n=localNumDays,
                    startTime=timeFormat(timeFrom, prefix=gettext("starting at ")))
            retval = _("{dateAndStartTime} {finishTime}").format(
                    dateAndStartTime=retval.strip(),
                    finishTime=timeFormat(timeTo, prefix=gettext("finishing at ")))
        return retval.strip()

    def _getFromTime(self, atDate=None):
        """
        Time that the event starts (in the local time zone).
        """
        return getLocalTime(self.except_date, self.time_from, self.tz)

    def _getFromDt(self):
        """
        Datetime that the event starts (in the local time zone).
        """
        return getLocalDatetime(self.except_date, self.time_from, self.tz)

    def _getToDt(self):
        """
        Datetime that the event ends (in the local time zone).
        """
        return getLocalDatetime(self.except_date, self.time_to, self.tz)

    def full_clean(self, *args, **kwargs):
        """
        Apply fixups that need to happen before per-field validation occurs.
        Sets the page's title.
        """
        name = self.slugName.title()
        # generate the title and slug in English
        # the translation of the title will happen in the property local_title
        with translation.override("en"):
            self.title = "{} for {}".format(name, dateFormat(self.except_date))
            self.slug = "{}-{}".format(self.except_date, self.slugName)
        super().full_clean(*args, **kwargs)

    def isAuthorized(self, request):
        """
        Is the user authorized for the requested action with this event?
        """
        restrictions = self.get_view_restrictions()
        if restrictions and request is None:
            return False
        else:
            return all(restriction.accept_request(request)
                       for restriction in restrictions)

    def _copyFieldsFromParent(self, parent):
        """
        Copy across field values from the recurring event parent.
        """
        self.overrides = parent
        self.except_date = parent._getMyNextDate()

# ------------------------------------------------------------------------------
class ExtraInfoQuerySet(EventExceptionQuerySet):
    def this(self):
        request = self.request
        class ThisExtraInfoIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.extra_title, page,
                                    page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisExtraInfoIterable
        return qs

class ExtraInfoPageForm(EventExceptionPageForm):
    description = _("Extra Information")

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        return cleaned_data

class ExtraInfoPage(EventExceptionBase, Page):
    class Meta:
        verbose_name = _("extra event information")
        verbose_name_plural = _("extra event information")
        default_manager_name = "objects"

    events = EventManager.from_queryset(ExtraInfoQuerySet)()
    parent_page_types = ["joyous.RecurringEventPage",
                         "joyous.MultidayRecurringEventPage"]
    subpage_types = []
    base_form_class = ExtraInfoPageForm
    slugName    = "extra-info"
    gettext_noop("Extra-Info")

    extra_title = models.CharField(_("title"), max_length=255, blank=True)
    extra_title.help_text = _("A more specific title for this occurence (optional)")
    extra_information = RichTextField(_("extra information"), blank=True)
    extra_information.help_text = _("Information just for this date")

    search_fields = Page.search_fields + [
        index.SearchField('extra_title'),
        index.SearchField('extra_information'),
    ]
    # Note title is not displayed
    content_panels = [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('except_date'),
        FieldPanel('extra_title', classname="full title"),
        FieldPanel('extra_information', classname="full"),
        ]
    promote_panels = []

    # Original properties
    details     = property(attrgetter("overrides.details"))

    @property
    def status(self):
        """
        The current status of the event (started, finished or pending).
        """
        myNow = timezone.localtime(timezone=self.tz)
        fromDt = getAwareDatetime(self.except_date, self.time_from, self.tz)
        daysDelta = dt.timedelta(days=self.num_days - 1)
        toDt = getAwareDatetime(self.except_date + daysDelta, self.time_to, self.tz)
        if toDt < myNow:
            return "finished"
        elif fromDt < myNow:
            return "started"

    @property
    def status_text(self):
        """
        A text description of the current status of the event.
        """
        status = self.status
        if status == "finished":
            return _("This event has finished.")
        elif status == "started":
            return _("This event has started.")
        else:
            return ""

    @property
    def _current_datetime_from(self):
        """
        The datetime this event will start or did start in the local timezone, or
        None if it is finished.
        """
        # _occursOn means a lookup of CancellationPage
        # possible performance problem?
        if not self.overrides._occursOn(self.except_date):
            return None
        fromDt = self._getFromDt()
        toDt = self._getToDt()
        return fromDt if toDt >= timezone.localtime() else None

    @property
    def _future_datetime_from(self):
        """
        The datetime this event next starts in the local timezone, or None if
        in the past.
        """
        # possible performance problem?
        if not self.overrides._occursOn(self.except_date):
            return None
        fromDt = self._getFromDt()
        return fromDt if fromDt >= timezone.localtime() else None

    @property
    def _past_datetime_from(self):
        """
        The datetime this event previously started in the local timezone, or
        None if it never did.
        """
        # possible performance problem?
        if not self.overrides._occursOn(self.except_date):
            return None
        fromDt = self._getFromDt()
        return fromDt if fromDt < timezone.localtime() else None

# ------------------------------------------------------------------------------
class CancellationQuerySet(EventExceptionQuerySet):
    def this(self):
        request = self.request
        class ThisCancellationIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.cancellation_title, page,
                                    page.getCancellationUrl(request))
        qs = self._clone()
        qs._iterable_class = ThisCancellationIterable
        return qs

class CancellationPageForm(EventExceptionPageForm):
    description = _("a cancellation")

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        self._checkSlugAvailable(cleaned_data, "postponement")
        return cleaned_data

class CancellationPage(EventExceptionBase, Page):
    class Meta:
        verbose_name = _("cancellation")
        verbose_name_plural = _("cancellations")
        default_manager_name = "objects"

    events = EventManager.from_queryset(CancellationQuerySet)()
    parent_page_types = ["joyous.RecurringEventPage",
                         "joyous.MultidayRecurringEventPage"]
    subpage_types = []
    base_form_class = CancellationPageForm
    slugName = "cancellation"
    gettext_noop("Cancellation")

    cancellation_title = models.CharField(_("title"), max_length=255, blank=True)
    cancellation_title.help_text = _("Show in place of cancelled event "
                                     "(Leave empty to show nothing)")
    cancellation_details = RichTextField(_("details"), blank=True)
    cancellation_details.help_text = _("Why was the event cancelled?")

    search_fields = Page.search_fields + [
        index.SearchField('cancellation_title'),
        index.SearchField('cancellation_details'),
    ]
    # Note title is not displayed
    content_panels = [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('except_date'),
        MultiFieldPanel([
            FieldPanel('cancellation_title', classname="full title"),
            FieldPanel('cancellation_details', classname="full")],
            heading=_("Cancellation")),
        ]
    promote_panels = []

    @property
    def status(self):
        """
        The current status of the event (started, finished or pending).
        """
        return "cancelled"

    @property
    def status_text(self):
        """
        A text description of the current status of the event.
        """
        return _("This event has been cancelled.")

    @property
    def _current_datetime_from(self):
        """
        The datetime the event that was cancelled would start in the local
        timezone, or None if it would have finished by now.
        """
        if self.except_date not in self.overrides.repeat:
            return None
        fromDt = self._getFromDt()
        toDt = self._getToDt()
        return fromDt if toDt >= timezone.localtime() else None

    @property
    def _future_datetime_from(self):
        """
        The datetime the event that was cancelled would start in the local
        timezone, or None if that is in the past.
        """
        if self.except_date not in self.overrides.repeat:
            return None
        fromDt = self._getFromDt()
        return fromDt if fromDt >= timezone.localtime() else None

    @property
    def _past_datetime_from(self):
        """
        The datetime of the event that was cancelled in the local timezone, or
        None if it never would have.
        """
        if self.except_date not in self.overrides.repeat:
            return None
        fromDt = self._getFromDt()
        return fromDt if fromDt < timezone.localtime() else None

    def getCancellationUrl(self, request=None):
        """
        The URL to a page describing the cancellation for Postponements and
        plain Cancellations.
        """
        url = self.get_url(request)
        if hasattr(self, "postponementpage"):
            if url[-1] != '/':
                url += "/from"
            else:
                url += "from/"
        return url

    cancellation_url = property(getCancellationUrl)

# ------------------------------------------------------------------------------
class PostponementQuerySet(EventQuerySet):
    def current(self):
        qs = super().current()
        return qs.filter(date__gte = todayUtc() - _1day)

    def future(self):
        qs = super().future()
        return qs.filter(date__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(date__lte = todayUtc() + _1day)

    def this(self):
        request = self.request
        class ThisPostponementIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.postponement_title,
                                    page, page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisPostponementIterable
        return qs

    def byDay(self, fromDate, toDate):
        request = self.request
        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = EventsByDayList(fromDate, toDate)
                for page in super().__iter__():
                    thisEvent = ThisEvent(page.postponement_title,
                                          page, page.get_url(request))
                    pageFromDate = getLocalDate(page.date,
                                                page.time_from, page.tz)
                    daysDelta = dt.timedelta(days=page.num_days - 1)
                    pageToDate = getLocalDate(page.date + daysDelta,
                                              page.time_to, page.tz)
                    evods.add(thisEvent, pageFromDate, pageToDate)
                yield from evods

        qs = self._clone()
        qs._iterable_class = ByDayIterable
        return qs.filter(date__range=(fromDate - _1day, toDate + _1day))

class PostponementPageForm(EventExceptionPageForm):
    description = _("a postponement")

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        self._checkSlugAvailable(cleaned_data, "cancellation")
        self._checkStartBeforeEnd(cleaned_data)
        return cleaned_data

    def _checkStartBeforeEnd(self, cleaned_data):
        numDays   = cleaned_data.get('num_days', 1)
        startTime = getTimeFrom(cleaned_data.get('time_from'))
        endTime   = getTimeTo(cleaned_data.get('time_to'))
        if numDays == 1 and startTime > endTime:
            self.add_error('time_to', _("Event cannot end before it starts"))

class RescheduleEventBase(EventBase):
    """
    This class exists just so that the class attributes defined here are
    picked up before the instance properties from EventExceptionBase,
    as well as before EventBase.
    """
    class Meta:
        abstract = True

    num_days = models.IntegerField(_("number of days"), default=1,
                                   validators=[MinValueValidator(1),
                                               MaxValueValidator(99)])
    # Original properties
    tz          = property(attrgetter("overrides.tz"))
    group       = property(attrgetter("overrides.group"))
    uid         = property(attrgetter("overrides.uid"))
    group_page  = None
    get_context = EventExceptionBase.get_context

class PostponementPage(RoutablePageMixin, RescheduleEventBase, CancellationPage):
    class Meta:
        verbose_name = _("postponement")
        verbose_name_plural = _("postponements")
        default_manager_name = "objects"

    events = EventManager.from_queryset(PostponementQuerySet)()
    parent_page_types = ["joyous.RecurringEventPage"]
    subpage_types = []
    base_form_class = PostponementPageForm
    slugName = "postponement"
    gettext_noop("Postponement")

    postponement_title = models.CharField(_("title"), max_length=255)
    postponement_title.help_text = _("The title for the postponed event")
    date = models.DateField(_("date"))

    search_fields = Page.search_fields + [
        index.SearchField('postponement_title'),
    ]

    cancellation_panel = MultiFieldPanel([
            FieldPanel('cancellation_title', classname="full title"),
            FieldPanel('cancellation_details', classname="full")],
            heading=_("Cancellation"))
    postponement_panel0 = [
            FieldPanel('postponement_title', classname="full title"),
            ImageChooserPanel('image'),
            FieldPanel('date')]
    postponement_panel1 = [
            TimePanel('time_from'),
            TimePanel('time_to'),
            FieldPanel('details', classname="full"),
            MapFieldPanel('location'),
            FieldPanel('website')]
    postponement_panel = MultiFieldPanel(
            postponement_panel0 + [HiddenNumDaysPanel()] + postponement_panel1,
            heading=_("Postponed to"))
    content_panels = [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('except_date'),
        cancellation_panel,
        postponement_panel,
    ]
    promote_panels = []

    @route(r"^from/$")
    def serveCancellation(self, request):
        return TemplateResponse(request,
                                "joyous/postponement_page_from.html",
                                self.get_context(request))

    @property
    def status(self):
        """
        The current status of the postponement (started, finished or pending).
        """
        myNow = timezone.localtime(timezone=self.tz)
        fromDt = getAwareDatetime(self.date, self.time_from, self.tz)
        daysDelta = dt.timedelta(days=self.num_days - 1)
        toDt = getAwareDatetime(self.date + daysDelta, self.time_to, self.tz)
        if toDt < myNow:
            return "finished"
        elif fromDt < myNow:
            return "started"

    @property
    def when(self):
        """
        A string describing when the postponement occurs (in the local time zone).
        """
        return EventExceptionBase._getLocalWhen(self, self.date, self.num_days)

    @property
    def postponed_from_when(self):
        """
        A string describing when the event was postponed from (in the local time zone).
        """
        what = self.what
        if what:
            return _("{what} from {when}").format(what=what,
                                                  when=self.cancellationpage.when)

    @property
    def what(self):
        """
        May return a 'postponed' or 'rescheduled' string depending what
        the start and finish time of the event has been changed to.
        """
        originalFromDt = dt.datetime.combine(self.except_date,
                                             getTimeFrom(self.overrides.time_from))
        changedFromDt = dt.datetime.combine(self.date, getTimeFrom(self.time_from))
        originalDaysDelta = dt.timedelta(days=self.overrides.num_days - 1)
        originalToDt = dt.datetime.combine(self.except_date + originalDaysDelta,
                                           getTimeTo(self.overrides.time_to))
        changedDaysDelta = dt.timedelta(days=self.num_days - 1)
        changedToDt = dt.datetime.combine(self.except_date + changedDaysDelta,
                                          getTimeTo(self.time_to))
        if originalFromDt < changedFromDt:
            return _("Postponed")
        elif originalFromDt > changedFromDt or originalToDt != changedToDt:
            return _("Rescheduled")
        else:
            return None

    @property
    def postponed_from(self):
        """
        Date that the event was postponed from (in the local time zone).
        """
        fromDate = getLocalDate(self.except_date, self.time_from, self.tz)
        return dateFormat(fromDate)

    @property
    def postponed_to(self):
        """
        Date that the event was postponed to (in the local time zone).
        """
        toDate = getLocalDate(self.date, self.time_from, self.tz)
        return dateFormat(toDate)

    @property
    def at(self):
        """
        A string describing what time the postponement starts (in the local time zone).
        """
        return timeFormat(self._getFromTime())

    def _getFromTime(self, atDate=None):
        """
        Time that the postponement starts (in the local time zone).
        """
        return getLocalTime(self.date, self.time_from, self.tz)

    def _getFromDt(self):
        """
        Datetime that the postponement starts (in the local time zone).
        """
        return getLocalDatetime(self.date, self.time_from, self.tz)

    def _getToDt(self):
        """
        Datetime that the postponement ends (in the local time zone).
        """
        return getLocalDatetime(self.date, self.time_to, self.tz)

    def _copyFieldsFromParent(self, parent):
        """
        Copy across field values from the recurring event parent.
        """
        super()._copyFieldsFromParent(parent)
        parentFields = set()
        for panel in parent.content_panels:
            parentFields.update(panel.required_fields())
        pageFields = set()
        for panel in self.content_panels:
            pageFields.update(panel.required_fields())
        commonFields = parentFields & pageFields
        for name in commonFields:
            setattr(self, name, getattr(parent, name))
        if self.except_date:
            self.date = self.except_date + dt.timedelta(days=1)
        self.postponement_title = parent.title

# ------------------------------------------------------------------------------
class RescheduleMultidayEventPage(ProxyPageMixin, PostponementPage):
    """
    A proxy of PostponementPage that exposes the hidden num_days field.
    """
    class Meta(ProxyPageMixin.Meta):
        verbose_name = _("postponement")
        verbose_name_plural = _("postponements")

    parent_page_types = ["joyous.MultidayRecurringEventPage"]
    template = "joyous/postponement_page.html"

    postponement_panel = MultiFieldPanel(
            PostponementPage.postponement_panel0 +
            [FieldPanel('num_days')] +
            PostponementPage.postponement_panel1,
            heading=_("Postponed to"))
    content_panels = [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('except_date'),
        PostponementPage.cancellation_panel,
        postponement_panel,
    ]

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
