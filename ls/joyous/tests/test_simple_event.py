# ------------------------------------------------------------------------------
# Test Simple Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import SimpleEventPage
from ls.joyous.models.groups import get_group_model
from .testutils import datetimetz
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
        now = timezone.localtime()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = SimpleEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date      = now.date(),
                                   time_from = earlier.time(),
                                   time_to   = dt.time.max)
        self.assertEqual(nowEvent.status, "started")
        self.assertEqual(nowEvent.status_text, "This event has started.")
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        futureEvent = SimpleEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date  = tomorrow)
        self.calendar.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent.status)
        self.assertEqual(futureEvent.status_text, "")

    def testWhen(self):
        self.assertEqual(self.event.when,
                         "Friday 5th of June 1987 at 11am to 5:30pm")

    def testAt(self):
        self.assertEqual(self.event.at, "11am")

    def testUpcomingDt(self):
        self.assertIsNone(self.event._upcoming_datetime_from)
        now = timezone.localtime()
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
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        futureEvent = SimpleEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date  = tomorrow)
        self.calendar.add_child(instance=futureEvent)
        self.assertEqual(futureEvent._upcoming_datetime_from,
                         datetimetz(tomorrow, dt.time.max))

    def testPastDt(self):
        self.assertEqual(self.event._past_datetime_from, datetimetz(1987,6,5,11,0))
        now = timezone.localtime()
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
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
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
        race = SimpleEventPage(owner = self.user,
                               slug  = "race",
                               title = "Race",
                               date  = dt.date(2008, 6, 3))
        group.add_child(instance=race)
        self.assertEqual(race.group, group)


class TestSimpleEventTZ(TestCase):
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
                                     date   = dt.date(1987,6,5),
                                     time_from = dt.time(11),
                                     time_to   = dt.time(17,30),
                                     tz = pytz.timezone("Australia/Sydney"))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    @timezone.override("America/Los_Angeles")
    def testGetEventsByLocalDay(self):
        events = SimpleEventPage.getEventsByDay(dt.date(1987,6,1),
                                                dt.date(1987,6,30))
        self.assertEqual(len(events), 30)
        evod1 = events[3]
        self.assertEqual(evod1.date, dt.date(1987,6,4))
        self.assertEqual(len(evod1.days_events), 1)
        self.assertEqual(len(evod1.continuing_events), 0)
        evod2 = events[4]
        self.assertEqual(evod2.date, dt.date(1987,6,5))
        self.assertEqual(len(evod2.days_events), 0)
        self.assertEqual(len(evod2.continuing_events), 1)
        self.assertEqual(evod1.all_events[0], evod2.all_events[0])
        self.assertIs(evod1.all_events[0].page, evod2.all_events[0].page)

    @timezone.override("America/Los_Angeles")
    def testLocalWhen(self):
        self.assertEqual(self.event.when,
                         "Thursday 4th of June 1987 at 6pm to Friday 5th of June 1987 at 12:30am")

    @timezone.override("America/Los_Angeles")
    def testLocalAt(self):
        self.assertEqual(self.event.at, "6pm")

    @timezone.override("America/Los_Angeles")
    def testUpcomingLocalDt(self):
        self.assertIsNone(self.event._upcoming_datetime_from)

    @timezone.override("America/Los_Angeles")
    def testPastLocalDt(self):
        when = self.event._past_datetime_from
        self.assertEqual(when.tzinfo.zone, "America/Los_Angeles")
        self.assertEqual(when.time(), dt.time(18))
        self.assertEqual(when.date(), dt.date(1987,6,4))

    @timezone.override("Pacific/Tongatapu")
    def testGetEventsAcrossDateline(self):
        showDay = SimpleEventPage(owner = self.user,
                                  slug  = "tamakautoga-village-show-day",
                                  title = "Tamakautoga Village Show Day",
                                  date      = dt.date(2016,7,30),
                                  tz = pytz.timezone("Pacific/Niue"))
        self.calendar.add_child(instance=showDay)
        events = SimpleEventPage.getEventsByDay(dt.date(2016,7,31),
                                                dt.date(2016,7,31))
        self.assertEqual(len(events[0].days_events), 1)
        self.assertEqual(len(events[0].continuing_events), 0)
        event = events[0].days_events[0].page
        self.assertEqual(event.at, "")
        self.assertEqual(event.when, "Sunday 31st of July 2016")
