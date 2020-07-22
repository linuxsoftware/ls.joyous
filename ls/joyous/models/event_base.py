# ------------------------------------------------------------------------------
# Joyous events models
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from collections import namedtuple
from uuid import uuid4
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.query import ModelIterable
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext
from timezone_field import TimeZoneField
from wagtail.core.query import PageQuerySet
from wagtail.core.models import Page, PageManager, PageViewRestriction
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import (FieldPanel,
        PageChooserPanel, BaseCompositeEditHandler)
from wagtail.images import get_image_model_string
from wagtail.search import index
from wagtail.admin.forms import WagtailAdminPageForm
from ..utils.telltime import getLocalDateAndTime
from ..utils.telltime import getTimeFrom, getTimeTo
from ..utils.telltime import timeFormat, dateFormat
from ..edit_handlers import MapFieldPanel
from .groups import get_group_model_string, get_group_model


# ------------------------------------------------------------------------------
# Private
# ------------------------------------------------------------------------------
def _filterContentPanels(panels, remove):
    retval = []
    for panel in panels:
        if isinstance(panel, FieldPanel) and panel.field_name in remove:
            continue
        elif isinstance(panel, BaseCompositeEditHandler):
            panel.children = _filterContentPanels(panel.children, remove)
        retval.append(panel)
    return retval

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
    def __init__(self, fromDate, toDate, holidays=None):
        if holidays is None:
            holidays = {}
        self.fromOrd = fromDate.toordinal()
        self.toOrd   = toDate.toordinal()
        days = [dt.date.fromordinal(ord)
                for ord in range(self.fromOrd, self.toOrd+1)]
        super().__init__(EventsOnDay(day, holidays.get(day)) for day in days)

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
        self._fetchResults()
        self._filterResults()

    def _fetchResults(self):
        super()._fetch_all()

    def _filterResults(self):
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
        class ThisIterable(ModelIterable):
            def __iter__(self):
                for page in super().__iter__():
                    yield ThisEvent(page.title, page, page.get_url(request))
        qs = self._clone()
        qs._iterable_class = ThisIterable
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

    # Init these variables to prevent template DEBUG messages
    # Yes, this is very ugly.  An alternative solution would be welcome.
    cancellation_details = None
    extra_information    = None
    postponed_from_when  = None

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
    def at(self):
        """
        A string describing what time the event starts (in the local time zone).
        """
        return timeFormat(self._getFromTime())

    @classmethod
    def _removeContentPanels(cls, *args):
        """
        Remove the panels and so hide the fields named.
        """
        remove = []
        for arg in args:
            if type(arg) is str:
                remove.append(arg)
            else:
                remove.extend(arg)
        cls.content_panels = _filterContentPanels(cls.content_panels, remove)

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
        # This is used by the default implementations of
        # _current_datetime_from, _future_datetime_from, _past_datetime_from,
        # and _first_datetime_from
        raise NotImplementedError()

    def _getToDt(self):
        """
        Datetime that the event ends (in the local time zone).
        """
        # This is used by the default implementation of
        # _current_datetime_from
        raise NotImplementedError()

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
