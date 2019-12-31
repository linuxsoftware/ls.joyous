# ------------------------------------------------------------------------------
# Test Calendar Pages
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from unittest.mock import Mock
from django_bs_test import TestCase
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.utils import translation
from django.urls import reverse
from wagtail.admin.edit_handlers import get_form_for_model
from wagtail.core.models import Site, Page
from ls.joyous.models.calendar import (CalendarPage, SpecificCalendarPage,
        CalendarPageForm, GeneralCalendarPage)
from ls.joyous.models.events import SimpleEventPage
from ls.joyous.models.groups import get_group_model
from .testutils import freeze_timetz, getPage

GroupPage = get_group_model()

# ------------------------------------------------------------------------------
class TestCalendar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('i', 'i@j.test', 's3(r3t')
        calendar = CalendarPage(owner  = self.user,
                                slug  = "events",
                                title = "Events",
                                default_view = "L")
        Page.objects.get(slug='home').add_child(instance=calendar)
        calendar.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "tree-planting",
                                title = "Tree Planting",
                                date      = dt.date(2011,6,5),
                                time_from = dt.time(9,30),
                                time_to   = dt.time(11,0))
        calendar.add_child(instance=event)
        event.save_revision().publish()

    def testMonthView(self):
        response = self.client.get("/events/2012/03/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select('thead a')), 4)
        self.assertEqual(len(select(".joy-cal__weekday--sun")), 1)
        month = select("tr.joy-cal__headings th.joy-cal__heading .joy-cal__month-name")[0]
        self.assertEqual(month.string.strip(), "March")
        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.joy-cal__day")), 31)
        self.assertEqual(len(select("tbody td.joy-cal__no-day")), 4)
        holidayNames = [holiday.string.strip() for holiday in
                        select("tbody td.joy-cal__day .joy-cal__holiday-name")]
        self.assertEqual(holidayNames,
                         ["Taranaki Anniversary Day", "Otago Anniversary Day"])

    def testMonthAbbr(self):
        response = self.client.get("/events/2012/Apr/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".joy-cal__weekday--sun")), 1)
        month = select(".joy-cal__month-name")[0]
        self.assertEqual(month.string.strip(), "April")

    def testWeekView(self):
        response = self.client.get("/events/2012/W11/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select('thead a')), 4)
        self.assertEqual(len(select(".joy-cal__weekday--sun")), 1)
        self.assertEqual(len(select("tbody tr")), 1)
        self.assertEqual(len(select(".joy-cal__day")), 7)
        holidayDates = select(".joy-cal__date--holiday")
        self.assertEqual(len(holidayDates), 1)
        self.assertEqual(holidayDates[0].string.strip(), "12 Mar")
        holidayNames = select(".joy-cal__holiday-name")
        self.assertEqual(holidayNames[0].string.strip(),
                         "Taranaki Anniversary Day")

    def testDayWithOneEvent(self):
        response = self.client.get("/events/2011/6/5/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/events/tree-planting/")

    def testDayWithEvents(self):
        calendar = getPage("/home/events/")
        event1 = SimpleEventPage(owner = self.user,
                                 slug  = "memory",
                                 title = "We remember",
                                 date      = dt.date(2011,6,8),
                                 time_from = dt.time(9,30),
                                 time_to   = dt.time(10,30))
        calendar.add_child(instance=event1)
        event1.save_revision().publish()
        event2 = SimpleEventPage(owner = self.user,
                                slug  = "action",
                                title = "Make things better",
                                date      = dt.date(2011,6,8),
                                time_from = dt.time(11,30),
                                time_to   = dt.time(16,0))
        calendar.add_child(instance=event2)
        event2.save_revision().publish()
        response = self.client.get("/events/2011/6/8/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".joy-cal-list")), 1)
        events = select(".joy-ev-item")
        self.assertEqual(len(events), 2)
        title = events[0].select("a.joy-title__link")[0]
        self.assertEqual(title.string.strip(), "We remember")
        self.assertEqual(title['href'], "/events/memory/")

    def testUpcomingEvents(self):
        response = self.client.get("/events/upcoming/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".joy-cal-list--upcoming")), 1)
        self.assertEqual(len(select(".joy-cal-list--upcoming .joy-ev-item")), 0)

    def testUpcomingEventsInvalidPage(self):
        response = self.client.get("/events/upcoming/?page=99")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".joy-cal-list--upcoming")), 1)
        self.assertEqual(len(select(".joy-cal-list--upcoming .joy-ev-item")), 0)

    def testPastEvents(self):
        response = self.client.get("/events/past/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".joy-cal-list--past")), 1)
        events = select(".joy-cal-list--past .joy-ev-item")
        self.assertEqual(len(events), 1)
        title = events[0].select("a.joy-title__link")[0]
        self.assertEqual(title.string.strip(), "Tree Planting")
        self.assertEqual(title['href'], "/events/tree-planting/")
        when = events[0].select(".joy-ev-when")[0]
        self.assertEqual(when.string.strip(),
                         "Sunday 5th of June 2011 at 9:30am to 11am")

    def testPastEventsInvalidPage(self):
        response = self.client.get("/events/past/?page=99")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".joy-cal-list--past")), 1)
        self.assertEqual(len(select(".joy-cal-list--past .joy-ev-item")), 1)

    def testRouteDefault(self):
        response = self.client.get("/events/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".joy-cal-list--upcoming")), 1)
        response = self.client.get("/events/?view=weekly")
        self.assertEqual(response.status_code, 200)
        select = response.soup.select
        self.assertEqual(len(select(".joy-cal__week-name")), 1)
        response = self.client.get("/events/?view=monthly")
        select = response.soup.select
        self.assertEqual(len(select(".joy-cal__month-name")), 1)

    def testMiniMonthView(self):
        response = self.client.get("/events/mini/2011/06/")
        self.assertEqual(response.status_code, 404)

    def testMiniMonthAjaxView(self):
        response = self.client.get("/events/mini/2011/06/",
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select("table.joy-minical thead tr .joy-minical__weekday--sun")), 1)
        month = select("tr th .joy-minical__month-name")[0]
        self.assertEqual(month.string.strip(), "June")
        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.joy-minical__day")), 30)
        self.assertEqual(len(select("tbody td.joy-minical__no-day")), 5)
        event = select("tbody td.joy-minical__day a.joy-minical__date--event-link")[0]
        self.assertEqual(event.string.strip(), "5")
        self.assertEqual(event['href'], "/events/2011/06/05/")
        self.assertEqual(event['title'], "Tree Planting")

    def testInvalidDates(self):
        invalidDates = ["2012/13", "2008/W54", "2099/W53"]
        for date in invalidDates:
            with self.subTest(date=date):
                response = self.client.get("/events/{}/".format(date))
                self.assertEqual(response.status_code, 404)

    def testCalendarStartMonth(self):
        response = self.client.get("/events/1900/1/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        links = select('thead a')
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].get('title'), "Next month")
        self.assertEqual(links[0].get('href'), "/events/1900/2/")
        self.assertEqual(links[1].get('title'), "Next year")
        self.assertEqual(links[1].get('href'), "/events/1901/1/")

    def testCalendarFinishMonth(self):
        response = self.client.get("/events/2099/12/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        links = select('thead a')
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].get('title'), "Previous month")
        self.assertEqual(links[0].get('href'), "/events/2099/11/")
        self.assertEqual(links[1].get('title'), "Previous year")
        self.assertEqual(links[1].get('href'), "/events/2098/12/")

    def testCalendarStartWeek(self):
        response = self.client.get("/events/1900/W1/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        links0 = select('.joy-view-choices a')
        self.assertEqual(len(links0), 3)
        self.assertEqual(links0[0].get_text(), "List View")
        self.assertEqual(links0[1].get_text(), "This Week")
        self.assertEqual(links0[2].get_text(), "Monthly View")
        self.assertEqual(links0[2].get('href'), "/events/1900/1/")
        links1 = select('thead a')
        self.assertEqual(len(links1), 2)
        self.assertEqual(links1[0].get('title'), "Next week")
        self.assertEqual(links1[0].get('href'), "/events/1900/W2/")
        self.assertEqual(links1[1].get('title'), "Next year")
        self.assertEqual(links1[1].get('href'), "/events/1901/W1/")

    def testCalendarFinishWeek(self):
        response = self.client.get("/events/2099/W52/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        links0 = select('.joy-view-choices a')
        self.assertEqual(len(links0), 3)
        self.assertEqual(links0[0].get_text(), "List View")
        self.assertEqual(links0[1].get_text(), "This Week")
        self.assertEqual(links0[2].get_text(), "Monthly View")
        self.assertEqual(links0[2].get('href'), "/events/2099/12/")
        links1 = select('thead a')
        self.assertEqual(len(links1), 2)
        self.assertEqual(links1[0].get('title'), "Previous week")
        self.assertEqual(links1[0].get('href'), "/events/2099/W51/")
        self.assertEqual(links1[1].get('title'), "Previous year")
        self.assertEqual(links1[1].get('href'), "/events/2098/W52/")

    def testNextYearW53(self):
        response = self.client.get("/events/2098/W53/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        links = select('thead a')
        self.assertEqual(len(links), 3)
        self.assertEqual(links[0].get('title'), "Previous week")
        self.assertEqual(links[0].get('href'), "/events/2098/W52/")
        self.assertEqual(links[1].get('title'), "Next week")
        self.assertEqual(links[1].get('href'), "/events/2099/W1/")
        self.assertEqual(links[2].get('title'), "Previous year")
        self.assertEqual(links[2].get('href'), "/events/2097/W52/")

    def testFutureDates(self):
        response = self.client.get("/events/2525/1/")
        self.assertEqual(response.status_code, 404)
        response = self.client.get("/events/2100/W1/")
        self.assertEqual(response.status_code, 404)

# ------------------------------------------------------------------------------
class TestCalendarPageForm(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('i', 'i@j.test', 's3(r3t')
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.home = Page.objects.get(slug='home')
        self.page = CalendarPage(owner  = self.user,
                                 slug  = "events",
                                 title = "Events")
        self.home.add_child(instance=self.page)
        self.page.save_revision().publish()

    def testImportPanel(self):
        CalendarPageForm.registerImportHandler(Mock())
        panel = CalendarPage.settings_panels[-1]
        self.assertFalse(panel._show())
        panel.instance = self.page
        panel.request  = self.request
        self.assertFalse(panel._show())
        setattr(self.page, '__joyous_edit_request', self.request)
        self.assertTrue(panel._show())
        delattr(self.page, '__joyous_edit_request')

    def testSave(self):
        Form = get_form_for_model(CalendarPage, form_class=CalendarPageForm)
        setattr(self.page, '__joyous_edit_request', self.request)
        form = Form(instance=self.page, parent_page=self.home)
        handler = Mock()
        CalendarPageForm.registerImportHandler(handler)
        form.cleaned_data = {'utc2local': True,
                             'upload':    "FILE"}
        form.save()
        handler.load.assert_called_with(self.page, self.request,
                                        "FILE", utc2local=True)


# ------------------------------------------------------------------------------
class TestFrançais(TestCase):
    def setUp(self):
        translation.activate('fr')
        self.user = User.objects.create_superuser('i', 'i@j.test', 's3(r3t')
        calendar = CalendarPage(owner  = self.user,
                                slug  = "calendrier",
                                title = "Calendrier")
        Page.objects.get(slug='home').add_child(instance=calendar)
        calendar.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "plantation-d-arbres",
                                title = "Plantation d'arbres",
                                date      = dt.date(2011,6,5),
                                time_from = dt.time(9,30),
                                time_to   = dt.time(11,0))
        calendar.add_child(instance=event)
        event.save_revision().publish()

    def tearDown(self):
        translation.deactivate()

    def testMonthView(self):
        response = self.client.get("/calendrier/2012/03/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        month = select(".joy-cal__month-name")[0]
        self.assertEqual(month.string.strip(), "Mars")

    def testWeekView(self):
        response = self.client.get("/calendrier/2012/W11/")
        select = response.soup.select
        holidayDate = select(".joy-cal__date--holiday")
        self.assertEqual(holidayDate[0].string.strip(), "12 Mar")
        holidayName = select(".joy-cal__holiday-name")
        self.assertEqual(holidayName[0].string.strip(),
                         "Taranaki Anniversary Day")

# ------------------------------------------------------------------------------
class TestSpecificCalendar(TestCase):
    def setUp(self):
        SpecificCalendarPage.is_creatable = True
        self.user = User.objects.create_user('i', 'i@j.test', 's3(r3t')
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.calendar1 = SpecificCalendarPage(owner  = self.user,
                                              slug  = "calendar1",
                                              title = "Red Team Calendar")
        home = getPage("/home/")
        home.add_child(instance=self.calendar1)
        self.calendar1.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "football",
                                title = "Football Game",
                                uid   = "570ed9c4-4503-4b45-b15e-c99faed9c531",
                                date      = dt.date(2011,6,5),
                                time_from = dt.time(9,30),
                                time_to   = dt.time(11,0))
        self.calendar1.add_child(instance=event)
        event.save_revision().publish()
        self.calendar2 = SpecificCalendarPage(owner  = self.user,
                                              slug  = "calendar2",
                                              title = "Green Team Calendar")
        home.add_child(instance=self.calendar2)
        self.calendar2.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "tree-planting",
                                title = "Tree Planting",
                                uid   = "eb50e787-12bf-477b-8493-c4414ac001ca",
                                date      = dt.date(2011,6,5),
                                time_from = dt.time(9,30))
        self.calendar2.add_child(instance=event)
        event.save_revision().publish()

    def testEventsOnDay(self):
        evod = self.calendar1._getEventsOnDay(self.request, dt.date(2011,6,5))
        self.assertEqual(evod.date, dt.date(2011,6,5))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 1)
        event = evod.days_events[0]
        self.assertEqual(event.title, "Football Game")

    def testEventsByDay(self):
        evods = self.calendar1._getEventsByDay(self.request, dt.date(2011,7,1),
                                               dt.date(2011,7,10))
        self.assertEqual(len(evods), 10)
        evod = evods[0]
        self.assertEqual(evod.date, dt.date(2011,7,1))
        self.assertEqual(len(evod.all_events), 0)

    def testEventsByWeek(self):
        weeks = self.calendar1._getEventsByWeek(self.request, 2011, 6)
        self.assertEqual(len(weeks), 5)
        self.assertIsNone(weeks[0][0])
        self.assertIsNone(weeks[0][2])
        evod = weeks[1][0]
        self.assertEqual(evod.date, dt.date(2011,6,5))
        self.assertEqual(len(evod.all_events), 1)
        event = evod.days_events[0]
        self.assertEqual(event.title, "Football Game")
        self.assertEqual(event.page.slug, "football")

    @freeze_timetz("2011-01-21 15:00")
    def testUpcomingEvents(self):
        events = self.calendar2._getUpcomingEvents(self.request)
        self.assertEqual(len(events), 1)
        title, event, url = events[0]
        self.assertEqual(title, "Tree Planting")
        self.assertEqual(event.slug, "tree-planting")

    @freeze_timetz("2011-01-21 15:00")
    def testPastEvents(self):
        events = self.calendar2._getPastEvents(self.request)
        self.assertEqual(len(events), 0)

    def testGetEventFromUid(self):
        event = self.calendar1._getEventFromUid(self.request,
                                                "570ed9c4-4503-4b45-b15e-c99faed9c531")
        self.assertEqual(event.title, "Football Game")
        event = self.calendar1._getEventFromUid(self.request,
                                                "eb50e787-12bf-477b-8493-c4414ac001ca")
        self.assertIsNone(event)

    def testGetAllEventsByDay(self):
        events = self.calendar2._getAllEvents(self.request)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Tree Planting")

# ------------------------------------------------------------------------------
class TestGeneralCalendar(TestCase):
    def setUp(self):
        GeneralCalendarPage.is_creatable = True
        self.user = User.objects.create_user('i', 'i@j.test', 's3(r3t')
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.calendar = GeneralCalendarPage(owner  = self.user,
                                             slug  = "calendar",
                                             title = "My Calendar")
        home = getPage("/home/")
        home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "bbq",
                                title = "BBQ",
                                uid   = "a94c3211-08e5-4e36-9448-86a869a47d89",
                                date      = dt.date(2011,8,20),
                                time_from = dt.time(18,30))
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        self.group = GroupPage(slug = "initech", title = "Initech Corporation")
        home.add_child(instance=self.group)
        self.group.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "planning-meeting",
                                title = "Planning to Plan",
                                uid   = "a96484da-e350-45c7-af03-97ca2bb173d6",
                                date      = dt.date(2011,8,20),
                                time_from = dt.time(8,0))
        self.group.add_child(instance=event)
        event.save_revision().publish()

    def testEventsOnDay(self):
        evod = self.calendar._getEventsOnDay(self.request, dt.date(2011,8,20))
        self.assertEqual(evod.date, dt.date(2011,8,20))
        self.assertEqual(len(evod.all_events), 2)
        self.assertEqual(len(evod.days_events), 2)
        events = evod.days_events
        self.assertEqual(events[0].title, "Planning to Plan")
        self.assertEqual(events[1].title, "BBQ")

    def testEventsByDay(self):
        evods = self.calendar._getEventsByDay(self.request, dt.date(2011,8,1),
                                              dt.date(2011,8,20))
        self.assertEqual(len(evods), 20)
        evod = evods[19]
        self.assertEqual(evod.date, dt.date(2011,8,20))
        self.assertEqual(len(evod.all_events), 2)
        events = evod.days_events
        self.assertEqual(events[0].title, "Planning to Plan")
        self.assertEqual(events[1].title, "BBQ")

    def testEventsByWeek(self):
        weeks = self.calendar._getEventsByWeek(self.request, 2011, 8)
        self.assertEqual(len(weeks), 5)
        self.assertIsNone(weeks[0][0])
        evod = weeks[2][6]
        self.assertEqual(evod.date, dt.date(2011,8,20))
        self.assertEqual(len(evod.all_events), 2)
        events = evod.days_events
        self.assertEqual(events[0].title, "Planning to Plan")
        self.assertEqual(events[1].title, "BBQ")

    @freeze_timetz("2011-08-21 15:00")
    def testUpcomingEvents(self):
        events = self.calendar._getUpcomingEvents(self.request)
        self.assertEqual(len(events), 0)

    @freeze_timetz("2011-08-21 15:00")
    def testPastEvents(self):
        events = self.calendar._getPastEvents(self.request)
        self.assertEqual(len(events), 2)
        title, event, url = events[0]
        self.assertEqual(title, "BBQ")
        self.assertEqual(event.slug, "bbq")
        title, event, url = events[1]
        self.assertEqual(event.slug, "planning-meeting")

    def testGetEventFromUid(self):
        event = self.calendar._getEventFromUid(self.request,
                                                "a94c3211-08e5-4e36-9448-86a869a47d89")
        self.assertEqual(event.title, "BBQ")
        event = self.calendar._getEventFromUid(self.request,
                                                "a96484da-e350-45c7-af03-97ca2bb173d6")
        self.assertEqual(event.title, "Planning to Plan")

    def testGetAllEventsByDay(self):
        events = self.calendar._getAllEvents(self.request)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].title, "Planning to Plan")
        self.assertEqual(events[1].title, "BBQ")

# ------------------------------------------------------------------------------
class TestMultiCalendarCreate(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('i', 'i@j.test', 's3(r3t')
        self.main = getPage("/home/")
        self.sub = Page(slug="nova", title="Nova Homepage")
        self.main.add_child(instance=self.sub)
        self.sub.save_revision().publish()
        Site.objects.create(hostname='nova.joy.test',
                            root_page_id=self.sub.id,
                            is_default_site=False)
        SpecificCalendarPage.is_creatable = True
        GeneralCalendarPage.is_creatable = True

    def testMainSiteAnotherCalendar(self):
        calendar = CalendarPage(owner  = self.user,
                                slug  = "events",
                                title = "Events",)
        self.main.add_child(instance=calendar)
        calendar.save_revision().publish()
        self.assertFalse(CalendarPage.can_create_at(self.main))

    def testSubSiteAnotherCalendar(self):
        calendar = CalendarPage(owner  = self.user,
                                slug  = "events",
                                title = "Events")
        self.main.add_child(instance=calendar)
        calendar.save_revision().publish()
        self.assertTrue(CalendarPage.can_create_at(self.sub))

    def testNoSiteAnotherCalendar(self):
        rogue = Page(slug="rogue", title="Rogue")
        self.assertFalse(CalendarPage.can_create_at(rogue))

    def testMainSiteAnotherSpecificCalendar(self):
        calendar = SpecificCalendarPage(owner  = self.user,
                                        slug  = "events",
                                        title = "Events")
        self.main.add_child(instance=calendar)
        calendar.save_revision().publish()
        self.assertTrue(SpecificCalendarPage.can_create_at(self.main))

    def testMainSiteAnotherGeneralCalendar(self):
        calendar = GeneralCalendarPage(owner  = self.user,
                                       slug  = "events",
                                       title = "Events")
        self.main.add_child(instance=calendar)
        calendar.save_revision().publish()
        self.assertFalse(GeneralCalendarPage.can_create_at(self.main))

    def testSubSiteAnotherGeneralCalendar(self):
        calendar = GeneralCalendarPage(owner  = self.user,
                                       slug  = "events",
                                       title = "Events")
        self.main.add_child(instance=calendar)
        calendar.save_revision().publish()
        self.assertFalse(GeneralCalendarPage.can_create_at(self.sub))

    def testCalendarMixture(self):
        general = GeneralCalendarPage(owner  = self.user,
                                      slug  = "events1",
                                      title = "Events")
        self.main.add_child(instance=general)
        general.save_revision().publish()
        self.assertTrue(CalendarPage.can_create_at(self.main))
        calendar = CalendarPage(owner  = self.user,
                                slug  = "events2",
                                title = "Events")
        self.main.add_child(instance=calendar)
        calendar.save_revision().publish()
        self.assertTrue(SpecificCalendarPage.can_create_at(self.main))
        specific = SpecificCalendarPage(owner  = self.user,
                                        slug  = "events3",
                                        title = "Events")
        self.main.add_child(instance=specific)
        specific.save_revision().publish()


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
