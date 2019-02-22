# ------------------------------------------------------------------------------
# Test Calendar Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django_bs_test import TestCase
from django.contrib.auth.models import User
from django.utils import translation
from wagtail.core.models import Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import SimpleEventPage

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('i', 'i@j.test', 's3(r3t')
        calendar = CalendarPage(owner  = self.user,
                                slug  = "events",
                                title = "Events")
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
        self.assertEqual(len(select("table.calendar thead tr th.sun")), 1)
        month = select("tr.heading th.month .month-name")[0]
        self.assertEqual(month.string.strip(), "March")
        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.day")), 31)
        self.assertEqual(len(select("tbody td.noday")), 4)
        holidayNames = [holiday.string.strip() for holiday in
                        select("tbody td.day .holiday .holiday-name")]
        self.assertEqual(holidayNames,
                         ["Taranaki Anniversary Day", "Otago Anniversary Day"])

    def testMonthAbbr(self):
        response = self.client.get("/events/2012/Apr/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select("table.calendar thead tr th.sun")), 1)
        month = select("tr.heading th.month .month-name")[0]
        self.assertEqual(month.string.strip(), "April")

    def testWeekView(self):
        response = self.client.get("/events/2012/W11/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select('thead a')), 4)
        self.assertEqual(len(select("table.calendar thead tr th.sun")), 1)
        self.assertEqual(len(select("tbody tr")), 1)
        self.assertEqual(len(select("tbody td.day")), 7)
        holidays = select("tbody td.day .holiday")
        self.assertEqual(len(holidays), 1)
        self.assertEqual(holidays[0].h4.string.strip(), "12 Mar")
        self.assertEqual(holidays[0].div.string.strip(),
                         "Taranaki Anniversary Day")

    def testDayWithOneEvent(self):
        response = self.client.get("/events/2011/6/5/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/events/tree-planting/")

    def testUpcomingEvents(self):
        response = self.client.get("/events/upcoming/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".upcoming-events")), 1)
        self.assertEqual(len(select(".upcoming-events .event-item")), 0)

    def testPastEvents(self):
        response = self.client.get("/events/past/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select(".past-events")), 1)
        events = select(".past-events .event-item")
        self.assertEqual(len(events), 1)
        title = events[0].select("a.event-title")[0]
        self.assertEqual(title.string.strip(), "Tree Planting")
        self.assertEqual(title['href'], "/events/tree-planting/")
        when = events[0].select(".event-when")[0]
        self.assertEqual(when.string.strip(),
                         "Sunday 5th of June 2011 at 9:30am to 11am")

    def testMiniMonthView(self):
        response = self.client.get("/events/mini/2011/06/")
        self.assertEqual(response.status_code, 404)

    def testMiniMonthAjaxView(self):
        response = self.client.get("/events/mini/2011/06/",
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(select("table.minicalendar thead tr th.sun")), 1)
        month = select("tr.heading th.month .month-name")[0]
        self.assertEqual(month.string.strip(), "June")
        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.day")), 30)
        self.assertEqual(len(select("tbody td.noday")), 5)
        event = select("tbody td.day a.event")[0]
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
        links0 = select('.calendar-options .events-view a')
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
        links0 = select('.calendar-options .events-view a')
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
        month = select("tr.heading th.month .month-name")[0]
        self.assertEqual(month.string.strip(), "Mars")

    def testWeekView(self):
        response = self.client.get("/calendrier/2012/W11/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        holidays = select("tbody td.day .holiday")
        self.assertEqual(holidays[0].h4.string.strip(), "12 Mar")
        self.assertEqual(holidays[0].div.string.strip(),
                         "Taranaki Anniversary Day")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
