# ------------------------------------------------------------------------------
# Test Simple Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase
from django.contrib.auth.models import User
from wagtail.core.models import Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import SimpleEventPage
from ls.joyous.models.groups import get_group_model
GroupPage = get_group_model()


class TestSimpleEvent(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@ok.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = SimpleEventPage(owner = self.user,
                                    slug   = "pet-show",
                                    title  = "Pet Show",
                                    date      = dt.date(1987,6,5),
                                    time_from = dt.time(11),
                                    time_to   = dt.time(17,30))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByDay(self):
        events = SimpleEventPage.getEventsByDay(dt.date(1987,6,1),
                                                dt.date(1987,6,30))
        self.assertEqual(len(events), 30)
        evod = events[4]
        self.assertEqual(evod.date, dt.date(1987,6,5))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)

    def testStatus(self):
        self.assertEqual(self.event.status, "finished")
        self.assertEqual(self.event.status_text, "This event has finished.")
        now = dt.datetime.now()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = SimpleEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date      = now.date(),
                                   time_from = earlier.time(),
                                   time_to   = dt.time.max)
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent.status, "started")
        self.assertEqual(nowEvent.status_text, "This event has started.")
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        futureEvent = SimpleEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date  = tomorrow)
        self.calendar.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent.status)
        self.assertEqual(futureEvent.status_text, "")

    def testWhen(self):
        self.assertEqual(self.event.when, "Friday 5th of June 1987 at 11am to 5:30pm")

    def testAt(self):
        self.assertEqual(self.event.at.strip(), "11am")

    def testUpcomingDt(self):
        self.assertIsNone(self.event._upcoming_datetime_from)
        now = dt.datetime.now()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = SimpleEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date      = now.date(),
                                   time_from = earlier.time(),
                                   time_to   = dt.time.max)
        self.calendar.add_child(instance=nowEvent)
        self.assertIsNone(nowEvent._upcoming_datetime_from)
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        futureEvent = SimpleEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date  = tomorrow)
        self.calendar.add_child(instance=futureEvent)
        self.assertEqual(futureEvent._upcoming_datetime_from,
                         dt.datetime.combine(tomorrow, dt.time.max))


    def testPastDt(self):
        self.assertEqual(self.event._past_datetime_from,
                         dt.datetime(1987,6,5,11,0))
        now = dt.datetime.now()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = SimpleEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date      = now.date(),
                                   time_from = earlier.time(),
                                   time_to   = dt.time.max)
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent._past_datetime_from, earlier)
        tomorrow = dt.date.today() + dt.timedelta(days=1)
        futureEvent = SimpleEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date  = tomorrow)
        self.calendar.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent._past_datetime_from)

    def testGroup(self):
        self.assertIsNone(self.event.group)
        group = GroupPage(slug  = "runners",
                          title = "Runners")
        self.home.add_child(instance=group)
        race = SimpleEventPage(owner      = self.user,
                               slug       = "race",
                               title      = "Race",
                               date       = dt.date(2008, 6, 3))
        group.add_child(instance=race)
        self.assertEqual(race.group, group)
