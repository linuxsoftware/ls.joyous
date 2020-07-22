# ------------------------------------------------------------------------------
# Joyous events models
# ------------------------------------------------------------------------------
import datetime as dt
from operator import attrgetter
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import models
from django.db.models import Q
from django.db.models.query import ModelIterable
from django import forms
from django.forms import widgets
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils import translation
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext, gettext_noop
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import (FieldPanel, MultiFieldPanel,
        PageChooserPanel)
from wagtail.images.edit_handlers import ImageChooserPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.search import index
from wagtail.admin.forms import WagtailAdminPageForm
from modelcluster.fields import ParentalKey
from ..utils.manythings import hrJoin
from ..utils.mixins import ProxyPageMixin
from ..utils.telltime import (todayUtc, getAwareDatetime, getLocalDatetime,
        getLocalDateAndTime, getLocalDate, getLocalTime, getLocalTimeAtDate)
from ..utils.telltime import getTimeFrom, getTimeTo
from ..utils.telltime import timeFormat, dateFormat
from ..fields import RecurrenceField
from ..edit_handlers import (TZDatePanel, ExceptionDatePanel, TimePanel,
        MapFieldPanel)
from ..holidays import Holidays
from .groups import get_group_model_string
from .event_base import (ThisEvent, EventsByDayList,
        EventManager, EventQuerySet, EventPageForm, EventBase)

# ------------------------------------------------------------------------------
# Helper types and constants
# ------------------------------------------------------------------------------
_1day  = dt.timedelta(days=1)
_2days = dt.timedelta(days=2)

# ------------------------------------------------------------------------------
# Event models
# ------------------------------------------------------------------------------
class EventWithHolidaysManager(EventManager):
    def get_queryset(self):
        return self._queryset_class(self.model).live()

    def __call__(self, request, holidays):
        # a shortcut
        return self.get_queryset().auth(request).hols(holidays)

class EventWithHolidaysQuerySet(EventQuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.holidays = None

    def _clone(self):
        qs = super()._clone()
        qs.holidays = self.holidays
        return qs

    def _fetch_all(self):
        super()._fetchResults()
        # make sure we all have the same holidays
        if self.holidays is not None:
            for item in self._result_cache:
                for event in getattr(item, 'all_events', [item]):
                    page = getattr(event, 'page', event)
                    page.holidays = self.holidays
        super()._filterResults()

    def hols(self, holidays):
        qs = self._clone()
        qs.holidays = holidays
        return qs

class RecurringEventQuerySet(EventWithHolidaysQuerySet):
    def this(self):
        request = self.request
        class ThisIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.title, page, page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisIterable
        return qs

    def byDay(self, fromDate, toDate):
        request  = self.request
        holidays = self.holidays
        class ByDayIterable(ModelIterable):
            def __iter__(self):
                evods = EventsByDayList(fromDate, toDate, holidays)
                for page in super().__iter__():
                    exceptions = self.__getExceptionsFor(page)
                    closedHols = self.__getClosedForHolidays(page, holidays)
                    startDelta = dt.timedelta(days=page.num_days + 1)
                    for occurence in page.repeat.between(fromDate - startDelta,
                                                         toDate + _2days,
                                                         inc=True):
                        thisEvent = None
                        exception = exceptions.get(occurence)
                        if exception:
                            if exception.title:
                                thisEvent = exception
                        elif closedHols and closedHols._closedOn(occurence):
                            # ClosedForHolidaysPage still affects the event,
                            # even if the user is not authorized
                            if (closedHols.isAuthorized(request) and
                                closedHols.cancellation_title):
                                thisEvent = ThisEvent(closedHols.cancellation_title,
                                                      closedHols,
                                                      closedHols.get_url(request))
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
                # TODO consider storing extended cancellations in an interval tree?
                for shutdown in ExtCancellationPage.events.child_of(page)    \
                           .filter(cancelled_from_date__lte=dateRange[1])    \
                           .filter(Q(cancelled_to_date__gte=dateRange[0]) |
                                   Q(cancelled_to_date__isnull = True)):
                    if shutdown.isAuthorized(request):
                        title = shutdown.cancellation_title
                    else:
                        title = None
                    thisEvent = ThisEvent(title, shutdown,
                                          shutdown.get_url(request))
                    for myDate in shutdown._getMyRawDates(*dateRange):
                        exceptions[myDate] = thisEvent
                return exceptions

            def __getClosedForHolidays(self, page, holidays):
                closedHols = ClosedForHolidaysPage.events.hols(holidays)\
                                                  .child_of(page).first()
                return closedHols

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
    events = EventWithHolidaysManager.from_queryset(RecurringEventQuerySet)()

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
                     'joyous.ExtCancellationPage',
                     'joyous.ClosedForHolidaysPage',
                     'joyous.PostponementPage']
    base_form_class = RecurringEventPageForm
    MAX_REPEAT_COUNT = 500

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

    def __init__(self, *args, **kwargs):
        self.holidays = kwargs.pop("holidays", None)
        super().__init__(*args, **kwargs)

    @property
    def next_date(self):
        """
        Date when this event is next scheduled to occur in the local time zone
        (Does not include postponements, but does exclude cancellations)
        """
        myNextDt = self.__after(timezone.localtime(timezone=self.tz))
        if myNextDt is not None:
            return getLocalDate(myNextDt.date(), self.time_from,
                                self.tz, dt.time.min)

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
        myNextDt = self.__after(myNow - timeDelta,
                              excludeCancellations=True,
                              excludeExtraInfo=True)
        if myNextDt is not None:
            return getLocalDatetime(myNextDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    @property
    def _future_datetime_from(self):
        """
        The datetime this event next starts in the local timezone, or None if
        in the past.
        """
        myNextDt = self.__after(timezone.localtime(timezone=self.tz),
                                excludeCancellations=True,
                                excludeExtraInfo=True)
        if myNextDt is not None:
            return getLocalDatetime(myNextDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    @property
    def prev_date(self):
        """
        Date when this event last occurred in the local time zone
        (Does not include postponements, but does exclude cancellations)
        """
        myPrevDt = self.__before(timezone.localtime(timezone=self.tz))
        if myPrevDt is not None:
            return getLocalDate(myPrevDt.date(), self.time_from,
                                self.tz, dt.time.min)

    @property
    def _past_datetime_from(self):
        """
        The datetime this event previously started in the local time zone, or
        None if it never did.
        """
        myPrevDt = self.__before(timezone.localtime(timezone=self.tz),
                                 excludeCancellations=True,
                                 excludeExtraInfo=True)
        # Exclude extra info pages as this is used for sorting and the extra
        # info pages sit alongside
        if myPrevDt is not None:
            return getLocalDatetime(myPrevDt.date(), self.time_from,
                                    self.tz, dt.time.max)

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

    def _getFromTime(self, atDate=None):
        """
        What was the time of this event?  Due to time zones that depends what
        day we are talking about.  If no day is given, assume today.

        :param atDate: day in local timezone for which we want the time_from
        :rtype: time_from in local timezone
        """
        if atDate is None:
            atDate = timezone.localdate()
        return getLocalTimeAtDate(atDate, self.time_from, self.tz)

    def _futureExceptions(self, request):
        """
        Returns all future extra info, cancellations and postponements created
        for this recurring event
        """
        retval = []
        for extraInfo in ExtraInfoPage.events(request).child_of(self)         \
                                      .future():
            retval.append(extraInfo)
        for cancellation in CancellationPage.events(request).child_of(self)   \
                                            .future():
            postponement = getattr(cancellation, "postponementpage", None)
            if postponement:
                retval.append(postponement)
            else:
                retval.append(cancellation)
        for shutdown in ExtCancellationPage.events(request).child_of(self)   \
                                           .future():
            retval.append(shutdown)
        closedHols = ClosedForHolidaysPage.events(request, self.holidays)    \
                                          .child_of(self).first()
        if closedHols is not None:
            retval.append(closedHols)
        retval.sort(key=attrgetter('_future_datetime_from'))
        # notice these are events not ThisEvents
        return retval

    def _nextOn(self, request):
        """
        Formatted date/time of when this event (including any postponements)
        will next be on
        """
        retval = None
        myNow = timezone.localtime(timezone=self.tz)
        myNextDt, event = self.__afterOrPostponedTo(myNow)
        if myNextDt is not None:
            nextDate, nextTime = getLocalDateAndTime(myNextDt.date(), event.time_from,
                                                     self.tz, dt.time.min)
            retval = "{} {}".format(dateFormat(nextDate),
                                    timeFormat(nextTime, prefix=gettext("at ")))
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
        if ExtCancellationPage.events.child_of(self)                         \
                           .filter(cancelled_from_date__lte=myDate)          \
                           .filter(Q(cancelled_to_date__gte=myDate) |
                                   Q(cancelled_to_date__isnull = True))      \
                           .exists():
            return False
        closedHols = ClosedForHolidaysPage.events.hols(self.holidays)        \
                                          .child_of(self).first()
        if closedHols and closedHols._closedOn(myDate):
            return False
        return True

    def _getMyFirstDatetimeFrom(self):
        """
        The datetime this event first started, or None if it never did.
        """
        myStartDt = getAwareDatetime(self.repeat.dtstart, None,
                                     self.tz, dt.time.min)
        return self.__after(myStartDt, excludeCancellations=False)

    def _getMyFirstDatetimeTo(self, myFirstDt=False):
        """
        The datetime this event first finished, or None if it never did.
        """
        if myFirstDt is False:
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
        myNextDt = self.__after(timezone.localtime(timezone=self.tz))
        if myNextDt is not None:
            return myNextDt.date()

    def __getMyFromDt(self):
        """
        Get the datetime of the next event after or before now in my timezone.
        """
        myNow = timezone.localtime(timezone=self.tz)
        return self.__after(myNow) or self.__before(myNow)

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

    def __after(self, fromDt, excludeCancellations=True, excludeExtraInfo=False):
        fromDate = fromDt.date()
        if self.time_from and self.time_from < fromDt.time():
            fromDate += _1day
        exceptions = set()
        shutdowns  = []
        closedHols = None
        if excludeCancellations:
            for cancelled in CancellationPage.events.child_of(self)          \
                           .filter(except_date__gte=fromDate):
                exceptions.add(cancelled.except_date)
            # TODO consider storing extended cancellations in an interval tree?
            shutdowns = ExtCancellationPage.events.child_of(self) \
                           .filter(Q(cancelled_to_date__gte=fromDate) |
                                   Q(cancelled_to_date__isnull = True))
            closedHols = ClosedForHolidaysPage.events.hols(self.holidays)    \
                                              .child_of(self).first()
        if excludeExtraInfo:
            for info in ExtraInfoPage.events.child_of(self)                  \
                                     .filter(except_date__gte=fromDate)      \
                                     .exclude(extra_title=""):
                exceptions.add(info.except_date)
        for occurence in self.repeat.xafter(fromDate,
                                            count=self.MAX_REPEAT_COUNT,
                                            inc=True):
            if occurence in exceptions:
                continue
            shutdown = next((shutdown for shutdown in shutdowns
                             if shutdown._closedOn(occurence)), None)
            if shutdown is not None:
                if shutdown.cancelled_to_date is None:
                    break
                else:
                    # the next line is run; coverage is wrong
                    continue  # pragma: no cover
            if closedHols and closedHols._closedOn(occurence):
                continue
            return getAwareDatetime(occurence, self.time_from,
                                    self.tz, dt.time.min)

    def __before(self, fromDt, excludeCancellations=True, excludeExtraInfo=False):
        fromDate = fromDt.date()
        if self.time_from and self.time_from > fromDt.time():
            fromDate -= _1day
        exceptions = set()
        shutdowns  = []
        if excludeCancellations:
            for cancelled in CancellationPage.events.child_of(self)          \
                           .filter(except_date__lte=fromDate):
                exceptions.add(cancelled.except_date)
            shutdowns = ExtCancellationPage.events.child_of(self)            \
                           .filter(cancelled_from_date__lte=fromDate)
            closedHols = ClosedForHolidaysPage.events.hols(self.holidays)    \
                                              .child_of(self).first()
        if excludeExtraInfo:
            for info in ExtraInfoPage.events.child_of(self)                  \
                                     .filter(except_date__lte=fromDate)      \
                                     .exclude(extra_title=""):
                exceptions.add(info.except_date)
        last = None
        for occurence in self.repeat:
            if occurence > fromDate:
                break
            if occurence in exceptions:
                continue
            if any(shutdown._closedOn(occurence) for shutdown in shutdowns):
                continue
            if closedHols and closedHols._closedOn(occurence):
                continue
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
                     'joyous.ExtCancellationPage',
                     'joyous.RescheduleMultidayEventPage']
    template = "joyous/recurring_event_page.html"

    content_panels = RecurringEventPage.content_panels0 + [
        FieldPanel('num_days'),
        ] + RecurringEventPage.content_panels1

# ------------------------------------------------------------------------------
# EventException models
# ------------------------------------------------------------------------------
class EventExceptionBase(models.Model):
    class Meta:
        abstract = True

    # overrides is also the parent, but parent is not set until the
    # child is saved and added.  (NB: is published version of parent)
    overrides = models.ForeignKey('joyous.RecurringEventPage',
                                  null=True, blank=False,
                                  related_name='+',
                                  verbose_name=_("overrides"),
                                  # can't set to CASCADE, so go with SET_NULL
                                  on_delete=models.SET_NULL)
    overrides.help_text = _("The recurring event that we are updating.")

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

    # NB: exceptions do not need _first_datetime_from

    # Init these variables to prevent template DEBUG messages
    # Yes, this is very ugly.  An alternative solution would be welcome.
    cancellation_details = None
    extra_information    = None
    postponed_from_when  = None

    @property
    def at(self):
        """
        A string describing what time the event starts (in the local time zone).
        """
        return timeFormat(self._getFromTime())

    @property
    def overrides_repeat(self):
        """
        The recurrence rule of the event being overridden.
        """
        return getattr(self.overrides, 'repeat', None)

    def get_context(self, request, *args, **kwargs):
        retval = super().get_context(request, *args, **kwargs)
        retval['overrides'] = self.overrides
        retval['themeCSS'] = getattr(settings, "JOYOUS_THEME_CSS", "")
        return retval

    # TOO CONFUSING.  Stick with English and the event's timezone
    # def get_admin_display_title(self):
    #     if self.has_unpublished_changes:
    #         # WARNING this could be expensive
    #         page = self.get_latest_revision().as_page_object()
    #     else:
    #         page = self
    #     return page.local_title

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

# ------------------------------------------------------------------------------
class DateExceptionQuerySet(EventQuerySet):
    def current(self):
        qs = super().current()
        return qs.filter(except_date__gte = todayUtc() - _1day)

    def future(self):
        qs = super().future()
        return qs.filter(except_date__gte = todayUtc() - _1day)

    def past(self):
        qs = super().past()
        return qs.filter(except_date__lte = todayUtc() + _1day)

class DateExceptionPageForm(WagtailAdminPageForm):
    def _checkSlugAvailable(self, cleaned_data, slugName=None):
        if slugName is None:
            slugName = self.instance.slugName
        description = getattr(self, 'description', "a {}".format(slugName))
        exceptDate = cleaned_data.get('except_date', "invalid")
        slug = "{}-{}".format(exceptDate, slugName)
        if not Page._slug_is_available(slug, self.parent_page, self.instance):
            self.add_error('except_date',
                           _("That date already has") + " " + description.lower())

class DateExceptionBase(EventExceptionBase):
    class Meta:
        abstract = True

    events = EventManager.from_queryset(DateExceptionQuerySet)()

    except_date = models.DateField(_("For Date"))
    except_date.help_text = _("For this date")

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
            # Friday the 10th of April for 3 days starting at 1pm finishing at 10am
            # TODO Is "Friday the 10th of April at 1pm to Sunday the 12th of April at 10am" better????
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
        daysDelta = dt.timedelta(days=self.num_days - 1)
        return getAwareDatetime(self.except_date + daysDelta, self.time_to, self.tz)

    def _copyFieldsFromParent(self, parent):
        """
        Copy across field values from the recurring event parent.
        """
        super()._copyFieldsFromParent(parent)
        self.except_date = parent._getMyNextDate()

# ------------------------------------------------------------------------------
class ExtraInfoQuerySet(DateExceptionQuerySet):
    def this(self):
        request = self.request
        class ThisIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.extra_title, page,
                                    page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisIterable
        return qs

class ExtraInfoPageForm(DateExceptionPageForm):
    description = _("Extra Information")

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        return cleaned_data

class ExtraInfoPage(DateExceptionBase, Page):
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
        now = timezone.localtime()
        if self._getToDt() < now:
           return "finished"
        elif self._getFromDt() < now:
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
        # _occursOn means a lookup of CancellationPage and ClosedForHolidaysPage
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
class CancellationQuerySet(DateExceptionQuerySet):
    def this(self):
        request = self.request
        class ThisIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.cancellation_title, page,
                                    page.getCancellationUrl(request))
        qs = self._clone()
        qs._iterable_class = ThisIterable
        return qs

class CancellationPageForm(DateExceptionPageForm):
    description = _("a cancellation")

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        self._checkSlugAvailable(cleaned_data, "postponement")
        return cleaned_data

class CancellationBase(models.Model):
    class Meta:
        abstract = True

    cancellation_title = models.CharField(_("title"), max_length=255, blank=True)
    cancellation_title.help_text = _("Show in place of cancelled event "
                                     "(Leave empty to show nothing)")
    cancellation_details = RichTextField(_("details"), blank=True)
    cancellation_details.help_text = _("Why was the event cancelled?")

    search_fields = Page.search_fields + [
        index.SearchField('cancellation_title'),
        index.SearchField('cancellation_details'),
    ]

    cancellation_panel = MultiFieldPanel([
            FieldPanel('cancellation_title', classname="full title"),
            FieldPanel('cancellation_details', classname="full")],
            heading=_("Cancellation"))

    @property
    def status(self):
        """
        The current status of the event
        """
        return "cancelled"

    @property
    def status_text(self):
        """
        A text description of the current status of the event.
        """
        return _("This event has been cancelled.")

class CancellationPage(CancellationBase, DateExceptionBase, Page):
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

    search_fields = Page.search_fields + CancellationBase.search_fields

    # Note title is not displayed
    content_panels = [
        PageChooserPanel('overrides'),
        ExceptionDatePanel('except_date'),
        CancellationBase.cancellation_panel,
        ]
    promote_panels = []

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
        class ThisIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.postponement_title,
                                    page, page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisIterable
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

class PostponementPageForm(DateExceptionPageForm):
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
    picked up by Django before the properties from EventExceptionBase,
    as well as before EventBase.
    """
    class Meta:
        abstract = True

    # num_days from here to come before overrides.num_days
    num_days = models.IntegerField(_("number of days"), default=1,
                                   validators=[MinValueValidator(1),
                                               MaxValueValidator(99)])
    # Original properties
    tz          = property(attrgetter("overrides.tz"))
    group       = property(attrgetter("overrides.group"))
    uid         = property(attrgetter("overrides.uid"))
    group_page  = None
    get_context = DateExceptionBase.get_context

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
        CancellationBase.cancellation_panel,
        postponement_panel,
    ]
    promote_panels = []

    @route(r"^from/$")
    def serveCancellation(self, request):
        return TemplateResponse(request,
                                "joyous/postponement_page_from.html",
                                self.get_context(request))

    @property
    def when(self):
        """
        A string describing when the postponement occurs (in the local time zone).
        """
        return DateExceptionBase._getLocalWhen(self, self.date, self.num_days)

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
        daysDelta = dt.timedelta(days=self.num_days - 1)
        return getLocalDatetime(self.date + daysDelta, self.time_to, self.tz)

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
class ClosedFor(models.Model):
    """The holidays we are closed for."""
    class Meta:
        ordering = ['pk']
        unique_together = ['page', 'name']

    page = ParentalKey('joyous.ClosedForHolidaysPage',
                       on_delete=models.CASCADE,
                       related_name="closed_for")
    name = models.CharField(_("name"), max_length=100)
    # Storing holidays by name is a violation of 1NF, but holidays are
    # defined programmatically not in the database and the definitions
    # may change, so there is no holiday_id which can be used instead.

    # used by ChoiceWidget.format_value
    def __str__(self):
        return self.name

class ClosedForHolidaysQuerySet(EventWithHolidaysQuerySet):
    def this(self):
        request = self.request
        class ThisIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.cancellation_title, page,
                                    page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisIterable
        return qs

class ClosedForHolidaysPageForm(WagtailAdminPageForm):
    class Media:
        css = { 'all': ["admin/css/widgets.css",
                        "joyous/css/holidays_admin.css"] }
        js = ["/django-admin/jsi18n",
              "joyous/js/holidays_admin.js"]

    holidays_class = Holidays
    description = _("closed for holidays")
    closed_for = forms.MultipleChoiceField(label=_("These holidays"),
                                           required=False,
                                           widget=FilteredSelectMultiple(
                                                            _("Holidays"),
                                                            is_stacked=False))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['closed_for'].choices = self._holidayChoices()
        self.initial['closed_for'] = list(self.instance.closed_for.all())

    def save(self, commit=True):
        self._saveChosenHolidays()
        page = super().save(commit)
        return page

    def _holidayChoices(self):
        if self.instance.holidays is not None:
            holidays = self.instance.holidays
        else:
            holidays = self.holidays_class()
        retval = [(name, name) for name in holidays.names()]
        return retval

    def _saveChosenHolidays(self):
        chosen = self.cleaned_data.get('closed_for', [])
        initial = {day.name: day for day in self.initial['closed_for']}
        days = [initial.get(name, ClosedFor(name=name)) for name in chosen]
        self.instance.closed_for.set(days)

class ClosedForHolidaysPage(CancellationBase, EventExceptionBase, Page):
    class Meta:
        verbose_name = _("closed for holidays")
        verbose_name_plural = _("closed for holidays")
        default_manager_name = "objects"

    events = EventWithHolidaysManager.from_queryset(ClosedForHolidaysQuerySet)()
    parent_page_types = ["joyous.RecurringEventPage"]
    # TODO add "joyous.MultidayRecurringEventPage" : How would that work?
    # A. If the first day of the event is a holiday then the event is cancelled, or
    # B. If a holiday occurs anywhere in the event the event is cancelled, or
    # C. If every day of the event is a holiday then the event is cancelled?
    subpage_types = []
    base_form_class = ClosedForHolidaysPageForm
    MAX_REPEAT_COUNT = RecurringEventPage.MAX_REPEAT_COUNT
    MAX_DATETIME = timezone.make_aware(dt.datetime.max - _2days)
    MIN_DATETIME = timezone.make_aware(dt.datetime.min + _2days)

    all_holidays = models.BooleanField(default=True)
    all_holidays.help_text = "Cancel any occurence of this event on a public holiday"

    search_fields = Page.search_fields + CancellationBase.search_fields
    # Note title is not displayed
    content_panels = [
        PageChooserPanel('overrides'),
        MultiFieldPanel([
            FieldPanel('all_holidays'),
            FieldPanel('closed_for')],
            heading=_("Closed For")),
        CancellationBase.cancellation_panel,
        ]
    promote_panels = []

    @classmethod
    def can_create_at(cls, parent):
        retval = (super().can_create_at(parent) and
                  not cls.objects.descendant_of(parent).exists())
        return retval

    def __init__(self, *args, **kwargs):
        self.holidays = kwargs.pop("holidays", None)
        super().__init__(*args, **kwargs)
        self.__closedSet = None

    def full_clean(self, *args, **kwargs):
        """
        Apply fixups that need to happen before per-field validation occurs.
        Sets the page's title.
        """
        self.title = "Closed for holidays"
        self.slug  = "closed-for-holidays"
        super().full_clean(*args, **kwargs)

    @property
    def local_title(self):
        """
        Localised version of the human-readable title of the page.
        """
        return _("Closed for holidays")

    @property
    def status_text(self):
        """
        A text description of the current status of the event.
        """
        return _("Closed for holidays.")

    @property
    def when(self):
        """
        A string describing when the event occurs (in the local time zone).
        """
        if self.all_holidays:
            retval = _("Closed for holidays")
        else:
            retval = _("Closed for {}").format(hrJoin(self.closed))
            # TODO: it'd be quite cool if we could say
            # "Closed for {current-holiday}"
            # This would require changes to ThisEvent either add another field
            # or make the big move and turn it into a proper facade class
        return retval

    @property
    def closed(self):
        """
        The list of holidays we are closed for, or "ALL" if we are closed for
        all holidays.
        """
        if self.all_holidays:
            retval = "ALL"
        else:
            retval = [day.name for day in self.closed_for.all()]
        return retval

    @property
    def _current_datetime_from(self):
        """
        The datetime the event that was cancelled would start in the local
        timezone, or None if it would have finished by now.
        """
        # TODO this code would need to change if this is going to support
        # MultidayRecurringEventPage
        return self._future_datetime_from

    @property
    def _future_datetime_from(self):
        """
        The datetime the event that was cancelled would start in the local
        timezone, or None if that is in the past.
        """
        if self.holidays is None:
            return self.MAX_DATETIME
        myNextDt = self.__after(timezone.localtime(timezone=self.tz))
        if myNextDt is not None:
            return getLocalDatetime(myNextDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    @property
    def _past_datetime_from(self):
        """
        The datetime of the event that was cancelled in the local timezone, or
        None if it never would have.
        """
        if self.holidays is None:
            return self.MIN_DATETIME
        myPrevDt = self.__before(timezone.localtime(timezone=self.tz))
        if myPrevDt is not None:
            return getLocalDatetime(myPrevDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    @property
    def _closed_for_dates(self):
        """
        Return all the dates which we are closed for in the local timezone
        """
        for occurence in self._getMyDates():
            yield getLocalDate(occurence, self.time_from, self.tz)

    def _getMyDates(self):
        """
        Return all the dates which we are closed for in the event timezone
        """
        if self.holidays is not None:
            self._cacheClosedSet()
            if not self.__closedSet:
                return None
            n = 0
            for occurence in self.overrides.repeat:
                n += 1
                if n > self.MAX_REPEAT_COUNT:
                    # that's enough, bailing out
                    return None
                if self._closedOn(occurence):
                    n = 0
                    yield occurence

    def _getFromTime(self, atDate=None):
        """
        Time that the event starts (in the local time zone).
        """
        return self.overrides._getFromTime(atDate)

    def _cacheClosedSet(self):
        """
        Cache the set of names of the holidays we are closed for.
        This needs to be re-called if the page's fields change.
        """
        closed = self.closed
        if closed == "ALL":
            self.__closedSet = "ALL"
        else:
            self.__closedSet = set(self.closed)

    def _closedOn(self, myDate):
        """
        Are we closed for holidays on myDate?
        """
        if self.holidays is None:
            return False
        if self.__closedSet is None:
            self._cacheClosedSet()
        if not self.__closedSet:
            return False
        holiday = self.holidays.get(myDate)
        if holiday:
            if self.all_holidays:
                return True
            names = holiday.split(", ")
            return any(name in self.__closedSet for name in names)
        return False

    def __after(self, fromDt, excludeCancellations=True):
        fromDate = fromDt.date()
        if self.time_from and self.time_from < fromDt.time():
            fromDate += _1day
        self._cacheClosedSet()
        exceptions = set()
        shutdowns  = []
        if excludeCancellations:
            for cancelled in CancellationPage.events.child_of(self.overrides) \
                                     .filter(except_date__gte=fromDate):
                exceptions.add(cancelled.except_date)
            shutdowns = ExtCancellationPage.events.child_of(self.overrides)  \
                           .filter(Q(cancelled_to_date__gte=fromDate) |
                                   Q(cancelled_to_date__isnull = True))
        repeat = self.overrides.repeat
        for n, occurence in enumerate(repeat.xafter(fromDate, inc=True)):
            if n > self.MAX_REPEAT_COUNT:
                # that's enough, bailing out, return two days before max
                # (so we can still do TZ conversions on the result)
                return self.MAX_DATETIME
            if occurence in exceptions:
                continue
            shutdown = next((shutdown for shutdown in shutdowns
                             if shutdown._closedOn(occurence)), None)
            if shutdown is not None:
                if shutdown.cancelled_to_date is None:
                    break
                else:
                    # the next line is run; coverage is wrong
                    continue  # pragma: no cover
            if not self._closedOn(occurence):
                continue
            return getAwareDatetime(occurence, self.time_from,
                                    self.tz, dt.time.min)

    def __before(self, fromDt, excludeCancellations=True):
        fromDate = fromDt.date()
        if self.time_from and self.time_from > fromDt.time():
            fromDate -= _1day
        self._cacheClosedSet()
        exceptions = set()
        shutdowns  = []
        if excludeCancellations:
            for cancelled in CancellationPage.events.child_of(self.overrides) \
                                     .filter(except_date__lte=fromDate):
                exceptions.add(cancelled.except_date)
            shutdowns = ExtCancellationPage.events.child_of(self.overrides)  \
                           .filter(cancelled_from_date__lte=fromDate)
        last = None
        repeat = self.overrides.repeat
        for occurence in repeat:
            if occurence > fromDate:
                break
            if occurence in exceptions:
                continue
            if any(shutdown._closedOn(occurence) for shutdown in shutdowns):
                continue
            if not self._closedOn(occurence):
                continue
            last = occurence
        if last is not None:
            return getAwareDatetime(last, self.time_from, self.tz, dt.time.min)

# ------------------------------------------------------------------------------
class ExtCancellationQuerySet(EventQuerySet):
    def current(self):
        qs = super().current()
        return qs.filter(Q(cancelled_to_date__gte=todayUtc() - _1day) |
                         Q(cancelled_to_date__isnull=True))

    def future(self):
        qs = super().future()
        return qs.filter(Q(cancelled_to_date__gte=todayUtc() - _1day) |
                         Q(cancelled_to_date__isnull=True))

    def past(self):
        qs = super().past()
        return qs.filter(cancelled_from_date__lte=todayUtc() + _1day)

    def this(self):
        request = self.request
        class ThisIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.cancellation_title, page,
                                    page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisIterable
        return qs

class ExtCancellationPageForm(WagtailAdminPageForm):
    class Media:
        css = { 'all': ["joyous/css/recurrence_admin.css"] }

    def clean(self):
        cleaned_data = super().clean()
        self._checkSlugAvailable(cleaned_data)
        return cleaned_data

    def _checkSlugAvailable(self, cleaned_data):
        fromDate = cleaned_data.get('cancelled_from_date', "invalid")
        siblings = self.parent_page.get_children().not_page(self.instance)
        pattern = r"{}-.*-cancellation".format(fromDate)
        if siblings.filter(slug__regex=pattern).exists():
            self.add_error('cancelled_from_date',
                           _("There is already an extended cancellation for then"))

class ExtCancellationPage(CancellationBase, EventExceptionBase, Page):
    class Meta:
        verbose_name = _("extended cancellation")
        verbose_name_plural = _("extended cancellations")
        default_manager_name = "objects"

    events = EventManager.from_queryset(ExtCancellationQuerySet)()
    parent_page_types = ["joyous.RecurringEventPage",
                         "joyous.MultidayRecurringEventPage"]
    subpage_types = []
    base_form_class = ExtCancellationPageForm
    FAR_DATE = dt.date(3000,12,31)

    cancelled_from_date = models.DateField(_("From Date"))
    cancelled_from_date.help_text = _("Cancelled from this date")
    cancelled_to_date = models.DateField(_("To Date"), null=True, blank=True)
    cancelled_to_date.help_text = _('Cancelled to this date '
                                    '(Leave empty for "until further notice")')

    search_fields = Page.search_fields + CancellationBase.search_fields
    # Note title is not displayed
    content_panels = [
        PageChooserPanel('overrides'),
        TZDatePanel('cancelled_from_date'),
        TZDatePanel('cancelled_to_date'),
        CancellationBase.cancellation_panel,
        ]
    promote_panels = []

    @property
    def local_title(self):
        """
        Localised version of the human-readable title of the page.
        """
        title = _("Cancellation from {fromDate} {untilWhen}").format(
                            fromDate=dateFormat(self.cancelled_from_date),
                            untilWhen=self.until_when)
        return title

    @property
    def until_when(self):
        """
        A string describing how long we are cancelled for
        """
        if self.cancelled_to_date is not None:
            retval = _("to {}").format(dateFormat(self.cancelled_to_date))
        else:
            retval = _("until further notice")
        return retval

    @property
    def when(self):
        """
        A string describing when the event occurs (in the local time zone).
        """
        retval = _("Cancelled from {fromDate} {untilWhen}").format(
                            fromDate=dateFormat(self.cancelled_from_date),
                            untilWhen=self.until_when)
        return retval

    @property
    def _current_datetime_from(self):
        """
        The datetime the event that was cancelled would start in the local
        timezone, or None if it would have finished by now.
        """
        myNow = timezone.localtime(timezone=self.tz)
        timeFrom = getTimeFrom(self.time_from)
        timeTo = getTimeTo(self.time_to)
        # Yes this ignores DST transitions and milliseconds
        timeDelta = dt.timedelta(days    = self.num_days - 1,
                                 hours   = timeTo.hour   - timeFrom.hour,
                                 minutes = timeTo.minute - timeFrom.minute,
                                 seconds = timeTo.second - timeFrom.second)
        myNextDt = self.__after(myNow - timeDelta)
        if myNextDt is not None:
            return getLocalDatetime(myNextDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    @property
    def _future_datetime_from(self):
        """
        The datetime the event that was cancelled would start in the local
        timezone, or None if that is in the past.
        """
        myNextDt = self.__after(timezone.localtime(timezone=self.tz))
        if myNextDt is not None:
            return getLocalDatetime(myNextDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    @property
    def _past_datetime_from(self):
        """
        The datetime of the event that was cancelled in the local timezone, or
        None if it never would have.
        """
        myPrevDt = self.__before(timezone.localtime(timezone=self.tz))
        if myPrevDt is not None:
            return getLocalDatetime(myPrevDt.date(), self.time_from,
                                    self.tz, dt.time.max)

    def full_clean(self, *args, **kwargs):
        """
        Apply fixups that need to happen before per-field validation occurs.
        Sets the page's title.
        """
        # generate the title and slug in English
        # the translation of the title will happen in the property local_title
        with translation.override("en"):
            if self.cancelled_to_date is not None:
                titleTo = "to " + dateFormat(self.cancelled_to_date)
                slugTo = str(self.cancelled_to_date)
            else:
                titleTo = "until further notice"
                slugTo = ""

            self.title = "Cancellation from {} {}".format(
                                dateFormat(self.cancelled_from_date), titleTo)
            self.slug = "{}-{}-cancellation".format(
                                self.cancelled_from_date, slugTo)
        super().full_clean(*args, **kwargs)

    def _getMyDates(self, fromDate=dt.date.min, toDate=FAR_DATE):
        """
        Return all the dates which we are cancelled for in the event timezone.
        Only if the event occurs on those dates.
        Limited by fromDate and toDate if given.
        """
        if self.cancelled_from_date > fromDate:
            fromDate = self.cancelled_from_date
        if (self.cancelled_to_date is not None and
            self.cancelled_to_date < toDate):
            toDate = self.cancelled_to_date
        repeat = self.overrides.repeat
        yield from repeat.between(fromDate, toDate, inc=True)

    def _getMyRawDates(self, fromDate=dt.date.min, toDate=FAR_DATE):
        """
        Return all the dates which we are cancelled for in the event timezone.
        Without considering if the event occurs on those dates.
        Limited by fromDate and toDate if given.
        """
        if self.cancelled_from_date > fromDate:
            fromDate = self.cancelled_from_date
        if (self.cancelled_to_date is not None and
            self.cancelled_to_date < toDate):
            toDate = self.cancelled_to_date
        fromOrd = fromDate.toordinal()
        toOrd   = toDate.toordinal()
        for ord in range(fromOrd, toOrd+1):
            yield dt.date.fromordinal(ord)

    def _getFromTime(self, atDate=None):
        """
        Time that the event starts (in the local time zone).
        """
        return self.overrides._getFromTime(atDate)

    def _closedOn(self, myDate):
        """
        Are we closed on myDate?
        """
        if self.cancelled_to_date is not None:
            retval = (self.cancelled_from_date <= myDate <=
                      self.cancelled_to_date)
        else:
            retval = self.cancelled_from_date <= myDate
        return retval

    def __after(self, fromDt):
        fromDate = fromDt.date()
        if self.time_from and self.time_from < fromDt.time():
            fromDate += _1day
        if fromDate < self.cancelled_from_date:
            fromDate = self.cancelled_from_date
        occurence = self.overrides.repeat.after(fromDate, inc=True)
        if (self.cancelled_to_date is None or
            occurence <= self.cancelled_to_date):
            return getAwareDatetime(occurence, self.time_from,
                                    self.tz, dt.time.min)

    def __before(self, fromDt):
        fromDate = fromDt.date()
        if self.time_from and self.time_from > fromDt.time():
            fromDate -= _1day
        if (self.cancelled_to_date is not None and
            fromDate > self.cancelled_to_date):
            fromDate = self.cancelled_to_date
        occurence = self.overrides.repeat.before(fromDate, inc=True)
        if occurence >= self.cancelled_from_date:
            return getAwareDatetime(occurence, self.time_from,
                                    self.tz, dt.time.min)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
