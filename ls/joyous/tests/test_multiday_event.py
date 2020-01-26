# ------------------------------------------------------------------------------
# Test Multiday Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import MultidayEventPage, MultidayEventPageForm
from freezegun import freeze_time
from .testutils import datetimetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
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
        events = MultidayEventPage.events.byDay(dt.date(2012,12,1),
                                                dt.date(2012,12,31))
        self.assertEqual(len(events), 31)
        evod = events[30]
        self.assertEqual(evod.date, dt.date(2012,12,31))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        events = MultidayEventPage.events.byDay(dt.date(2013,1,1),
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
        today = timezone.localdate()
        yesterday = today - dt.timedelta(1)
        nextWeek = today + dt.timedelta(7 - today.weekday())
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
        self.assertEqual(self.event.when, "Monday 31st of December 2012 at 11pm to "
                                          "Tuesday 1st of January 2013 at 3am")

    def testAt(self):
        self.assertEqual(self.event.at, "11pm")

    def testCurrentDt(self):
        self.assertIsNone(self.event._current_datetime_from)
        now = timezone.localtime()
        today = now.date()
        nextWeek = today + dt.timedelta(7 - today.weekday())
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = datetimetz(now.date(), dt.time.min)
        nowEvent = MultidayEventPage(owner = self.user,
                                     slug  = "now",
                                     title = "Now Event",
                                     date_from = earlier.date(),
                                     date_to   = nextWeek,
                                     time_from = earlier.time(),
                                     time_to   = dt.time(1))
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent._current_datetime_from, earlier)
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        futureEvent = MultidayEventPage(owner = self.user,
                                        slug  = "tomorrow",
                                        title = "Tomorrow's Event",
                                        date_from  = tomorrow,
                                        date_to    = tomorrow + dt.timedelta(2))
        self.calendar.add_child(instance=futureEvent)
        self.assertEqual(futureEvent._current_datetime_from,
                         datetimetz(tomorrow, dt.time.max))

    def testFutureDt(self):
        self.assertIsNone(self.event._future_datetime_from)
        now = timezone.localtime()
        today = now.date()
        nextWeek = today + dt.timedelta(7 - today.weekday())
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = datetimetz(now.date(), dt.time.min)
        nowEvent = MultidayEventPage(owner = self.user,
                                     slug  = "now",
                                     title = "Now Event",
                                     date_from = earlier.date(),
                                     date_to   = nextWeek,
                                     time_from = earlier.time(),
                                     time_to   = dt.time(1))
        self.calendar.add_child(instance=nowEvent)
        self.assertIsNone(nowEvent._future_datetime_from)
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        futureEvent = MultidayEventPage(owner = self.user,
                                        slug  = "tomorrow",
                                        title = "Tomorrow's Event",
                                        date_from  = tomorrow,
                                        date_to    = tomorrow + dt.timedelta(2))
        self.calendar.add_child(instance=futureEvent)
        self.assertEqual(futureEvent._future_datetime_from,
                         datetimetz(tomorrow, dt.time.max))

    def testPastDt(self):
        self.assertEqual(self.event._past_datetime_from,
                         datetimetz(2012,12,31,23,0))
        now = timezone.localtime()
        today = now.date()
        nextWeek = today + dt.timedelta(7 - today.weekday())
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = datetimetz(now.date(), dt.time.min)
        nowEvent = MultidayEventPage(owner = self.user,
                                     slug  = "now",
                                     title = "Now Event",
                                     date_from = earlier.date(),
                                     date_to   = nextWeek,
                                     time_from = earlier.time(),
                                     time_to   = dt.time(1))
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent._past_datetime_from, earlier)
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        futureEvent = MultidayEventPage(owner = self.user,
                                        slug  = "tomorrow",
                                        title = "Tomorrow's Event",
                                        date_from  = tomorrow,
                                        date_to    = tomorrow + dt.timedelta(2))
        self.calendar.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent._past_datetime_from)

    def testGroup(self):
        self.assertIsNone(self.event.group)

# ------------------------------------------------------------------------------
class TestTZ(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = MultidayEventPage(owner = self.user,
                                       slug  = "niuekulele2018",
                                       title = "Niuekulele Ukulele Music Festival",
                                       date_from = dt.date(2018,3,16),
                                       date_to   = dt.date(2018,3,20),
                                       tz = pytz.timezone("Pacific/Niue"))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByLocalDay(self):
        events = MultidayEventPage.events.byDay(dt.date(2018,3,1),
                                                dt.date(2018,3,31))
        self.assertEqual(len(events), 31)
        evod1 = events[16]
        self.assertEqual(evod1.date, dt.date(2018,3,17))
        self.assertEqual(len(evod1.days_events), 1)
        self.assertEqual(len(evod1.continuing_events), 0)
        evod5 = events[20]
        self.assertEqual(evod5.date, dt.date(2018,3,21))
        self.assertEqual(len(evod5.days_events), 0)
        self.assertEqual(len(evod5.continuing_events), 1)
        self.assertEqual(evod1.all_events[0], evod5.all_events[0])
        self.assertEqual(evod1.all_events[0].page, evod5.all_events[0].page)

    @freeze_time("2018-04-01")
    def testLocalWhen(self):
        self.assertEqual(self.event.when,
                         "Friday 16th of March to Wednesday 21st of March")

    def testLocalAt(self):
        self.assertEqual(self.event.at, "")

    @timezone.override("America/Los_Angeles")
    def testCurrentLocalDt(self):
        self.assertIsNone(self.event._current_datetime_from)

    @timezone.override("America/Los_Angeles")
    def testFutureLocalDt(self):
        self.assertIsNone(self.event._future_datetime_from)

    @timezone.override("Pacific/Auckland")
    def testPastLocalDt(self):
        when = self.event._past_datetime_from
        self.assertEqual(when.tzinfo.zone, "Pacific/Auckland")
        self.assertEqual(when.time(), dt.time.max)
        self.assertEqual(when.date(), dt.date(2018,3,17))

# ------------------------------------------------------------------------------
class TestPageForm(TestCase):
    Form = MultidayEventPage.get_edit_handler().get_form_class()

    def setUp(self):
        timezone.activate("Pacific/Auckland")

    def tearDown(self):
        timezone.deactivate()

    def testValidDates(self):
        form = self.Form({'slug':      "C2C",
                          'title':     "Coast to Coast",
                          'date_from': "2019-02-08",
                          'date_to':   "2019-02-09",
                          'time_from': "07:00:00",
                          'tz':        "Pacific/Auckland"})
        self.assertTrue(form.is_valid())
        self.assertDictEqual(form.errors, {})

    def testValidEndTimeBeforeStartTime(self):
        form = self.Form({'slug':      "ABC",
                          'title':     "AlphaBravoCharlie",
                          'date_from': "2012-03-08",
                          'date_to':   "2012-03-09",
                          'time_from': "13:00:00",
                          'time_to':   "12:00:00",
                          'tz':        "Pacific/Auckland"})
        self.assertTrue(form.is_valid())
        self.assertDictEqual(form.errors, {})

    def testEndDateBeforeStartDate(self):
        form = self.Form({'slug':      "Q2U",
                          'title':     "QWERTY2UIOPA",
                          'date_from': "2019-02-10",
                          'date_to':   "2019-02-09",
                          'time_from': "07:00:00",
                          'tz':        "Pacific/Auckland"})
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors,
                             {'date_to': ["Event cannot end before it starts"]})

    def testEndTimeBeforeStartTime(self):
        form = self.Form({'slug':      "AB",
                          'title':     "AlphaBravo",
                          'date_from': "2012-03-08",
                          'date_to':   "2012-03-08",
                          'time_from': "13:00:00",
                          'time_to':   "12:00:00",
                          'tz':        "Pacific/Auckland"})
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors,
                             {'time_to': ["Event cannot end before it starts"]})

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
