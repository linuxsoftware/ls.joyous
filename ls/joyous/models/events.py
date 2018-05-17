# ------------------------------------------------------------------------------
# Joyous events models
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from collections import namedtuple
from functools import partial
from itertools import chain, groupby
from operator import attrgetter
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.query import ModelIterable
from django.utils.html import format_html
from django.utils import timezone
from timezone_field import TimeZoneField
from wagtail.core.query import PageQuerySet
from wagtail.core.models import Page, PageManager, PageViewRestriction
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import (FieldPanel, MultiFieldPanel,
        PageChooserPanel)
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images import get_image_model_string
from wagtail.search import index
from wagtail.admin.forms import WagtailAdminPageForm
from ..holidays.parser import parseHolidays
from ..utils.telltime import (getAwareDatetime, getLocalDatetime,
        getLocalDateAndTime, getLocalDate, getLocalTime, todayUtc)
from ..utils.telltime import timeFrom, timeTo
from ..utils.telltime import timeFormat, dateFormat
from ..utils.weeks import week_of_month
from ..recurrence import RecurrenceField
from ..recurrence import ExceptionDatePanel
from ..widgets import TimeInput
from .groups import get_group_model_string, get_group_model

try:
    # Use wagtailgmaps for location if it is installed
    # but don't depend upon it
    settings.INSTALLED_APPS.index('wagtailgmaps')
    from wagtailgmaps.edit_handlers import MapFieldPanel
except (ValueError, ImportError):
    MapFieldPanel = FieldPanel

# ------------------------------------------------------------------------------
# API get functions
# ------------------------------------------------------------------------------
def getAllEventsByDay(request, fromDate, toDate):
    simpleEvents    = SimpleEventPage.events(request).byDay(fromDate, toDate)
    multidayEvents  = MultidayEventPage.events(request).byDay(fromDate, toDate)
    recurringEvents = RecurringEventPage.events(request).byDay(fromDate, toDate)
    postponedEvents = PostponementPage.events(request).byDay(fromDate, toDate)
    evods = _getEventsByDay(fromDate, (simpleEvents, multidayEvents,
                                       recurringEvents, postponedEvents))
    return evods

def getAllEventsByWeek(request, year, month):
    return _getEventsByWeek(year, month, partial(getAllEventsByDay, request))

def getAllUpcomingEvents(request, home=None):
    qrys = [SimpleEventPage.events(request).upcoming().this(),
            MultidayEventPage.events(request).upcoming().this(),
            RecurringEventPage.events(request).upcoming().this(),
            PostponementPage.events(request).upcoming().this(),
            ExtraInfoPage.events(request).exclude(extra_title="").upcoming()
                                         .this()]
    if home is not None:
        qrys = [qry.descendant_of(home) for qry in qrys]
    events = sorted(chain.from_iterable(qrys),
                    key=attrgetter('page._upcoming_datetime_from'))
    return events

def getGroupUpcomingEvents(request, group):
    # Get events that are a child of a group page, or a postponement or extra
    # info a child of the recurring event child of the group (using descendant_of)
    qrys = [SimpleEventPage.events(request).upcoming().child_of(group).this(),
            MultidayEventPage.events(request).upcoming().child_of(group).this(),
            RecurringEventPage.events(request).upcoming().child_of(group).this(),
            PostponementPage.events(request).upcoming()
                                         .descendant_of(group).this(),
            ExtraInfoPage.events(request).exclude(extra_title="").upcoming()
                                         .descendant_of(group).this()]

    # Get events that are linked to a group page, or a postponement or extra
    # info a child of the recurring event linked to a group (the long way)
    rrEvents = group.recurringeventpage_set(manager='events').auth(request).this()
    qrys += [group.simpleeventpage_set(manager='events').auth(request).this(),
             group.multidayeventpage_set(manager='events').auth(request).this(),
             rrEvents]
    for rrEvent in rrEvents:
        qrys += [PostponementPage.events(request).child_of(rrEvent.page).this(),
                 ExtraInfoPage.events(request).exclude(extra_title="")
                                              .child_of(rrEvent.page).this()]
    events = sorted(chain.from_iterable(qrys),
                    key=attrgetter('page._upcoming_datetime_from'))
    return events

def getAllPastEvents(request, home=None):
    qrys = [SimpleEventPage.events(request).past().this(),
            MultidayEventPage.events(request).past().this(),
            RecurringEventPage.events(request).past().this(),
            PostponementPage.events(request).past().this(),
            ExtraInfoPage.events(request).exclude(extra_title="").past().this()]
    if home is not None:
        qrys = [qry.descendant_of(home) for qry in qrys]
    events = sorted(chain.from_iterable(qrys),
                    key=attrgetter('page._past_datetime_from'), reverse=True)
    return events

# def getAllEvents(request, home=None):
#     qrys = [SimpleEventPage.events(request).all(),
#             MultidayEventPage.events(request).all(),
#             RecurringEventPage.events(request).all(),
#             PostponementPage.events(request).all(),
#             ExtraInfoPage.events(request).upcoming().this()]
#     if home is not None:
#         qrys = [qry.descendant_of(home) for qry in qrys]
#     events = sorted(chain.from_iterable(qrys), key=attrgetter('page._upcoming_datetime_from'))
#     return events

# ------------------------------------------------------------------------------
# Private
# ------------------------------------------------------------------------------
def _getEventsByDay(date_from, eventsByDaySrcs):
    evods = []
    day = date_from
    for srcs in zip(*eventsByDaySrcs):
        days_events       = []
        continuing_events = []
        for src in srcs:
            days_events += src.days_events
            continuing_events += src.continuing_events
        def sortByTime(thisEvent):
            fromTime = thisEvent.page._getFromTime()
            if fromTime is None:
                fromTime = dt.time.max
            return fromTime
        days_events.sort(key=sortByTime)
        evods.append(EventsOnDay(day, days_events, continuing_events))
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

# ------------------------------------------------------------------------------
# Helper types and constants
# ------------------------------------------------------------------------------
ThisEvent = namedtuple("ThisEvent", "title page")

class EventsOnDay(namedtuple("EODBase", "date days_events continuing_events")):
    holidays = parseHolidays(getattr(settings, "JOYOUS_HOLIDAYS", ""))

    @property
    def all_events(self):
        return self.days_events + self.continuing_events

    @property
    def preview(self):
        return ", ".join(event.title for event in self.all_events)[:100]

    @property
    def weekday(self):
        return calendar.day_abbr[self.date.weekday()].lower()

    @property
    def holiday(self):
        return self.holidays.get(self.date)

_1day = dt.timedelta(days=1)

# ------------------------------------------------------------------------------
# Event models
# ------------------------------------------------------------------------------
class EventCategory(models.Model):
    class Meta:
        ordering = ["name"]
        verbose_name = "Event Category"
        verbose_name_plural = "Event Categories"

    code = models.CharField(max_length=4, unique=True)
    name = models.CharField(max_length=80)

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

    def upcoming(self):
        qs = self._chain()
        qs.postFilter = self.__predicateBasedOn('_upcoming_datetime_from')
        return qs

    def past(self):
        qs = self._chain()
        qs.postFilter = self.__predicateBasedOn('_past_datetime_from')
        return qs

    def __predicateBasedOn(self, attribute):
        def predicate(item):
            for event in getattr(item, 'days_events', [item]):
                page = getattr(event, 'page', event)
                if not getattr(page, attribute, False):
                    return False
            return True
        return predicate

    def this(self):
        class ThisEventIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.title, page)
        qs = self._chain()
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
        q = Q()
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
        startTime = timeFrom(cleaned_data.get('time_from'))
        endTime   = timeTo(cleaned_data.get('time_to'))
        if startTime > endTime:
            self.add_error('time_to', "Event cannot end before it starts")

def _get_default_timezone():
    return timezone.get_default_timezone()

class EventBase(models.Model):
    class Meta:
        abstract = True

    category = models.ForeignKey(EventCategory,
                                 related_name="+",
                                 verbose_name="Category",
                                 on_delete=models.SET_NULL,
                                 blank=True, null=True)
    image = models.ForeignKey(get_image_model_string(),
                              null=True, blank=True,
                              on_delete=models.SET_NULL,
                              related_name='+')

    time_from = models.TimeField("Start time", null=True, blank=True)
    time_to = models.TimeField("End time", null=True, blank=True)
    # No you can't set different timezones for time_from and time_to
    tz = TimeZoneField(verbose_name="Time zone",
                       default=_get_default_timezone)

    group_page  = models.ForeignKey(get_group_model_string(),
                                    null=True, blank=True,
                                    on_delete=models.SET_NULL)
    details  = RichTextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    website = models.URLField(blank=True)

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

    # adding the event as a child of a group automatically assigns the event to
    # that group.
    @property
    def group(self):
        retval = None
        parent = self.get_parent()
        Group = get_group_model()
        if issubclass(parent.specific_class, Group):
            retval = parent.specific
        if retval is None:
            retval = self.group_page
        return retval

    @property
    def _upcoming_datetime_from(self):
        fromDt = self._getFromDt()
        return fromDt if fromDt >= timezone.localtime() else None

    @property
    def _past_datetime_from(self):
        fromDt = self._getFromDt()
        return fromDt if fromDt < timezone.localtime() else None

    @property
    def status(self):
        raise NotImplementedError()

    @property
    def status_text(self):
        status = self.status
        if status == "finished":
            return "This event has finished."
        elif status == "started":
            return "This event has started."
        else:
            return ""

    @classmethod
    def _removeContentPanels(cls, remove):
        if type(remove) is str:
            remove = [remove]
        cls.content_panels = [panel for panel in cls.content_panels
                              if getattr(panel, "field_name", None) not in remove]

    def isAuthorized(self, request):
        return all(restriction.accept_request(request)
                   for restriction in self.get_view_restrictions())

    def _getLocalWhen(self, date_from, date_to=None):
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
            retval = "{} {}".format(dateFormat(dateFrom),
                                    timeFormat(timeFrom, timeTo, "at "))
        else:
            retval = "{} {}".format(dateFormat(dateFrom),
                                    timeFormat(timeFrom, prefix="at "))
            retval = "{} to {} {}".format(retval.strip(),
                                          dateFormat(dateTo),
                                          timeFormat(timeTo, prefix="at "))
        return retval.strip()

    def _getFromTime(self):
        raise NotImplementedError()

    def _getFromDt(self):
        raise NotImplementedError()

def removeContentPanels(remove):
    SimpleEventPage._removeContentPanels(remove)
    MultidayEventPage._removeContentPanels(remove)
    RecurringEventPage._removeContentPanels(remove)
    PostponementPage._removeContentPanels(remove)

# ------------------------------------------------------------------------------
class SimpleEventQuerySet(EventQuerySet):
    def upcoming(self):
        qs = super().upcoming()
        return qs.filter(date__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(date__lte = todayUtc() + _1day)

    def byDay(self, fromDate, toDate):
        fromOrd = fromDate.toordinal()
        toOrd   = toDate.toordinal()
        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = [EventsOnDay(dt.date.fromordinal(ord), [], [])
                         for ord in range(fromOrd, toOrd+1)]
                for page in super().__iter__():
                    pageFromDate = getLocalDate(page.date,
                                                page.time_from, page.tz)
                    pageToDate   = getLocalDate(page.date,
                                                page.time_to, page.tz)
                    dayNum = pageFromDate.toordinal() - fromOrd
                    thisEvent = ThisEvent(page.title, page)
                    if 0 <= dayNum <= toOrd - fromOrd:
                        evods[dayNum].days_events.append(thisEvent)
                    if pageFromDate != pageToDate:
                        if 0 <= dayNum+1 <= toOrd - fromOrd:
                            evods[dayNum+1].continuing_events.append(thisEvent)
                for evod in evods:
                    yield evod
        qs = self._chain()
        qs._iterable_class = ByDayIterable
        return qs.filter(date__range=(fromDate - _1day, toDate + _1day))

class SimpleEventPage(Page, EventBase):
    events = EventManager.from_queryset(SimpleEventQuerySet)()

    class Meta:
        verbose_name = "Event Page"
        default_manager_name = "objects"

    parent_page_types = ["joyous.CalendarPage",
                         get_group_model_string()]
    subpage_types = []
    base_form_class = EventPageForm

    date    = models.DateField("Date", default=dt.date.today)

    content_panels = Page.content_panels + [
        FieldPanel('category'),
        ImageChooserPanel('image'),
        FieldPanel('date'),
        FieldPanel('time_from', widget=TimeInput),
        FieldPanel('time_to', widget=TimeInput),
        FieldPanel('tz'),
        ] + EventBase.content_panels1

    @property
    def status(self):
        myNow = timezone.localtime(timezone=self.tz)
        if getAwareDatetime(self.date, self.time_to, self.tz) < myNow:
            return "finished"
        elif getAwareDatetime(self.date, self.time_from, self.tz) < myNow:
            return "started"
        return None

    @property
    def when(self):
        return self._getLocalWhen(self.date)

    @property
    def at(self):
        return timeFormat(self._getFromTime())

    def _getFromTime(self):
        return getLocalTime(self.date, self.time_from, self.tz)

    def _getFromDt(self):
        return getLocalDatetime(self.date, self.time_from, self.tz)

# ------------------------------------------------------------------------------
class MultidayEventQuerySet(EventQuerySet):
    def upcoming(self):
        qs = super().upcoming()
        return qs.filter(date_from__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(date_from__lte = todayUtc() + _1day)

    def byDay(self, fromDate, toDate):
        fromOrd =  fromDate.toordinal()
        toOrd   =  toDate.toordinal()
        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = []
                days = [dt.date.fromordinal(ord)
                        for ord in range(fromOrd, toOrd+1)]
                for day in days:
                    days_events = []
                    continuing_events = []
                    for page in super().__iter__():
                        pageFromDate = getLocalDate(page.date_from,
                                                    page.time_from, page.tz)
                        pageToDate   = getLocalDate(page.date_to,
                                                    page.time_to, page.tz)
                        if pageFromDate == day:
                            days_events.append(ThisEvent(page.title, page))
                        elif pageFromDate < day <= pageToDate:
                            continuing_events.append(ThisEvent(page.title, page))
                    evods.append(EventsOnDay(day, days_events, continuing_events))
                for evod in evods:
                    yield evod
        qs = self._chain()
        qs._iterable_class = ByDayIterable
        return qs.filter(date_to__gte   = fromDate - _1day)   \
                 .filter(date_from__lte = toDate + _1day)

class MultidayEventPageForm(EventPageForm):
    def _checkStartBeforeEnd(self, cleaned_data):
        startDate = cleaned_data.get('date_from', dt.date.min)
        endDate   = cleaned_data.get('date_to', dt.date.max)
        if startDate > endDate:
            self.add_error('date_to', "Event cannot end before it starts")
        elif startDate == endDate:
            super()._checkStartBeforeEnd(cleaned_data)


class MultidayEventPage(Page, EventBase):
    events = EventManager.from_queryset(MultidayEventQuerySet)()

    class Meta:
        verbose_name = "Multiday Event Page"
        default_manager_name = "objects"

    parent_page_types = ["joyous.CalendarPage",
                         get_group_model_string()]
    subpage_types = []
    base_form_class = MultidayEventPageForm

    date_from = models.DateField("Start date", default=dt.date.today)
    date_to = models.DateField("End date", default=dt.date.today)

    content_panels = Page.content_panels + [
        FieldPanel('category'),
        ImageChooserPanel('image'),
        FieldPanel('date_from'),
        FieldPanel('time_from', widget=TimeInput),
        FieldPanel('date_to'),
        FieldPanel('time_to', widget=TimeInput),
        FieldPanel('tz'),
        ] + EventBase.content_panels1

    @property
    def status(self):
        myNow = timezone.localtime(timezone=self.tz)
        if getAwareDatetime(self.date_to, self.time_to, self.tz) < myNow:
            return "finished"
        elif getAwareDatetime(self.date_from, self.time_from, self.tz) < myNow:
            return "started"
        return None

    @property
    def when(self):
        return self._getLocalWhen(self.date_from, self.date_to)

    @property
    def at(self):
        return timeFormat(self._getFromTime())

    def _getFromTime(self):
        return getLocalTime(self.date_from, self.time_from, self.tz)

    def _getFromDt(self):
        return getLocalDatetime(self.date_from, self.time_from, self.tz)

# ------------------------------------------------------------------------------
class RecurringEventQuerySet(EventQuerySet):
    def byDay(self, fromDate, toDate):
        request = self.request
        fromOrd = fromDate.toordinal()
        toOrd   = toDate.toordinal()
        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = [EventsOnDay(dt.date.fromordinal(ord), [], [])
                         for ord in range(fromOrd, toOrd+1)]
                for page in super().__iter__():
                    exceptions = self.__getExceptionsFor(page)
                    for occurence in page.repeat.between(fromDate - _1day,
                                                         toDate + _1day, True):
                        thisEvent = None
                        exception = exceptions.get(occurence)
                        if exception:
                            if exception.title:
                                thisEvent = exception
                        else:
                            thisEvent = ThisEvent(page.title, page)
                        if thisEvent:
                            pageFromDate = getLocalDate(occurence,
                                                        page.time_from, page.tz)
                            pageToDate  = getLocalDate(occurence,
                                                       page.time_to, page.tz)
                            dayNum = pageFromDate.toordinal() - fromOrd
                            if 0 <= dayNum <= toOrd - fromOrd:
                                evods[dayNum].days_events.append(thisEvent)
                            if pageFromDate != pageToDate:
                                if 0 <= dayNum+1 <= toOrd - fromOrd:
                                    cont = evods[dayNum+1].continuing_events
                                    cont.append(thisEvent)
                for evod in evods:
                    yield evod

            def __getExceptionsFor(self, page):
                dateRange = (fromDate - _1day, toDate + _1day)
                exceptions = {}
                for extraInfo in ExtraInfoPage.events(request).child_of(page)\
                                     .filter(except_date__range=dateRange):
                    title = extraInfo.extra_title or page.title
                    exceptDate = extraInfo.except_date
                    exceptions[exceptDate] = ThisEvent(title, extraInfo)
                for cancellation in CancellationPage.events.child_of(page)   \
                                     .filter(except_date__range=dateRange):
                    if cancellation.isAuthorized(request):
                        title = cancellation.cancellation_title
                    else:
                        title = None
                    exceptDate = cancellation.except_date
                    exceptions[exceptDate] = ThisEvent(title, cancellation)
                return exceptions

        qs = self._chain()
        qs._iterable_class = ByDayIterable
        return qs

class RecurringEventPage(Page, EventBase):
    events = EventManager.from_queryset(RecurringEventQuerySet)()

    class Meta:
        verbose_name = "Recurring Event Page"
        default_manager_name = "objects"

    parent_page_types = ["joyous.CalendarPage",
                         get_group_model_string()]
    subpage_types = ['joyous.ExtraInfoPage',
                     'joyous.CancellationPage',
                     'joyous.PostponementPage']
    base_form_class = EventPageForm

    # FIXME So that Fred can't cancel Barney's event
    # owner_subpages_only = True

    repeat  = RecurrenceField()

    # TODO 
    # exclude_holidays = models.BooleanField(default=False)
    # exclude_holidays.help_text = "Cancel any occurence of this event on a public holiday"

    content_panels = Page.content_panels + [
        FieldPanel('category'),
        ImageChooserPanel('image'),
        FieldPanel('repeat'),
        FieldPanel('time_from', widget=TimeInput),
        FieldPanel('time_to', widget=TimeInput),
        FieldPanel('tz'),
        ] + EventBase.content_panels1

    @property
    def next_date(self):
        """
        Date when this event is next scheduled to occur
        (Does not include postponements, but does exclude cancellations)
        """
        nextDt = self.__localAfter(timezone.localtime(), dt.time.min)
        if nextDt is not None:
            return nextDt.date()
        else:
            return None

    @property
    def _upcoming_datetime_from(self):
        nextDt = self.__localAfter(timezone.localtime(), dt.time.max,
                                   excludeCancellations=True,
                                   excludeExtraInfo=True)
        return nextDt

    @property
    def prev_date(self):
        """
        Date when this event last occurred
        (Does not include postponements, but does exclude cancellations)
        """
        prevDt = self.__localBefore(timezone.localtime(), dt.time.min)
        if prevDt is not None:
            return prevDt.date()
        else:
            return None

    @property
    def _past_datetime_from(self):
        prevDt = self.__localBefore(timezone.localtime(), dt.time.max,
                                    excludeCancellations=True,
                                    excludeExtraInfo=True)
        return prevDt

    @property
    def status(self):
        myNow = timezone.localtime(timezone=self.tz)
        if self.repeat.until:
            untilDt = getAwareDatetime(self.repeat.until, self.time_to, self.tz)
            if untilDt < myNow:
                return "finished"
        todayStart = getAwareDatetime(myNow.date(), dt.time.min, self.tz)
        eventStart, event = self.__afterOrPostponedTo(todayStart)
        if eventStart is None:
            # the last occurences must have been cancelled
            return "finished"
        eventFinish = getAwareDatetime(eventStart.date(), event.time_to, self.tz)
        if (event.time_from is not None and
            eventStart < myNow < eventFinish):
            # if there are two occurences on the same day then we may miss
            # that one of them has started
            return "started"
        if (self.repeat.until and eventFinish < myNow and
            self.__afterOrPostponedTo(myNow)[0] is None):
            # only just wound up, the last occurence was earlier today
            return "finished"
        return None

    @property
    def status_text(self):
        status = self.status
        if status == "finished":
            return "These events have finished."
        else:
            return super().status_text

    @property
    def when(self):
        offset   = 0
        timeFrom = None
        timeTo   = None
        fromDt   = self.__after(timezone.localtime(timezone=self.tz))
        if fromDt is not None:
            offset = timezone.localtime(fromDt).toordinal() - fromDt.toordinal()
            if self.time_from is not None:
                timeFrom = getLocalTime(fromDt.date(), self.time_from, self.tz)
            if self.time_to is not None:
                timeTo = getLocalTime(fromDt.date(), self.time_to, self.tz)
        retval = "{} {}".format(self.repeat._getWhen(offset),
                                timeFormat(timeFrom, timeTo, "at "))
        return retval.strip()

    @property
    def at(self):
        return timeFormat(self._getFromTime())

    def _getFromTime(self):
        timeFrom = None
        fromDt   = self.__after(timezone.localtime(timezone=self.tz))
        if fromDt is not None:
            timeFrom = getLocalTime(fromDt.date(), self.time_from, self.tz)
        return timeFrom

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
            retval.append(ThisEvent(extraInfo.extra_title, extraInfo))
        for cancellation in CancellationPage.events(request).child_of(self)   \
                                            .filter(except_date__gte=myToday):
            postponement = getattr(cancellation, "postponementpage", None)
            if postponement:
                retval.append(ThisEvent(postponement.postponement_title,
                                        postponement))
            else:
                retval.append(ThisEvent(cancellation.cancellation_title,
                                        cancellation))
        retval.sort(key=attrgetter('page.except_date'))
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
                                    timeFormat(timeFrom, prefix="at "))
            if event is not self and event.isAuthorized(request):
                retval = format_html('<a class="inline-link" href="{}">{}</a>',
                                     event.url, retval)
        return retval

    def _occursOn(self, myDate):
        """
        Returns true iff this event occurs on this date (in event's own timezone)
        (Does not include postponements, but does exclude cancellations)
        """
        # TODO analyse which is faster (rrule or db) and test that first
        if myDate not in self.repeat:
            return False
        if CancellationPage.events.child_of(self)                            \
                           .filter(except_date=myDate).exists():
            return False
        return True

    def _getMyFirstDatetimeFrom(self):
        myStartDt = getAwareDatetime(self.repeat.dtstart, None,
                                     self.tz, dt.time.min)
        return self.__after(myStartDt)

    def _getMyFirstDatetimeTo(self):
        myFirstDt = self._getMyFirstDatetimeFrom()
        if myFirstDt is not None:
            return getAwareDatetime(myFirstDt.date(), self.time_to,
                                    self.tz, dt.time.max)
        else:
            return None

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
        else:
            return None

    def __after(self, fromDt, excludeCancellations=True, excludeExtraInfo=False):
        fromDate = fromDt.date()
        if self.time_from and self.time_from < fromDt.time():
            fromDate += dt.timedelta(days=1)
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
        return None

    def __localBefore(self, fromDt, timeDefault=dt.time.min, **kwargs):
        myFromDt = self.__before(fromDt.astimezone(self.tz), **kwargs)
        if myFromDt is not None:
            return getLocalDatetime(myFromDt.date(), self.time_from,
                                    self.tz, timeDefault)
        else:
            return None

    def __before(self, fromDt, excludeCancellations=True, excludeExtraInfo=False):
        fromDate = fromDt.date()
        if self.time_from and self.time_from > fromDt.time():
            fromDate -= dt.timedelta(days=1)
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
        else:
            return None

# TODO
# class MultidayReccuringEventPage(RecurringEventPage):

# ------------------------------------------------------------------------------
class EventExceptionQuerySet(EventQuerySet):
    def upcoming(self):
        qs = super().upcoming()
        return qs.filter(except_date__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(except_date__lte = todayUtc() + _1day)

class EventExceptionPageForm(WagtailAdminPageForm):
    def _checkSlugAvailable(self, cleaned_data, slugName=None):
        if slugName is None:
            slugName = self.slugName
        description = getattr(self, 'description', "a {}".format(slugName))
        exceptDate = cleaned_data.get('except_date', "invalid")
        slug = "{}-{}".format(exceptDate, slugName)
        if not Page._slug_is_available(slug, self.parent_page, self.instance):
            self.add_error('except_date',
                           'That date already has {}'.format(description))

    def save(self, commit=True):
        name = getattr(self, 'name', self.slugName.title())
        page = super().save(commit=False)
        page.title = "{} for {}".format(name, dateFormat(page.except_date))
        page.slug = "{}-{}".format(page.except_date, self.slugName)
        if commit:
            page.save()
        return page

class EventExceptionBase(models.Model):
    events = EventManager.from_queryset(EventExceptionQuerySet)()

    class Meta:
        abstract = True

    # overrides is also the parent, but parent is not set until the
    # child is saved and added.  (NB: is published version of parent)
    overrides = models.ForeignKey('joyous.RecurringEventPage',
                                  null=True, blank=False,
                                  # can't set to CASCADE, so go with SET_NULL
                                  on_delete=models.SET_NULL,
                                  related_name='+')
    overrides.help_text = "The recurring event that we are updating."
    except_date = models.DateField('For Date')
    except_date.help_text = "For this date"

    # Original properties
    time_from   = property(attrgetter("overrides.time_from"))
    time_to     = property(attrgetter("overrides.time_to"))
    tz          = property(attrgetter("overrides.tz"))
    group       = property(attrgetter("overrides.group"))

    @property
    def overrides_repeat(self):
        return getattr(self.overrides, 'repeat', None)

    @property
    def localTitle(self):
        # TODO localize for language too?
        name = self.title.partition(" for ")[0]
        exceptDate = getLocalDate(self.except_date, self.time_from, self.tz)
        title = "{} for {}".format(name, dateFormat(exceptDate))
        return title

    @property
    def when(self):
        return EventBase._getLocalWhen(self, self.except_date)

    @property
    def at(self):
        return timeFormat(self._getFromTime())

    def _getFromTime(self):
        return getLocalTime(self.except_date, self.time_from, self.tz)

# ------------------------------------------------------------------------------
class ExtraInfoQuerySet(EventExceptionQuerySet):
    def this(self):
        class ThisExtraInfoIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.extra_title, page)
        qs = self._chain()
        qs._iterable_class = ThisExtraInfoIterable
        return qs

class ExtraInfoPageForm(EventExceptionPageForm):
    name        = "Extra Information"
    description = name.lower()
    slugName    = "extra-info"

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        return cleaned_data

class ExtraInfoPage(Page, EventExceptionBase):
    events = EventManager.from_queryset(ExtraInfoQuerySet)()

    class Meta:
        verbose_name = "Extra Event Information"
        default_manager_name = "objects"

    parent_page_types = ["joyous.RecurringEventPage"]
    subpage_types = []
    base_form_class = ExtraInfoPageForm

    extra_title = models.CharField('Title', max_length=255, blank=True)
    extra_title.help_text = "A more specific title for this occurence (optional)"
    extra_information = RichTextField(blank=False)
    extra_information.help_text = "Information just for this date"

    # Note title is not displayed
    content_panels = [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('except_date'),
        FieldPanel('extra_title', classname="full title"),
        FieldPanel('extra_information', classname="full"),
        ]
    promote_panels = []

    # Original properties
    category    = property(attrgetter("overrides.category"))
    image       = property(attrgetter("overrides.image"))
    location    = property(attrgetter("overrides.location"))
    website     = property(attrgetter("overrides.website"))

    @property
    def status(self):
        myNow = timezone.localtime(timezone=self.tz)
        if getAwareDatetime(self.except_date, self.time_to, self.tz) < myNow:
            return "finished"
        elif getAwareDatetime(self.except_date, self.time_from, self.tz) < myNow:
            return "started"
        return None

    @property
    def status_text(self):
        return EventBase.status_text.fget(self)

    @property
    def _upcoming_datetime_from(self):
        return self._checkFromDt(lambda fromDt:fromDt >= timezone.localtime())

    @property
    def _past_datetime_from(self):
        return self._checkFromDt(lambda fromDt:fromDt < timezone.localtime())

    def _checkFromDt(self, predicate):
        if not self.overrides._occursOn(self.except_date):
            return None
        fromDt = getLocalDatetime(self.except_date, self.time_from, self.tz)
        return fromDt if predicate(fromDt) else None

# ------------------------------------------------------------------------------
class CancellationPageForm(EventExceptionPageForm):
    slugName = "cancellation"

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        self._checkSlugAvailable(cleaned_data, "postponement")
        return cleaned_data

class CancellationPage(Page, EventExceptionBase):
    class Meta:
        verbose_name = "Cancellation"
        default_manager_name = "objects"

    parent_page_types = ["joyous.RecurringEventPage"]
    subpage_types = []
    base_form_class = CancellationPageForm

    cancellation_title = models.CharField('Title', max_length=255, blank=True)
    cancellation_title.help_text = "Show in place of cancelled event "\
                                   "(Leave empty to show nothing)"
    cancellation_details = RichTextField('Details', blank=True)
    cancellation_details.help_text = "Why was the event cancelled?"

    # Note title is not displayed
    content_panels = [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('except_date'),
        MultiFieldPanel([
            FieldPanel('cancellation_title', classname="full title"),
            FieldPanel('cancellation_details', classname="full")],
            heading="Cancellation"),
        ]
    promote_panels = []

    @property
    def status(self):
        return "cancelled"

    @property
    def status_text(self):
        return "This event has been cancelled."

    def isAuthorized(self, request):
        return all(restriction.accept_request(request)
                   for restriction in self.get_view_restrictions())

# ------------------------------------------------------------------------------
class PostponementQuerySet(EventQuerySet):
    def upcoming(self):
        qs = super().upcoming()
        return qs.filter(date__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(date__lte = todayUtc() + _1day)

    def this(self):
        class ThisPostponementIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.postponement_title, page)
        qs = self._chain()
        qs._iterable_class = ThisPostponementIterable
        return qs

    def byDay(self, fromDate, toDate):
        fromOrd = fromDate.toordinal()
        toOrd   = toDate.toordinal()
        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = [EventsOnDay(dt.date.fromordinal(ord), [], [])
                         for ord in range(fromOrd, toOrd+1)]
                for page in super().__iter__():
                    pageFromDate = getLocalDate(page.date,
                                                page.time_from, page.tz)
                    pageToDate   = getLocalDate(page.date,
                                                page.time_to, page.tz)
                    dayNum = pageFromDate.toordinal() - fromOrd
                    thisEvent = ThisEvent(page.postponement_title, page)
                    if 0 <= dayNum <= toOrd - fromOrd:
                        evods[dayNum].days_events.append(thisEvent)
                    if pageFromDate != pageToDate:
                        if 0 <= dayNum+1 <= toOrd - fromOrd:
                            evods[dayNum+1].continuing_events.append(thisEvent)
                for evod in evods:
                    yield evod
        qs = self._chain()
        qs._iterable_class = ByDayIterable
        return qs.filter(date__range=(fromDate - _1day, toDate + _1day))

class PostponementPageForm(EventExceptionPageForm):
    slugName = "postponement"

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        self._checkSlugAvailable(cleaned_data, "cancellation")
        EventPageForm._checkStartBeforeEnd(self, cleaned_data)
        return cleaned_data

class PostponementPage(EventBase, CancellationPage):
    events = EventManager.from_queryset(PostponementQuerySet)()

    class Meta:
        verbose_name = "Postponement"
        default_manager_name = "objects"

    parent_page_types = ["joyous.RecurringEventPage"]
    subpage_types = []
    base_form_class = PostponementPageForm

    postponement_title = models.CharField('Title', max_length=255)
    postponement_title.help_text = "The title for the postponed event"
    date    = models.DateField("Date")

    content_panels = [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('except_date'),
        MultiFieldPanel([
            FieldPanel('cancellation_title', classname="full title"),
            FieldPanel('cancellation_details', classname="full")],
            heading="Cancellation"),
        MultiFieldPanel([
            FieldPanel('postponement_title', classname="full title"),
            ImageChooserPanel('image'),
            FieldPanel('date'),
            FieldPanel('time_from', widget=TimeInput),
            FieldPanel('time_to', widget=TimeInput),
            FieldPanel('details', classname="full"),
            MapFieldPanel('location'),
            FieldPanel('website')],
            heading="Postponed to"),
    ]
    promote_panels = []

    @property
    def tz(self):
        # use the parent's time zone
        return self.overrides.tz

    @property
    def group(self):
        # use the parent's group
        return self.overrides.group

    @property
    def status(self):
        myNow = timezone.localtime(timezone=self.tz)
        if getAwareDatetime(self.date, self.time_to, self.tz) < myNow:
            return "finished"
        elif getAwareDatetime(self.date, self.time_from, self.tz) < myNow:
            return "started"
        return None

    @property
    def when(self):
        return self._getLocalWhen(self.date)

    @property
    def postponed_from_when(self):
        return self.cancellationpage.when

    @property
    def at(self):
        return timeFormat(self._getFromTime())

    def _getFromTime(self):
        return getLocalTime(self.date, self.time_from, self.tz)

    def _getFromDt(self):
        return getLocalDatetime(self.date, self.time_from, self.tz)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
