# ------------------------------------------------------------------------------
# Joyous calendar models
# ------------------------------------------------------------------------------
import datetime as dt
import calendar
from itertools import groupby
from django.conf import settings
from django.shortcuts import render
from django.http.response import Http404
from wagtail.wagtailcore.models import Page
from wagtail.wagtailcore.fields import RichTextField
from wagtail.wagtailadmin.edit_handlers import FieldPanel
from wagtail.contrib.wagtailroutablepage.models import RoutablePageMixin, route
from wagtail.wagtailsearch import index
from ..utils.weeks import week_info, gregorian_to_week_date
from ..utils.weeks import week_of_month, weekday_abbr
from . import getAllEventsByDay
from . import getAllUpcomingEvents
from . import getAllPastEvents

# ------------------------------------------------------------------------------
# Calendar
# ------------------------------------------------------------------------------
DatePictures = {"YYYY":  r"((?:19|20)\d\d)",
                "MM":    r"(1[012]|0?[1-9])",
                "Mmm":   r"|".join(calendar.month_abbr[1:]),
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

    @route(r"(?i)^{YYYY}/{Mmm}$".format(**DatePictures))
    def routeByMonthAbbr(self, request, year, monthAbbr):
        month = calendar.month_abbr[:].index(monthAbbr)
        return self.serveMonth(request, year, month)

    @route(r"^month/$")
    @route(r"^{YYYY}/{MM}/$".format(**DatePictures))
    def serveMonth(self, request, year=None, month=None):
        myurl = self.get_url(request)
        def myUrl(urlYear, urlMonth):
            return myurl + self.reverse_subpage('serveMonth',
                                                args=[urlYear, urlMonth])

        today = dt.date.today()
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
        eventsByWeek = self._getAllEventsByWeek(year, month)

        prevMonth = month - 1
        prevMonthYear = year
        if prevMonth == 0:
            prevMonth = 12
            prevMonthYear = year - 1

        nextMonth = month + 1
        nextMonthYear = year
        if nextMonth == 13:
            nextMonth = 1
            nextMonthYear = year + 1

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
                       'events':       eventsByWeek})

    @route(r"^week/$")
    @route(r"^{YYYY}/W{WW}/$".format(**DatePictures))
    def serveWeek(self, request, year=None, week=None):
        myurl = self.get_url(request)
        def myUrl(urlYear, urlWeek):
            return myurl + self.reverse_subpage('serveWeek',
                                                args=[urlYear, urlWeek])

        today = dt.date.today()
        thisYear, thisWeekNum, _ = gregorian_to_week_date(today)
        if year is None: year = thisYear
        if week is None: week = thisWeekNum
        year = int(year)
        week = int(week)

        firstDay, lastDay, prevYearNumWeeks, yearNumWeeks = week_info(year, week)
        eventsInWeek = self._getEvents(firstDay, lastDay)
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
            prevWeekYear = year - 1

        nextWeek = week + 1
        nextWeekYear = year
        if nextWeek > yearNumWeeks:
            nextWeek = 1
            nextWeekYear = year + 1

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

    @route(r"^upcoming/$")
    def serveUpcoming(self, request):
        myurl = self.get_url(request)
        today = dt.date.today()
        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[today.year, today.month])
        weekNum = gregorian_to_week_date(today)[1]
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[today.year, weekNum])
        listUrl = myurl + self.reverse_subpage('servePast')
        events = getAllUpcomingEvents()

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
        today = dt.date.today()
        monthlyUrl = myurl + self.reverse_subpage('serveMonth',
                                                  args=[today.year, today.month])
        weekNum = gregorian_to_week_date(today)[1]
        weeklyUrl = myurl + self.reverse_subpage('serveWeek',
                                                 args=[today.year, weekNum])
        listUrl = myurl + self.reverse_subpage('serveUpcoming')
        events = getAllPastEvents()

        return render(request, "joyous/calendar_list_past.html",
                      {'self':         self,
                       'page':         self,
                       'today':        today,
                       'weeklyUrl':    weeklyUrl,
                       'monthlyUrl':   monthlyUrl,
                       'listUrl':      listUrl,
                       'events':       events})

    def _getEvents(self, firstDay, lastDay):
        return getAllEventsByDay(firstDay, lastDay)

    def _getAllEventsByWeek(self, year, month):
        weeks = []
        firstDay = dt.date(year, month, 1)
        lastDay  = dt.date(year, month, calendar.monthrange(year, month)[1])
        def calcWeekOfMonth(evod):
            return week_of_month(evod.date)
        events = self._getEvents(firstDay, lastDay)
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
# ------------------------------------------------------------------------------
