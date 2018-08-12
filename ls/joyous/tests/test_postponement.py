# ------------------------------------------------------------------------------
# Test Postponement Page
# ------------------------------------------------------------------------------
import sys
import pytz
import datetime as dt
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page
from ls.joyous.models.calendar import GeneralCalendarPage
from ls.joyous.models.events import RecurringEventPage
from ls.joyous.models.events import PostponementPage
from ls.joyous.models.events import CancellationPage
from ls.joyous.utils.recurrence import Recurrence, WEEKLY, MO, WE, FR


class TestPostponement(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('j', 'j@joy.test', 's3(r3t')
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.calendar = GeneralCalendarPage(owner = self.user,
                                            slug  = "events",
                                            title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug   = "test-meeting",
                                        title  = "Test Meeting",
                                        repeat = Recurrence(dtstart=dt.date(1990,1,1),
                                                            freq=WEEKLY,
                                                            byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13,30),
                                        time_to   = dt.time(16))
        self.calendar.add_child(instance=self.event)
        self.postponement = PostponementPage(owner = self.user,
                                             overrides = self.event,
                                             except_date = dt.date(1990,10,10),
                                             cancellation_title   = "Meeting Postponed",
                                             cancellation_details =
                                                 "The meeting has been postponed until tomorrow",
                                             postponement_title   = "A Meeting",
                                             date      = dt.date(1990,10,11),
                                             time_from = dt.time(13),
                                             time_to   = dt.time(16,30),
                                             details   = "Yes a test meeting on a Thursday")
        self.event.add_child(instance=self.postponement)
        self.postponement.save_revision().publish()

    def testGetEventsByDay(self):
        events = RecurringEventPage.events.byDay(dt.date(1990,10,1),
                                                 dt.date(1990,10,31))
        self.assertEqual(len(events), 31)
        evod = events[9]
        self.assertEqual(evod.date, dt.date(1990,10,10))
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        title, page = evod.days_events[0]
        self.assertEqual(title, "Meeting Postponed")
        self.assertIs(type(page), CancellationPage)
        self.assertIs(type(page.postponementpage), PostponementPage)

        events = PostponementPage.events.byDay(dt.date(1990,10,1),
                                               dt.date(1990,10,31))
        self.assertEqual(len(events), 31)
        evod = events[10]
        self.assertEqual(evod.date, dt.date(1990,10,11))
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        title, page = evod.days_events[0]
        self.assertEqual(title, "A Meeting")
        self.assertIs(type(page), PostponementPage)

    def testStatus(self):
        self.assertEqual(self.postponement.status, "finished")
        self.assertEqual(self.postponement.status_text, "This event has finished.")
        now = timezone.localtime()
        myday = now.date() + dt.timedelta(1)
        friday = myday + dt.timedelta(days=(4-myday.weekday())%7)
        futureEvent = PostponementPage(owner = self.user,
                                       overrides = self.event,
                                       except_date = friday,
                                       cancellation_title   = "",
                                       cancellation_details = "",
                                       postponement_title   = "Tuesday Meeting",
                                       date      = friday + dt.timedelta(days=4),
                                       time_from = dt.time(13,30),
                                       time_to   = dt.time(16),
                                       details   = "The meeting postponed from last Friday")
        self.event.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent.status)
        self.assertEqual(futureEvent.status_text, "")

    def testWhen(self):
        self.assertEqual(self.postponement.when, "Thursday 11th of October 1990 at 1pm to 4:30pm")

    def testAt(self):
        self.assertEqual(self.postponement.at.strip(), "1pm")
        nextDate = self.event.next_date
        newDate  = nextDate + dt.timedelta(1)
        reschedule = PostponementPage(owner = self.user,
                                      overrides = self.event,
                                      except_date = nextDate,
                                      cancellation_title   = "",
                                      cancellation_details = "",
                                      postponement_title   = "Early Meeting",
                                      date      = newDate,
                                      time_from = dt.time(8,30),
                                      time_to   = dt.time(11),
                                      details   = "The meeting will be held early tomorrow")
        self.event.add_child(instance=reschedule)
        nextOn = self.event._nextOn(self.request)
        url = "/events/test-meeting/{}-postponement/".format(nextDate)
        self.assertEqual(nextOn[:76], '<a class="inline-link" href="{}">'.format(url))
        self.assertEqual(nextOn[-4:], '</a>')
        parts = nextOn[76:-4].split()
        self.assertEqual(len(parts), 6)
        self.assertEqual(parts[0], "{:%A}".format(newDate))
        self.assertEqual(int(parts[1][:-2]), newDate.day)
        self.assertIn(parts[1][-2:], ["st", "nd", "rd", "th"])
        self.assertEqual(parts[2], "of")
        self.assertEqual(parts[3], "{:%B}".format(newDate))
        self.assertEqual(parts[4], "at")
        self.assertEqual(parts[5], "8:30am")


class TestPostponementTZ(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('j', 'j@joy.test', 's3(r3t')
        self.calendar = GeneralCalendarPage(owner = self.user,
                                            slug  = "events",
                                            title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug   = "test-meeting",
                                        title  = "Test Meeting",
                                        repeat = Recurrence(dtstart=dt.date(1990,1,1),
                                                            freq=WEEKLY,
                                                            byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13,30),
                                        time_to   = dt.time(16),
                                        tz = pytz.timezone("US/Eastern"))
        self.calendar.add_child(instance=self.event)
        self.postponement = PostponementPage(owner = self.user,
                                             overrides = self.event,
                                             postponement_title = "Delayed Meeting",
                                             except_date = dt.date(1990,10,10),
                                             date      = dt.date(1990,10,11),
                                             time_from = dt.time(13),
                                             time_to   = dt.time(16,30))
        self.event.add_child(instance=self.postponement)
        self.postponement.save_revision().publish()

    @timezone.override("Pacific/Auckland")
    def testLocalTitle(self):
        self.assertEqual(self.postponement.title,
                         "Postponement for Wednesday 10th of October 1990")
        self.assertEqual(self.postponement.localTitle,
                         "Postponement for Thursday 11th of October 1990")

    @timezone.override("Asia/Colombo")
    def testGetEventsByDay(self):
        events = PostponementPage.events.byDay(dt.date(1990,10,1),
                                               dt.date(1990,10,31))
        self.assertEqual(len(events), 31)
        evod0 = events[10]
        self.assertEqual(evod0.date, dt.date(1990,10,11))
        self.assertEqual(len(evod0.days_events), 1)
        self.assertEqual(len(evod0.continuing_events), 0)
        title, page = evod0.days_events[0]
        self.assertEqual(title, "Delayed Meeting")
        self.assertIs(type(page), PostponementPage)
        evod1 = events[11]
        self.assertEqual(evod1.date, dt.date(1990,10,12))
        self.assertEqual(len(evod1.days_events), 0)
        self.assertEqual(len(evod1.continuing_events), 1)
        title, page = evod1.continuing_events[0]
        self.assertEqual(title, "Delayed Meeting")
        self.assertIs(type(page), PostponementPage)
