# ------------------------------------------------------------------------------
# Test Multiday Recurring Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
import calendar
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page, PageViewRestriction
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import DAILY, WEEKLY, MONTHLY, YEARLY
from ls.joyous.utils.recurrence import SA, TU, TH, FR
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import MultidayRecurringEventPage
from .testutils import datetimetz, freeze_timetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        Page.objects.get(slug='home').add_child(instance=self.calendar)
        self.calendar.save()
        self.calendar.save_revision().publish()
        self.event = MultidayRecurringEventPage(
                               owner = self.user,
                               slug  = "team-retreat",
                               title = "Team Retreat",
                               repeat = Recurrence(dtstart=dt.date(2000,1,1),
                                                   freq=YEARLY,
                                                   bymonth=8,
                                                   byweekday=FR(1)),
                               num_days  = 3,
                               time_from = dt.time(18),
                               time_to   = dt.time(16,30))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByDay(self):
        events = MultidayRecurringEventPage.events.byDay(dt.date(2017,8,1),
                                                         dt.date(2017,8,31))
        self.assertEqual(len(events), 31)
        evod = events[3]
        self.assertEqual(evod.date, dt.date(2017,8,4))
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        evod = events[4]
        self.assertEqual(evod.date, dt.date(2017,8,5))
        self.assertEqual(len(evod.days_events), 0)
        self.assertEqual(len(evod.continuing_events), 1)
        evod = events[5]
        self.assertEqual(evod.date, dt.date(2017,8,6))
        self.assertEqual(len(evod.days_events), 0)
        self.assertEqual(len(evod.continuing_events), 1)

    def testStatus(self):
        with freeze_timetz("2014-08-01 17:00:00"):
            self.assertEqual(self.event.status_text, "")
        with freeze_timetz("2014-08-02 13:00:00"):
            self.assertEqual(self.event.status_text, "This event has started.")
        with freeze_timetz("2014-08-03 15:00:00"):
            self.assertEqual(self.event.status_text, "This event has started.")
        with freeze_timetz("2014-08-03 17:00:00"):
            self.assertEqual(self.event.status_text, "")

    def testWhen(self):
        self.assertEqual(self.event.when, "The first Friday of August for 3 days at 6pm to 4:30pm")

    def testAt(self):
        self.assertEqual(self.event.at.strip(), "6pm")

    @freeze_timetz("2035-04-03 10:00:00")
    def testPrevDate(self):
        self.assertEqual(self.event.prev_date, dt.date(2034, 8, 4))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
