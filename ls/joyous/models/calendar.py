# ------------------------------------------------------------------------------
# Joyous calendar models
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.http import Http404
from django import forms
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from wagtail.admin.forms import WagtailAdminPageForm
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import HelpPanel, FieldPanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.search import index
from .. import __version__
from ..edit_handlers import ConcealedPanel
from ..holidays import Holidays
from ..utils.names import WEEKDAY_NAMES, MONTH_NAMES, MONTH_ABBRS
from ..utils.weeks import week_info, gregorian_to_week_date, num_weeks_in_year
from ..utils.weeks import weekday_abbr, weekday_name
from ..utils.mixins import ProxyPageMixin
from ..fields import MultipleSelectField
from . import (getAllEventsByDay, getAllEventsByWeek, getAllUpcomingEvents,
               getAllPastEvents, getEventFromUid, getAllEvents)

# ------------------------------------------------------------------------------
class CalendarPageForm(WagtailAdminPageForm):
    importHandler = None
    exportHandler = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def registerImportHandler(cls, handler):
        class Panel(ConcealedPanel):
            def _show(self):
                page = getattr(self, 'instance', None)
                if not page:
                    return False
                hasReq = hasattr(page, '__joyous_edit_request')
                if not hasReq:
                    return False
                # only a user with edit and publishing rights should be able
                # to import iCalendar files
                perms = page.permissions_for_user(self.request.user)
                return perms.can_publish() and perms.can_edit()

        cls.importHandler = handler
        uploadWidget = forms.FileInput(attrs={'accept': "text/calendar,"
                                                        "application/zip,"
                                                        ".ics,.zip"})
        cls.declared_fields['upload'] = forms.FileField(
                                            label=_("Upload"),
                                            required=False,
                                            widget=uploadWidget)
        cls.declared_fields['utc2local'] = forms.BooleanField(
                                            label=_("Convert UTC to localtime?"),
                                            required=False,
                                            initial=True)
        CalendarPage.settings_panels.append(Panel([
              FieldPanel('upload'),
              FieldPanel('utc2local'),
            ], heading=_("Import")))

    @classmethod
    def registerExportHandler(cls, handler):
        class Panel(ConcealedPanel):
            def _show(self):
                page = getattr(self, 'instance', None)
                return page and page.url is not None and page.live

        cls.exportHandler = handler
        CalendarPage.settings_panels.append(Panel([
              HelpPanel(template="joyous/edit_handlers/export_panel.html")
            ], heading=_("Export")))

    def save(self, commit=True):
        page = super().save(commit=False)
        request = getattr(page, '__joyous_edit_request', None)

        if self.importHandler and request:
            delattr(page, '__joyous_edit_request')
            utc2local = self.cleaned_data.get('utc2local')
            upload = self.cleaned_data.get('upload')
            if upload is not None:
                self.importHandler.load(page, request, upload, utc2local=utc2local)

        if commit:
            page.save()
        return page

# ------------------------------------------------------------------------------
DatePictures = {"YYYY":  r"((?:19|20)\d\d)",
                "MM":    r"(1[012]|0?[1-9])",
                "Mon":   r"({})".format("|".join(m.lower()[:3] for m in MONTH_ABBRS[1:])),
                "DD":    r"(3[01]|[12]\d|0?[1-9])",
                "WW":    r"(5[0-3]|[1-4]\d|0?[1-9])"}

EVENTS_VIEW_CHOICES = [('L', _("List View")),
                       ('W', _("Weekly View")),
                       ('M', _("Monthly View"))]

# ------------------------------------------------------------------------------
class CalendarPage(RoutablePageMixin, Page):
    """CalendarPage displays all the events which are in the same site."""
    class Meta:
        verbose_name = _("calendar page")
        verbose_name_plural = _("calendar pages")

    EventsPerPage = getattr(settings, "JOYOUS_EVENTS_PER_PAGE", 25)
    holidays = Holidays()
    subpage_types = ['joyous.SimpleEventPage',
                     'joyous.MultidayEventPage',
                     'joyous.RecurringEventPage',
                     'joyous.MultidayRecurringEventPage']
    base_form_class = CalendarPageForm

    intro = RichTextField(_("intro"), blank=True,
                          help_text=_("Introductory text."))
    view_choices = MultipleSelectField(_("view choices"), blank=True,
                                       default=["L","W","M"],
                                       choices=EVENTS_VIEW_CHOICES)
    default_view = models.CharField(_("default view"),
                                    default="M", max_length=15,
                                    choices=EVENTS_VIEW_CHOICES)

    search_fields = Page.search_fields[:]
    content_panels = Page.content_panels + [
        FieldPanel('intro', classname="full"),
        ]
    settings_panels = Page.settings_panels + [
        MultiFieldPanel([
            FieldPanel('view_choices'),
            FieldPanel('default_view')],
            heading=_("View Options")),
        ]

    @route(r"^$")
    @route(r"^{YYYY}/$".format(**DatePictures))
    def routeDefault(self, request, year=None):
        """Route a request to the default calendar view."""
        eventsView = request.GET.get('view', self.default_view)
        if eventsView in ("L", "list"):
            return self.serveUpcoming(request)
        elif eventsView in ("W", "weekly"):
            return self.serveWeek(request, year)
        else:
            return self.serveMonth(request, year)

    @route(r"^{YYYY}/{Mon}/$(?i)".format(**DatePictures))
    def routeByMonthAbbr(self, request, year, monthAbbr):
        """Route a request with a month abbreviation to the monthly view."""
        month = (DatePictures['Mon'].index(monthAbbr.lower()) // 4) + 1
        return self.serveMonth(request, year, month)

    @route(r"^month/$")
    @route(r"^{YYYY}/{MM}/$".format(**DatePictures))
    def serveMonth(self, request, year=None, month=None):
        """Monthly calendar view."""
        myurl = self.get_url(request)
        def myUrl(urlYear, urlMonth):
            if 1900 <= urlYear <= 2099:
                return myurl + self.reverse_subpage('serveMonth',
                                                    args=[urlYear, urlMonth])
        today = timezone.localdate()
        if year is None: year = today.year
        if month is None: month = today.month
        year = int(year)
        month = int(month)
        lastDay = dt.date(year, month, calendar.monthrange(year, month)[1])

        if year == today.year and month == today.month:
            weekYear, weekNum, dow = gregorian_to_week_date(today)
        else:
            weekYear, weekNum, dow = gregorian_to_week_date(dt.date(year, month, 7))
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[weekYear, weekNum])
        listUrl = myurl + self.reverse_subpage('serveUpcoming')

        prevMonth = month - 1
        prevMonthYear = year
        if prevMonth == 0:
            prevMonth = 12
            prevMonthYear -= 1

        nextMonth = month + 1
        nextMonthYear = year
        if nextMonth == 13:
            nextMonth = 1
            nextMonthYear += 1

        cxt = self._getCommonContext(request)
        cxt.update({'year':         year,
                    'month':        month,
                    'yesterday':    today - dt.timedelta(1),
                    'lastweek':     today - dt.timedelta(7),
                    'lastDay':      lastDay,
                    'prevMonthUrl': myUrl(prevMonthYear, prevMonth),
                    'nextMonthUrl': myUrl(nextMonthYear, nextMonth),
                    'prevYearUrl':  myUrl(year - 1, month),
                    'nextYearUrl':  myUrl(year + 1, month),
                    'weeklyUrl':    weeklyUrl,
                    'listUrl':      listUrl,
                    'thisMonthUrl': myUrl(today.year, today.month),
                    'monthName':    MONTH_NAMES[month],
                    'weekdayAbbr':  weekday_abbr,
                    'events':       self._getEventsByWeek(request, year, month)})
        cxt.update(self._getExtraContext("month"))
        return TemplateResponse(request,
                                "joyous/calendar_month.html",
                                cxt)

    @route(r"^week/$")
    @route(r"^{YYYY}/W{WW}/$".format(**DatePictures))
    def serveWeek(self, request, year=None, week=None):
        """Weekly calendar view."""
        myurl = self.get_url(request)
        def myUrl(urlYear, urlWeek):
            if (urlYear < 1900 or
                urlYear > 2099 or
                urlYear == 2099 and urlWeek == 53):
                return None
            if urlWeek == 53 and num_weeks_in_year(urlYear) == 52:
                urlWeek = 52
            return myurl + self.reverse_subpage('serveWeek',
                                                args=[urlYear, urlWeek])
        today = timezone.localdate()
        thisYear, thisWeekNum, dow = gregorian_to_week_date(today)
        if year is None: year = thisYear
        if week is None: week = thisWeekNum
        year = int(year)
        week = int(week)

        firstDay, lastDay, prevYearNumWeeks, yearNumWeeks = week_info(year, week)
        if week == 53 and yearNumWeeks == 52:
            raise Http404("Only 52 weeks in {}".format(year))

        eventsInWeek = self._getEventsByDay(request, firstDay, lastDay)
        if firstDay.year >= 1900:
            monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                      args=[firstDay.year, firstDay.month])
        else:
            monthlyUrl = myurl + self.reverse_subpage('serveMonth', args=[1900, 1])
        listUrl = myurl + self.reverse_subpage('serveUpcoming')
        lastDayOfMonth = dt.date(firstDay.year, firstDay.month,
                                 calendar.monthrange(firstDay.year, firstDay.month)[1])

        prevWeek = week - 1
        prevWeekYear = year
        if prevWeek == 0:
            prevWeek = prevYearNumWeeks
            prevWeekYear -= 1

        nextWeek = week + 1
        nextWeekYear = year
        if nextWeek > yearNumWeeks:
            nextWeek = 1
            nextWeekYear += 1

        cxt = self._getCommonContext(request)
        cxt.update({'year':         year,
                    'week':         week,
                    'yesterday':    today - dt.timedelta(1),
                    'lastweek':     None,
                    'lastDay':      lastDayOfMonth,
                    'prevWeekUrl':  myUrl(prevWeekYear, prevWeek),
                    'nextWeekUrl':  myUrl(nextWeekYear, nextWeek),
                    'prevYearUrl':  myUrl(year - 1, week),
                    'nextYearUrl':  myUrl(year + 1, week),
                    'thisWeekUrl':  myUrl(thisYear, thisWeekNum),
                    'monthlyUrl':   monthlyUrl,
                    'listUrl':      listUrl,
                    'weekName':     _("Week {weekNum}").format(weekNum=week),
                    'weekdayAbbr':  weekday_abbr,
                    'events':       [eventsInWeek]})
        cxt.update(self._getExtraContext("week"))
        return TemplateResponse(request,
                                "joyous/calendar_week.html",
                                cxt)

    @route(r"^day/$")
    @route(r"^{YYYY}/{MM}/{DD}/$".format(**DatePictures))
    def serveDay(self, request, year=None, month=None, dom=None):
        """The events of the day list view."""
        myurl = self.get_url(request)
        today = timezone.localdate()
        if year is None: year = today.year
        if month is None: month = today.month
        if dom is None: dom = today.day
        year = int(year)
        month = int(month)
        dom = int(dom)
        daysInMonth = calendar.monthrange(year, month)[1]
        if dom > daysInMonth:
            raise Http404("Only {} days in month".format(daysInMonth))
        day = dt.date(year, month, dom)

        daysEvents = self._getEventsOnDay(request, day).all_events
        if len(daysEvents) == 1:
            event = daysEvents[0].page
            return redirect(event.get_url(request))
        eventsPage = self._paginate(request, daysEvents)

        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[year, month])
        weekYear, weekNum, dow = gregorian_to_week_date(dt.date(year, month, 7))
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[weekYear, weekNum])
        listUrl = myurl + self.reverse_subpage('serveUpcoming')

        cxt = self._getCommonContext(request)
        cxt.update({'year':         year,
                    'month':        month,
                    'dom':          dom,
                    'day':          day,
                    'monthlyUrl':   monthlyUrl,
                    'weeklyUrl':    weeklyUrl,
                    'listUrl':      listUrl,
                    'monthName':    MONTH_NAMES[month],
                    'weekdayName':  WEEKDAY_NAMES[day.weekday()],
                    'events':       eventsPage})
        cxt.update(self._getExtraContext("day"))
        return TemplateResponse(request,
                                "joyous/calendar_list_day.html",
                                cxt)

    @route(r"^upcoming/$")
    def serveUpcoming(self, request):
        """Upcoming events list view."""
        myurl = self.get_url(request)
        today = timezone.localdate()
        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[today.year, today.month])
        weekYear, weekNum, dow = gregorian_to_week_date(today)
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[weekYear, weekNum])
        listUrl = myurl + self.reverse_subpage('servePast')
        upcomingEvents = self._getUpcomingEvents(request)
        eventsPage = self._paginate(request, upcomingEvents)

        cxt = self._getCommonContext(request)
        cxt.update({'weeklyUrl':    weeklyUrl,
                    'monthlyUrl':   monthlyUrl,
                    'listUrl':      listUrl,
                    'events':       eventsPage})
        cxt.update(self._getExtraContext("upcoming"))
        return TemplateResponse(request,
                                "joyous/calendar_list_upcoming.html",
                                cxt)

    @route(r"^past/$")
    def servePast(self, request):
        """Past events list view."""
        myurl = self.get_url(request)
        today = timezone.localdate()
        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[today.year, today.month])
        weekYear, weekNum, dow = gregorian_to_week_date(today)
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[weekYear, weekNum])
        listUrl = myurl + self.reverse_subpage('serveUpcoming')
        pastEvents = self._getPastEvents(request)
        eventsPage = self._paginate(request, pastEvents)

        cxt = self._getCommonContext(request)
        cxt.update({'weeklyUrl':    weeklyUrl,
                    'monthlyUrl':   monthlyUrl,
                    'listUrl':      listUrl,
                    'events':       eventsPage})
        cxt.update(self._getExtraContext("past"))
        return TemplateResponse(request,
                                "joyous/calendar_list_past.html",
                                cxt)

    @route(r"^mini/{YYYY}/{MM}/$".format(**DatePictures))
    def serveMiniMonth(self, request, year=None, month=None):
        """Serve data for the MiniMonth template tag."""
        if not request.is_ajax():
            raise Http404("/mini/ is for ajax requests only")

        today = timezone.localdate()
        if year is None: year = today.year
        if month is None: month = today.month
        year = int(year)
        month = int(month)

        cxt = self._getCommonContext(request)
        cxt.update({'year':         year,
                    'month':        month,
                    'calendarUrl':  self.get_url(request),
                    'monthName':    MONTH_NAMES[month],
                    'weekdayInfo':  zip(weekday_abbr, weekday_name),
                    'events':       self._getEventsByWeek(request, year, month)})
        cxt.update(self._getExtraContext("mini"))
        return TemplateResponse(request,
                                "joyous/includes/minicalendar.html",
                                cxt)

    @classmethod
    def can_create_at(cls, parent):
        return super().can_create_at(parent) and cls._allowAnotherAt(parent)

    @classmethod
    def _allowAnotherAt(cls, parent):
        """You can only create one of these pages per site."""
        site = parent.get_site()
        if site is None:
            return False
        return not cls.peers().descendant_of(site.root_page).exists()

    @classmethod
    def peers(cls):
        """Return others of the same concrete type."""
        contentType = ContentType.objects.get_for_model(cls)
        return cls.objects.filter(content_type=contentType)

    def _getCommonContext(self, request):
        cxt = self.get_context(request)
        cxt.update({'version':  __version__,
                    'themeCSS': getattr(settings, "JOYOUS_THEME_CSS", ""),
                    'today':    timezone.localdate(),

                    # Init these variables to prevent template DEBUG messages
                    'listLink':     None,
                    'weeklyLink':   None,
                    'monthlyLink':  None,
                   })
        return cxt

    def _getExtraContext(self, route):
        return {}

    def _getEventsOnDay(self, request, day):
        """Return all the events in this site for a given day."""
        return self._getEventsByDay(request, day, day)[0]

    def _getEventsByDay(self, request, firstDay, lastDay):
        """
        Return the events in this site for the dates given, grouped by day.
        """
        home = request.site.root_page
        return getAllEventsByDay(request, firstDay, lastDay,
                                 home=home, holidays=self.holidays)

    def _getEventsByWeek(self, request, year, month):
        """
        Return the events in this site for the given month grouped by week.
        """
        home = request.site.root_page
        return getAllEventsByWeek(request, year, month,
                                  home=home, holidays=self.holidays)

    def _getUpcomingEvents(self, request):
        """Return the upcoming events in this site."""
        home = request.site.root_page
        return getAllUpcomingEvents(request, home=home, holidays=self.holidays)

    def _getPastEvents(self, request):
        """Return the past events in this site."""
        home = request.site.root_page
        return getAllPastEvents(request, home=home, holidays=self.holidays)

    def _getEventFromUid(self, request, uid):
        """Try and find an event with the given UID in this site."""
        event = getEventFromUid(request, uid) # might raise exception
        home = request.site.root_page
        if event.get_ancestors().filter(id=home.id).exists():
            # only return event if it is in the same site
            return event

    def _getAllEvents(self, request):
        """Return all the events in this site."""
        home = request.site.root_page
        return getAllEvents(request, home=home, holidays=self.holidays)

    def _paginate(self, request, events):
        paginator = Paginator(events, self.EventsPerPage)
        try:
            eventsPage = paginator.page(request.GET.get('page'))
        except PageNotAnInteger:
            eventsPage = paginator.page(1)
        except EmptyPage:
            eventsPage = paginator.page(paginator.num_pages)
        return eventsPage

# ------------------------------------------------------------------------------
class SpecificCalendarPage(ProxyPageMixin, CalendarPage):
    """
    SpecificCalendarPage displays only the events which are its children
    """
    class Meta(ProxyPageMixin.Meta):
        verbose_name = _("specific calendar page")
        verbose_name_plural = _("specific calendar pages")

    is_creatable  = False  # creation is disabled by default

    @classmethod
    def _allowAnotherAt(cls, parent):
        """Don't limit creation."""
        return True

    def _getEventsByDay(self, request, firstDay, lastDay):
        """
        Return my child events for the dates given,  grouped by day.
        """
        return getAllEventsByDay(request, firstDay, lastDay,
                                 home=self, holidays=self.holidays)

    def _getEventsByWeek(self, request, year, month):
        """Return my child events for the given month grouped by week."""
        return getAllEventsByWeek(request, year, month,
                                  home=self, holidays=self.holidays)

    def _getUpcomingEvents(self, request):
        """Return my upcoming child events."""
        return getAllUpcomingEvents(request, home=self, holidays=self.holidays)

    def _getPastEvents(self, request):
        """Return my past child events."""
        return getAllPastEvents(request, home=self, holidays=self.holidays)

    def _getEventFromUid(self, request, uid):
        """Try and find a child event with the given UID."""
        event = getEventFromUid(request, uid) # might raise exception
        if event.get_ancestors().filter(id=self.id).exists():
            # only return event if it is a descendant
            return event

    def _getAllEvents(self, request):
        """Return all my child events."""
        return getAllEvents(request, home=self, holidays=self.holidays)

# ------------------------------------------------------------------------------
class GeneralCalendarPage(ProxyPageMixin, CalendarPage):
    """
    GeneralCalendarPage displays all the events no matter where they are
    """
    class Meta(ProxyPageMixin.Meta):
        verbose_name = _("general calendar page")
        verbose_name_plural = _("general calendar pages")

    is_creatable  = False  # creation is disabled by default

    @classmethod
    def _allowAnotherAt(cls, parent):
        """You can only create one of these pages."""
        return not cls.peers().exists()

    def _getEventsByDay(self, request, firstDay, lastDay):
        """
        Return all events for the dates given, grouped by day.
        """
        return getAllEventsByDay(request, firstDay, lastDay,
                                 holidays=self.holidays)

    def _getEventsByWeek(self, request, year, month):
        """Return all events for the given month grouped by week."""
        return getAllEventsByWeek(request, year, month, holidays=self.holidays)

    def _getUpcomingEvents(self, request):
        """Return all the upcoming events."""
        return getAllUpcomingEvents(request, holidays=self.holidays)

    def _getPastEvents(self, request):
        """Return all the past events."""
        return getAllPastEvents(request, holidays=self.holidays)

    def _getEventFromUid(self, request, uid):
        """Try and find an event with the given UID."""
        return getEventFromUid(request, uid) # might raise exception

    def _getAllEvents(self, request):
        """Return all the events."""
        return getAllEvents(request, holidays=self.holidays)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
