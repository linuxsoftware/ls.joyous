# ------------------------------------------------------------------------------
# Joyous events models
# ------------------------------------------------------------------------------
import datetime as dt
from django.db import models
from django.db.models.query import ModelIterable
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.core.models import Page
from wagtail.admin.edit_handlers import FieldPanel
from wagtail.images.edit_handlers import ImageChooserPanel

from ..utils.telltime import (todayUtc, getAwareDatetime, getLocalDatetime,
        getLocalDate, getLocalTime)
from ..utils.telltime import timeFormat
from ..edit_handlers import TimePanel
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
    def when(self):
        """
        A string describing when the event occurs (in the local time zone).
        """
        return self._getLocalWhen(self.date)

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
    def when(self):
        """
        A string describing when the event occurs (in the local time zone).
        """
        return self._getLocalWhen(self.date_from, self.date_to)

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
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
