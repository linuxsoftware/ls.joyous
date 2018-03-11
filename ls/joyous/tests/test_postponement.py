# ------------------------------------------------------------------------------
# Test Postponement Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase
from django.contrib.auth.models import User
from wagtail.core.models import Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import RecurringEventPage
from ls.joyous.models.events import PostponementPage
from ls.joyous.models.events import CancellationPage
from ls.joyous.recurrence import Recurrence, WEEKLY, MO, WE, FR


class TestPostponement(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('j', 'j@ok.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug   = "test-meeting",
                                        title  = "Test Meeting",
                                        repeat = Recurrence(dtstart=dt.datetime(1990,1,1),
                                                            freq=WEEKLY,
                                                            byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13,30),
                                        time_to   = dt.time(16))
        self.calendar.add_child(instance=self.event)
        self.postponement = PostponementPage(owner = self.user,
                                             slug  = "1990-10-10-postponement",
                                             title = "Postponement for Wednesday 10th of October",
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
        events = RecurringEventPage.getEventsByDay(dt.date(1990,10,1),
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

        events = PostponementPage.getEventsByDay(dt.date(1990,10,1),
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
        now = dt.datetime.now()
        myday = now.date() + dt.timedelta(1)
        friday = myday + dt.timedelta(days=(4-myday.weekday())%7)
        futureEvent = PostponementPage(owner = self.user,
                                       slug  = "fri-postponement",
                                       title = "Postponement for Friday",
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
