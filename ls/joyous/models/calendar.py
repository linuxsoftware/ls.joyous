# ------------------------------------------------------------------------------
# Joyous calendar models
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect
from django.utils import timezone
from wagtail.core.models import Page
from wagtail.core.fields import RichTextField
from wagtail.admin.edit_handlers import FieldPanel, MultiFieldPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, route
from wagtail.search import index
from ..utils.weeks import week_info, gregorian_to_week_date
from ..utils.weeks import weekday_abbr, weekday_name
from . import getAllEventsByDay
from . import getAllEventsByWeek
from . import getAllUpcomingEvents
from . import getAllPastEvents

# ------------------------------------------------------------------------------
# Calendar
# ------------------------------------------------------------------------------
DatePictures = {"YYYY":  r"((?:19|20)\d\d)",
                "MM":    r"(1[012]|0?[1-9])",
                "Mmm":   r"({})".format("|".join(calendar.month_abbr[1:])),
                "DD":    r"(3[01]|[12]\d|0?[1-9])",
                "WW":    r"(5[0-3]|[1-4]\d|0?[1-9])"}

class CalendarPage(RoutablePageMixin, Page):
    subpage_types = ['joyous.SimpleEventPage',
                     'joyous.MultidayEventPage',
                     'joyous.RecurringEventPage']

    intro = RichTextField(blank=True)

    search_fields = Page.search_fields
    content_panels = Page.content_panels + [
        FieldPanel('intro', classname="full"),
        ]
    settings_panels = Page.settings_panels + [
        MultiFieldPanel([
            ], "Warning! this feature is experimental : Import"),
        MultiFieldPanel([
            ], "Export"),
        ]

    @route(r"^$")
    @route(r"^{YYYY}/$".format(**DatePictures))
    def routeDefault(self, request, year=None):
        eventsView = getattr(settings, "JOYOUS_DEFAULT_EVENTS_VIEW", "Monthly")
        if eventsView == "List":
            return self.serveUpcoming(request)
        elif eventsView == "Weekly":
            return self.serveWeek(request, year)
        else:
            return self.serveMonth(request, year)

    @route(r"(?i)^{YYYY}/{Mmm}/$".format(**DatePictures))
    def routeByMonthAbbr(self, request, year, monthAbbr):
        month = calendar.month_abbr[:].index(monthAbbr.title())
        return self.serveMonth(request, year, month)

    @route(r"^month/$")
    @route(r"^{YYYY}/{MM}/$".format(**DatePictures))
    def serveMonth(self, request, year=None, month=None):
        myurl = self.get_url(request)
        def myUrl(urlYear, urlMonth):
            return myurl + self.reverse_subpage('serveMonth',
                                                args=[urlYear, urlMonth])

        today = timezone.localdate()
        if year is None: year = today.year
        if month is None: month = today.month
        year = int(year)
        month = int(month)

        if year == today.year and month == today.month:
            weekNum = gregorian_to_week_date(today)[1]
        else:
            weekNum = gregorian_to_week_date(dt.date(year, month, 7))[1]
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[year, weekNum])
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

        return render(request, "joyous/calendar_month.html",
                      {'self':         self,
                       'page':         self,
                       'year':         year,
                       'month':        month,
                       'today':        today,
                       'yesterday':    today - dt.timedelta(1),
                       'lastweek':     today - dt.timedelta(7),
                       'prevMonthUrl': myUrl(prevMonthYear, prevMonth),
                       'nextMonthUrl': myUrl(nextMonthYear, nextMonth),
                       'prevYearUrl':  myUrl(year - 1, month),
                       'nextYearUrl':  myUrl(year + 1, month),
                       'weeklyUrl':    weeklyUrl,
                       'listUrl':      listUrl,
                       'thisMonthUrl': myUrl(today.year, today.month),
                       'monthName':    calendar.month_name[month],
                       'weekdayAbbr':  weekday_abbr,
                       'events':       self._getEventsByWeek(request, year, month)})

    @route(r"^week/$")
    @route(r"^{YYYY}/W{WW}/$".format(**DatePictures))
    def serveWeek(self, request, year=None, week=None):
        myurl = self.get_url(request)
        def myUrl(urlYear, urlWeek):
            return myurl + self.reverse_subpage('serveWeek',
                                                args=[urlYear, urlWeek])

        today = timezone.localdate()
        thisYear, thisWeekNum, _ = gregorian_to_week_date(today)
        if year is None: year = thisYear
        if week is None: week = thisWeekNum
        year = int(year)
        week = int(week)

        firstDay, lastDay, prevYearNumWeeks, yearNumWeeks = week_info(year, week)
        eventsInWeek = self._getEventsByDay(request, firstDay, lastDay)
        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[firstDay.year, firstDay.month])
        listUrl = myurl + self.reverse_subpage('serveUpcoming')
        if week == 53 and yearNumWeeks == 52:
            year += 1
            week = 1

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

        return render(request, "joyous/calendar_week.html",
                      {'self':         self,
                       'page':         self,
                       'year':         year,
                       'week':         week,
                       'today':        today,
                       'yesterday':    today - dt.timedelta(1),
                       'prevWeekUrl':  myUrl(prevWeekYear, prevWeek),
                       'nextWeekUrl':  myUrl(nextWeekYear, nextWeek),
                       'prevYearUrl':  myUrl(year - 1, week),
                       'nextYearUrl':  myUrl(year + 1, week),
                       'thisWeekUrl':  myUrl(thisYear, thisWeekNum),
                       'monthlyUrl':   monthlyUrl,
                       'listUrl':      listUrl,
                       'weekName':     "Week {}".format(week),
                       'weekdayAbbr':  weekday_abbr,
                       'events':       [eventsInWeek]})

    @route(r"^day/$")
    @route(r"^{YYYY}/{MM}/{DD}/$".format(**DatePictures))
    def serveDay(self, request, year=None, month=None, dom=None):
        myurl = self.get_url(request)
        today = timezone.localdate()
        if year is None: year = today.year
        if month is None: month = today.month
        if dom is None: dom = today.day
        year = int(year)
        month = int(month)
        dom = int(dom)
        day = dt.date(year, month, dom)

        eventsOnDay = self._getEventsOnDay(request, day)
        if len(eventsOnDay.all_events) == 1:
            event = eventsOnDay.all_events[0].page
            return redirect(event.get_url(request))

        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[year, month])
        weekNum = gregorian_to_week_date(today)[1]
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[year, weekNum])
        listUrl = myurl + self.reverse_subpage('serveUpcoming')

        return render(request, "joyous/calendar_list_day.html",
                      {'self':         self,
                       'page':         self,
                       'year':         year,
                       'month':        month,
                       'dom':          dom,
                       'day':          day,
                       'monthlyUrl':   monthlyUrl,
                       'weeklyUrl':    weeklyUrl,
                       'listUrl':      listUrl,
                       'monthName':    calendar.month_name[month],
                       'weekdayName':  calendar.day_name[month],
                       'events':       eventsOnDay})

    @route(r"^upcoming/$")
    def serveUpcoming(self, request):
        myurl = self.get_url(request)
        today = timezone.localdate()
        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[today.year, today.month])
        weekNum = gregorian_to_week_date(today)[1]
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[today.year, weekNum])
        listUrl = myurl + self.reverse_subpage('servePast')
        events = self._getUpcomingEvents(request)

        return render(request, "joyous/calendar_list_upcoming.html",
                      {'self':         self,
                       'page':         self,
                       'today':        today,
                       'weeklyUrl':    weeklyUrl,
                       'monthlyUrl':   monthlyUrl,
                       'listUrl':      listUrl,
                       'events':       events})

    @route(r"^past/$")
    def servePast(self, request):
        myurl = self.get_url(request)
        today = timezone.localdate()
        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[today.year, today.month])
        weekNum = gregorian_to_week_date(today)[1]
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[today.year, weekNum])
        listUrl = myurl + self.reverse_subpage('serveUpcoming')
        events = self._getPastEvents(request)

        return render(request, "joyous/calendar_list_past.html",
                      {'self':         self,
                       'page':         self,
                       'today':        today,
                       'weeklyUrl':    weeklyUrl,
                       'monthlyUrl':   monthlyUrl,
                       'listUrl':      listUrl,
                       'events':       events})

    @route(r"^mini/{YYYY}/{MM}/$".format(**DatePictures))
    def serveMiniMonth(self, request, year=None, month=None):
        if not request.is_ajax():
            raise Http404("/mini/ is for ajax requests only")

        today = timezone.localdate()
        if year is None: year = today.year
        if month is None: month = today.month
        year = int(year)
        month = int(month)

        return render(request, "joyous/includes/minicalendar.html",
                      {'self':         self,
                       'page':         self,
                       'today':        today,
                       'year':         year,
                       'month':        month,
                       'calendarUrl':  self.get_url(request),
                       'monthName':    calendar.month_name[month],
                       'weekdayInfo':  zip(weekday_abbr, weekday_name),
                       'events':       self._getEventsByWeek(request, year, month)})

    def _getEventsOnDay(self, request, day):
        return getAllEventsByDay(request, day, day)[0]

    def _getEventsByDay(self, request, firstDay, lastDay):
        return getAllEventsByDay(request, firstDay, lastDay)

    def _getEventsByWeek(self, request, year, month):
        return getAllEventsByWeek(request, year, month)

    def _getUpcomingEvents(self, request):
        return getAllUpcomingEvents(request)

    def _getPastEvents(self, request):
        return getAllPastEvents(request)

    #def _getAllEvents(self, request):
    #    return getAllEvents(request)
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
