# ------------------------------------------------------------------------------
# Test Multiday Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase
from django.contrib.auth.models import User
from wagtail.core.models import Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import MultidayEventPage


class TestMultidayEvent(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@ok.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = MultidayEventPage(owner = self.user,
                                       slug  = "allnighter",
                                       title = "All Night",
                                       date_from = dt.date(2012,12,31),
                                       date_to   = dt.date(2013,1,1),
                                       time_from = dt.time(23),
                                       time_to   = dt.time(3))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByDay(self):
        events = MultidayEventPage.getEventsByDay(dt.date(2012,12,1),
                                                  dt.date(2012,12,31))
        self.assertEqual(len(events), 31)
        evod = events[30]
        self.assertEqual(evod.date, dt.date(2012,12,31))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        events = MultidayEventPage.getEventsByDay(dt.date(2013,1,1),
                                                  dt.date(2013,1,31))
        self.assertEqual(len(events), 31)
        evod = events[0]
        self.assertEqual(evod.date, dt.date(2013,1,1))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 0)
        self.assertEqual(len(evod.continuing_events), 1)

    def testStatus(self):
        self.assertEqual(self.event.status, "finished")
        self.assertEqual(self.event.status_text, "This event has finished.")
        today = dt.date.today()
        yesterday = today - dt.timedelta(1)
        nextWeek = today + dt.timedelta(6 - today.weekday())
        nowEvent = MultidayEventPage(owner = self.user,
                                     slug  = "now",
                                     title = "Now Event",
                                     date_from = yesterday,
                                     date_to   = nextWeek)
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent.status, "started")
        self.assertEqual(nowEvent.status_text, "This event has started.")
        tomorrow = today + dt.timedelta(days=1)
        futureEvent = MultidayEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date_from  = tomorrow,
                                      date_to    = tomorrow + dt.timedelta(days=1))
        self.calendar.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent.status)
        self.assertEqual(futureEvent.status_text, "")

    def testWhen(self):
        # the odd spacing is expected / not a problem for HTML output
        self.assertEqual(self.event.when, "Monday 31st of December 2012 at 11pm  to "
                                          "Tuesday 1st of January 2013 at 3am ")

    def testAt(self):
        self.assertEqual(self.event.at.strip(), "11pm")

    def testUpcomingDt(self):
        self.assertIsNone(self.event._upcoming_datetime_from)
        now = dt.datetime.now()
        today = now.date()
        nextWeek = today + dt.timedelta(6 - today.weekday())
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = MultidayEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date_from = earlier.date(),
                                   date_to   = nextWeek,
                                   time_from = earlier.time(),
                                   time_to   = dt.time(1))
        self.calendar.add_child(instance=nowEvent)
        self.assertIsNone(nowEvent._upcoming_datetime_from)
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        futureEvent = MultidayEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date_from  = tomorrow,
                                      date_to    = tomorrow + dt.timedelta(2))
        self.calendar.add_child(instance=futureEvent)
        self.assertEqual(futureEvent._upcoming_datetime_from,
                         dt.datetime.combine(tomorrow, dt.time.max))

    def testPastDt(self):
        self.assertEqual(self.event._past_datetime_from,
                         dt.datetime(2012,12,31,23,0))
        now = dt.datetime.now()
        today = now.date()
        nextWeek = today + dt.timedelta(6 - today.weekday())
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = MultidayEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date_from = earlier.date(),
                                   date_to   = nextWeek,
                                   time_from = earlier.time(),
                                   time_to   = dt.time(1))
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent._past_datetime_from, earlier)
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        futureEvent = MultidayEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date_from  = tomorrow,
                                      date_to    = tomorrow + dt.timedelta(2))
        self.calendar.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent._past_datetime_from)

    def testGroup(self):
        self.assertIsNone(self.event.group)
