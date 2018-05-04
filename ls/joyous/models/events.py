# ------------------------------------------------------------------------------
# Joyous events models
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from collections import namedtuple
from itertools import groupby
from operator import attrgetter
from django.conf import settings
from django.db import models
from django.utils.html import format_html
from django.utils import timezone
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import (FieldPanel, MultiFieldPanel,
        PageChooserPanel)
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.images import get_image_model_string
from wagtail.search import index
from wagtail.admin.forms import WagtailAdminPageForm
from ..holidays.parser import parseHolidays
from ..utils.telltime import (getAwareDatetime, getLocalDatetime,
        getLocalDateAndTime, getLocalDate, getLocalTime, assertLocalTime)
from ..utils.telltime import timeFrom, timeTo
from ..utils.telltime import timeFormat, dateFormat
from ..utils.weeks import week_of_month
# from ..utils.ical import export_event
from ..recurrence import RecurrenceField
from ..recurrence import ExceptionDatePanel
from ..widgets import TimeInput
from .groups import get_group_model_string, get_group_model

# using django-timezone-field
from timezone_field import TimeZoneField
# TODO consider using django-timezone-utils?
# from timezone_utils.fields import TimeZoneField

try:
    # Use wagtailgmaps for location if it is installed
    # but don't depend upon it
    settings.INSTALLED_APPS.index('wagtailgmaps')
    from wagtailgmaps.edit_handlers import MapFieldPanel
except (ValueError, ImportError):
    MapFieldPanel = FieldPanel

# ------------------------------------------------------------------------------
# Event Pages
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

# ------------------------------------------------------------------------------
_1day = dt.timedelta(days=1)

def _getEventsByDay(date_from, eventsByDaySrcs):
    eventsByDay = []
    day = date_from
    for srcs in zip(*eventsByDaySrcs):
        days_events       = []
        continuing_events = []
        for src in srcs:
            days_events += src.days_events
            continuing_events += src.continuing_events
        def sortByTime(thisEvent):
            time_from = thisEvent.page.time_from
            if time_from is None:
                time_from = dt.time.max
            return time_from
        days_events.sort(key=sortByTime)
        eventsByDay.append(EventsOnDay(day, days_events, continuing_events))
        day += _1day
    return eventsByDay

def getAllEventsByDay(date_from, date_to):
    simpleEvents    = SimpleEventPage.getEventsByDay(date_from, date_to)
    multidayEvents  = MultidayEventPage.getEventsByDay(date_from, date_to)
    recurringEvents = RecurringEventPage.getEventsByDay(date_from, date_to)
    postponedEvents = PostponementPage.getEventsByDay(date_from, date_to)
    allEvents = _getEventsByDay(date_from, (simpleEvents, multidayEvents,
                                            recurringEvents, postponedEvents))
    return allEvents

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

def getAllEventsByWeek(year, month):
    return _getEventsByWeek(year, month, getAllEventsByDay)

# ------------------------------------------------------------------------------
def _getUpcomingEvents(simpleEventsQry=None,
                       multidayEventsQry=None,
                       recurringEventsQry=None,
                       postponedEventsQry=None,
                       extraInfoQry=None):
    todaySomewhere = dt.datetime.utcnow().date() - _1day
    events = []
    if simpleEventsQry is not None:
        for event in simpleEventsQry.live().filter(date__gte=todaySomewhere):
            if event._upcoming_datetime_from:
                events.append(ThisEvent(event.title, event))
    if multidayEventsQry is not None:
        for event in multidayEventsQry.live().filter(date_from__gte=todaySomewhere):
            if event._upcoming_datetime_from:
                events.append(ThisEvent(event.title, event))
    if postponedEventsQry is not None:
        for event in postponedEventsQry.live().filter(date__gte=todaySomewhere):
            if event._upcoming_datetime_from:
                events.append(ThisEvent(event.postponement_title, event))
    if extraInfoQry is not None:
        for event in extraInfoQry.live().filter(except_date__gte=todaySomewhere)     \
                                        .exclude(extra_title=""):
            if event._upcoming_datetime_from:
                events.append(ThisEvent(event.extra_title, event))
    if recurringEventsQry is not None:
        for event in recurringEventsQry.live():
            if event._upcoming_datetime_from:
                events.append(ThisEvent(event.title, event))
    return events

def getAllUpcomingEvents(home=None):
    if home is None:
        events =  _getUpcomingEvents(SimpleEventPage.objects,
                                     MultidayEventPage.objects,
                                     RecurringEventPage.objects,
                                     PostponementPage.objects,
                                     ExtraInfoPage.objects)
    else:
        events = _getUpcomingEvents(SimpleEventPage.objects.descendant_of(home),
                                    MultidayEventPage.objects.descendant_of(home),
                                    RecurringEventPage.objects.descendant_of(home),
                                    PostponementPage.objects.descendant_of(home),
                                    ExtraInfoPage.objects.descendant_of(home))
    events.sort(key=attrgetter('page._upcoming_datetime_from'))
    return events

def getGroupUpcomingEvents(group):
    # Get events that are a child of a group page, or a postponement or extra
    # info a child of the recurring event child of the group (using descendant_of)
    events = _getUpcomingEvents(SimpleEventPage.objects.child_of(group),
                                MultidayEventPage.objects.child_of(group),
                                RecurringEventPage.objects.child_of(group),
                                PostponementPage.objects.descendant_of(group),
                                ExtraInfoPage.objects.descendant_of(group))

    # Get events that are linked to a group page, or a postponement or extra
    # info a child of the recurring event linked to a group (the long way)
    events += _getUpcomingEvents(group.simpleeventpage_events,
                                 group.multidayeventpage_events)
    rrEvents = _getUpcomingEvents(recurringEventsQry=group.recurringeventpage_events)
    events += rrEvents
    for rrEvent in rrEvents:
        postponedEventsQry = PostponementPage.objects.child_of(rrEvent.page)
        extraInfoQry       = ExtraInfoPage.objects.child_of(rrEvent.page)
        events += _getUpcomingEvents(postponedEventsQry=postponedEventsQry,
                                     extraInfoQry=extraInfoQry)
    events.sort(key=attrgetter('page._upcoming_datetime_from'))
    return events

def _getPastEvents(simpleEventsQry=None,
                   multidayEventsQry=None,
                   recurringEventsQry=None,
                   postponedEventsQry=None,
                   extraInfoQry=None):
    todaySomewhere = dt.datetime.utcnow().date() + _1day
    events = []
    if simpleEventsQry is not None:
        for event in simpleEventsQry.live().filter(date__lte=todaySomewhere):
            if event._past_datetime_from:
                events.append(ThisEvent(event.title, event))
    if multidayEventsQry is not None:
        for event in multidayEventsQry.live().filter(date_from__lte=todaySomewhere):
            if event._past_datetime_from:
                events.append(ThisEvent(event.title, event))
    if postponedEventsQry is not None:
        for event in postponedEventsQry.live().filter(date__lte=todaySomewhere):
            if event._past_datetime_from:
                events.append(ThisEvent(event.postponement_title, event))
    if extraInfoQry is not None:
        for event in extraInfoQry.live().filter(except_date__lte=todaySomewhere)    \
                                        .exclude(extra_title=""):
            if event._past_datetime_from:
                events.append(ThisEvent(event.extra_title, event))
    if recurringEventsQry is not None:
        for event in recurringEventsQry.live():
            if event._past_datetime_from:
                events.append(ThisEvent(event.title, event))
    return events

def getAllPastEvents():
    events = _getPastEvents(SimpleEventPage.objects,
                            MultidayEventPage.objects,
                            RecurringEventPage.objects,
                            PostponementPage.objects,
                            ExtraInfoPage.objects)
    events.sort(key=attrgetter('page._past_datetime_from'), reverse=True)
    return events

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
                                    on_delete=models.SET_NULL,
                                    related_name="%(class)s_events",
                                    related_query_name="%(class)s_event")
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
    @assertLocalTime
    def _upcoming_datetime_from(self):
        fromDt = self._getFromDt()
        return fromDt if fromDt >= timezone.localtime() else None

    @property
    @assertLocalTime
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

    def _getFromDt(self):
        raise NotImplementedError()

def removeContentPanels(remove):
    SimpleEventPage._removeContentPanels(remove)
    MultidayEventPage._removeContentPanels(remove)
    RecurringEventPage._removeContentPanels(remove)
    PostponementPage._removeContentPanels(remove)

# ------------------------------------------------------------------------------
class SimpleEventPage(Page, EventBase):
    class Meta:
        verbose_name = "Event Page"

    parent_page_types = ["joyous.CalendarPage",
                         get_group_model_string()]
    subpage_types = []
    base_form_class = EventPageForm

    date = models.DateField("Date", default=dt.date.today)

    content_panels = Page.content_panels + [
        FieldPanel('category'),
        ImageChooserPanel('image'),
        FieldPanel('date'),
        FieldPanel('time_from', widget=TimeInput),
        FieldPanel('time_to', widget=TimeInput),
        FieldPanel('tz'),
        ] + EventBase.content_panels1

    @classmethod
    def getEventsByDay(cls, date_from, date_to):
        ordFrom =  date_from.toordinal()
        ordTo   =  date_to.toordinal()
        # TODO think about changing to the same algorithm as for multiday event
        # This works and is arguably faster [O(#pages) < O(#days * #pages) ???]
        # but the other one is easier to read
        events = [EventsOnDay(dt.date.fromordinal(ord), [], [])
                  for ord in range(ordFrom, ordTo+1)]

        dateRange = (date_from-_1day, date_to+_1day)
        pages = SimpleEventPage.objects.live().filter(date__range=dateRange)
        for page in pages:
            # convert event dates to local dates
            fromDate = getLocalDate(page.date, page.time_from, page.tz)
            toDate   = getLocalDate(page.date, page.time_to, page.tz)
            dayNum = fromDate.toordinal() - ordFrom
            thisEvent = ThisEvent(page.title, page)
            if 0 <= dayNum <= ordTo - ordFrom:
                events[dayNum].days_events.append(thisEvent)
            if fromDate != toDate:
                if 0 <= dayNum+1 <= ordTo - ordFrom:
                    events[dayNum+1].continuing_events.append(thisEvent)
        return events

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
        timeFrom = getLocalTime(self.date, self.time_from, self.tz)
        return timeFormat(timeFrom)

    @assertLocalTime
    def _getFromDt(self):
        return getLocalDatetime(self.date, self.time_from, self.tz)

# ------------------------------------------------------------------------------
# TODO I *could* replace SimpleEventPage with MultidayEventPage

class MultidayEventPageForm(EventPageForm):
    def _checkStartBeforeEnd(self, cleaned_data):
        startDate = cleaned_data.get('date_from', dt.date.min)
        endDate   = cleaned_data.get('date_to', dt.date.max)
        if startDate > endDate:
            self.add_error('date_to', "Event cannot end before it starts")
        elif startDate == endDate:
            super()._checkStartBeforeEnd(cleaned_data)

class MultidayEventPage(Page, EventBase):
    class Meta:
        verbose_name = "Multiday Event Page"

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

    @classmethod
    def getEventsByDay(cls, date_from, date_to):
        events = []
        ordFrom =  date_from.toordinal()
        ordTo   =  date_to.toordinal()
        # TODO think about using this algorithm for the other event classes
        days = [dt.date.fromordinal(ord) for ord in range(ordFrom, ordTo+1)]
        pages = MultidayEventPage.objects.live()                             \
                                 .filter(date_to__gte   = date_from-_1day)   \
                                 .filter(date_from__lte = date_to+_1day)
        for day in days:
            days_events = []
            continuing_events = []
            for page in pages:
                # convert event dates to local dates
                fromDate = getLocalDate(page.date_from, page.time_from, page.tz)
                toDate   = getLocalDate(page.date_to, page.time_to, page.tz)
                if fromDate == day:
                    days_events.append(ThisEvent(page.title, page))
                elif fromDate < day <= toDate:
                    continuing_events.append(ThisEvent(page.title, page))
            events.append(EventsOnDay(day, days_events, continuing_events))
        return events

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
        timeFrom = getLocalTime(self.date_from, self.time_from, self.tz)
        return timeFormat(timeFrom)

    @assertLocalTime
    def _getFromDt(self):
        return getLocalDatetime(self.date_from, self.time_from, self.tz)

# ------------------------------------------------------------------------------
class RecurringEventPage(Page, EventBase):
    class Meta:
        verbose_name = "Recurring Event Page"

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
        # TODO default to max or min ?!?!?!!!
        nextDt = self.__localAfter(timezone.localtime(), dt.time.min)
        if nextDt is not None:
            return nextDt.date()
        else:
            return None

    @property
    @assertLocalTime
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
        # TODO default to max or min ?!?!?!!!
        prevDt = self.__localBefore(timezone.localtime(), dt.time.min)
        if prevDt is not None:
            return prevDt.date()
        else:
            return None

    @property
    @assertLocalTime
    def _past_datetime_from(self):
        prevDt = self.__localBefore(timezone.localtime(), dt.time.max,
                                    excludeCancellations=True,
                                    excludeExtraInfo=True)
        return prevDt

    @property
    def next_on(self):
        """
        Formatted date/time of when this event (including any postponements)
        will next be on
        """
        retval = None
        # TODO default to max or min ?!?!?!!!
        nextDt, event = self.__localAfterOrPostponedTo(timezone.localtime(),
                                                       dt.time.min)
        if nextDt is not None:
            timeFrom = nextDt.time() if event.time_from is not None else None
            retval = "{} {}".format(dateFormat(nextDt.date()),
                                    timeFormat(timeFrom, prefix="at "))
            if event is not self:
                retval = format_html('<a class="inline-link" href="{}">{}</a>',
                                     event.url, retval)
        return retval

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
        # TODO: is calculating the next date too expensive?????
        # if so change it to just be based on today's date
        # fromTime = getLocalTime(timezone.localdate(), self.time_from)
        # toTime = getLocalTime(timezone.localdate(), self.time_to)
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
        # TODO as above
        timeFrom = None
        fromDt   = self.__after(timezone.localtime(timezone=self.tz))
        if fromDt is not None:
            timeFrom = getLocalTime(fromDt.date(), self.time_from, self.tz)
        return timeFormat(timeFrom)

    @property
    def future_exceptions(self):
        """
        Returns all future extra info, cancellations and postponements created
        for this recurring event
        """
        retval = []
        # We know all future exception dates are in the parent time zone
        myToday = timezone.localdate(timezone=self.tz)

        for extraInfo in ExtraInfoPage.objects.live().child_of(self)         \
                                      .filter(except_date__gte=myToday):
            retval.append(ThisEvent(extraInfo.extra_title, extraInfo))
        for cancellation in CancellationPage.objects.live().child_of(self)   \
                                            .filter(except_date__gte=myToday):
            postponement = getattr(cancellation, "postponementpage", None)
            if postponement:
                retval.append(ThisEvent(postponement.postponement_title, postponement))
            else:
                retval.append(ThisEvent(cancellation.cancellation_title, cancellation))
        retval.sort(key=attrgetter('page.except_date'))
        return retval

    # TODO add def _localOccursOn(self, localDate)?

    def _occursOn(self, myDate):
        """
        Returns true iff this event occurs on this date (in event's own timezone)
        (Does not include postponements, but does exclude cancellations)
        """
        # TODO analyse which is faster (rrule or db) and test that first
        if myDate not in self.repeat:
            return False
        if CancellationPage.objects.live().child_of(self)                    \
                           .filter(except_date=myDate).exists():
            return False
        return True

    @classmethod
    def getEventsByDay(cls, date_from, date_to):
        ordFrom =  date_from.toordinal()
        ordTo   =  date_to.toordinal()
        # TODO As with simple event, think about changing to the same algorithm
        # as used for multiday event
        events = [EventsOnDay(dt.date.fromordinal(ord), [], [])
                  for ord in range(ordFrom, ordTo+1)]
        pages = RecurringEventPage.objects.live()
        for page in pages:
            exceptions = page.__getExceptions(date_from-_1day, date_to+_1day)

            for occurence in page.repeat.between(date_from-_1day,
                                                 date_to+_1day, True):
                thisEvent = None
                exception = exceptions.get(occurence)
                if exception:
                    if exception.title:
                        thisEvent = exception
                else:
                    thisEvent = ThisEvent(page.title, page)

                if thisEvent:
                    fromDate = getLocalDate(occurence, page.time_from, page.tz)
                    todDate  = getLocalDate(occurence, page.time_to, page.tz)
                    dayNum = fromDate.toordinal() - ordFrom
                    if 0 <= dayNum <= ordTo - ordFrom:
                        events[dayNum].days_events.append(thisEvent)
                    if fromDate != todDate:
                        if 0 <= dayNum+1 <= ordTo - ordFrom:
                            events[dayNum+1].continuing_events.append(thisEvent)
        return events

    def __getExceptions(self, date_from, date_to):
        exceptions = {}

        for extraInfo in ExtraInfoPage.objects.live().child_of(self)         \
                         .filter(except_date__range=(date_from, date_to)):
            title = extraInfo.extra_title or self.title
            exceptions[extraInfo.except_date] = ThisEvent(title, extraInfo)

        for cancellation in CancellationPage.objects.live().child_of(self)   \
                         .filter(except_date__range=(date_from, date_to)):
            title = cancellation.cancellation_title
            exceptions[cancellation.except_date] = ThisEvent(title, cancellation)

        return exceptions

    def __localAfterOrPostponedTo(self, fromDt, timeDefault=dt.time.min):
        myFromDt, event = self.__afterOrPostponedTo(fromDt.astimezone(self.tz))
        if myFromDt is not None:
            localFromDt = getLocalDatetime(myFromDt.date(), event.time_from,
                                           self.tz, timeDefault)
            return (localFromDt, event)
        else:
            return (None, event)

    def __afterOrPostponedTo(self, fromDt):
        assert timezone.is_aware(fromDt)
        after = self.__after(fromDt)
        # We know all postponement exception dates are in the parent time zone
        if after:
            # is there a postponed event before that?
            # nb: range is inclusive
            postponements = PostponementPage.objects.live().child_of(self)                \
                                     .filter(date__range=(fromDt.date(), after.date()))   \
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
            postponements = PostponementPage.objects.live().child_of(self)   \
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
        assert timezone.is_aware(fromDt)
        fromDate = fromDt.date()
        if self.time_from and self.time_from < fromDt.time():
            fromDate += dt.timedelta(days=1)
        exceptions = set()
        if excludeCancellations:
            for cancelled in CancellationPage.objects.live().child_of(self)  \
                                     .filter(except_date__gte=fromDate):
                exceptions.add(cancelled.except_date)
        if excludeExtraInfo:
            for info in ExtraInfoPage.objects.live().child_of(self)          \
                                     .filter(except_date__gte=fromDate)      \
                                     .exclude(extra_title=""):
                exceptions.add(info.except_date)
        for occurence in self.repeat.xafter(fromDate, inc=True):
            if occurence not in exceptions:
                # TODO or return a plain date?
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
        assert timezone.is_aware(fromDt)
        fromDate = fromDt.date()
        if self.time_from and self.time_from > fromDt.time():
            fromDate -= dt.timedelta(days=1)
        exceptions = set()
        if excludeCancellations:
            for cancelled in CancellationPage.objects.live().child_of(self)  \
                                     .filter(except_date__lte=fromDate):
                exceptions.add(cancelled.except_date)
        if excludeExtraInfo:
            for info in ExtraInfoPage.objects.live().child_of(self)          \
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
        timeFrom = getLocalTime(self.except_date, self.time_from, self.tz)
        return timeFormat(timeFrom)

# ------------------------------------------------------------------------------
class ExtraInfoPageForm(EventExceptionPageForm):
    name        = "Extra Information"
    description = name.lower()
    slugName    = "extra-info"

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        return cleaned_data

class ExtraInfoPage(Page, EventExceptionBase):
    class Meta:
        verbose_name = "Extra Event Information"

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
    #@assertLocalTime
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

# ------------------------------------------------------------------------------
class PostponementPageForm(EventExceptionPageForm):
    slugName = "postponement"

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        self._checkSlugAvailable(cleaned_data, "cancellation")
        EventPageForm._checkStartBeforeEnd(self, cleaned_data)
        return cleaned_data

class PostponementPage(EventBase, CancellationPage):
    class Meta:
        verbose_name = "Postponement"

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

    @classmethod
    def getEventsByDay(cls, date_from, date_to):
        ordFrom =  date_from.toordinal()
        ordTo   =  date_to.toordinal()
        # TODO As with simple event, think about changing to the same algorithm
        # as used for multiday event
        # better yet how about refactoring it out
        events = [EventsOnDay(dt.date.fromordinal(ord), [], [])
                  for ord in range(ordFrom, ordTo+1)]

        dateRange = (date_from-_1day, date_to+_1day)
        pages = PostponementPage.objects.live().filter(date__range=dateRange)
        for page in pages:
            fromDate = getLocalDate(page.date, page.time_from, page.tz)
            toDate   = getLocalDate(page.date, page.time_to, page.tz)
            dayNum = fromDate.toordinal() - ordFrom
            thisEvent = ThisEvent(page.postponement_title, page)
            if 0 <= dayNum <= ordTo - ordFrom:
                events[dayNum].days_events.append(thisEvent)
            if fromDate != toDate:
                if 0 <= dayNum+1 <= ordTo - ordFrom:
                    events[dayNum+1].continuing_events.append(thisEvent)
        return events

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
        timeFrom = getLocalTime(self.date, self.time_from, self.tz)
        return timeFormat(timeFrom)

    @assertLocalTime
    def _getFromDt(self):
        return getLocalDatetime(self.date, self.time_from, self.tz)


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
