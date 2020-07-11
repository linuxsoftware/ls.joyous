# ------------------------------------------------------------------------------
# Test Reschedule Multiday Event Page
# ------------------------------------------------------------------------------
import sys
import pytz
import datetime as dt
from django.test import RequestFactory
from django_bs_test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page
from wagtail.tests.utils.form_data import nested_form_data, rich_text
from ls.joyous.models import (GeneralCalendarPage,
        MultidayRecurringEventPage, RescheduleMultidayEventPage)
from ls.joyous.utils.recurrence import Recurrence, WEEKLY, MONTHLY, MO, TU, WE, FR
from .testutils import freeze_timetz, getPage, datetimetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('j', 'j@joy.test', 's3(r3t')
        self.calendar = GeneralCalendarPage(owner = self.user,
                                            slug  = "events",
                                            title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = MultidayRecurringEventPage(slug = "test-session",
                                        title = "Test Session",
                                        repeat = Recurrence(dtstart=dt.date(1990,1,2),
                                                            freq=WEEKLY,
                                                            byweekday=[TU],
                                                            until=dt.date(1990,3,29)),
                                        num_days  = 3,
                                        time_from = dt.time(10),
                                        time_to   = dt.time(16,30))
        self.calendar.add_child(instance=self.event)
        self.postponement = RescheduleMultidayEventPage(owner = self.user,
                                             overrides = self.event,
                                             except_date = dt.date(1990,1,9),
                                             postponement_title   = "Delayed Start Session",
                                             date      = dt.date(1990,1,9),
                                             num_days  = 3,
                                             time_from = dt.time(13),
                                             time_to   = dt.time(19,30))
        self.event.add_child(instance=self.postponement)
        self.postponement.save_revision().publish()

    def testWhat(self):
        self.assertEqual(self.postponement.what, "Postponed")

    def testWhen(self):
        self.assertEqual(self.postponement.when,
                         "Tuesday 9th of January 1990 for 3 days "
                         "starting at 1pm finishing at 7:30pm")

    @freeze_timetz("1990-02-08 16:00")
    def testEventStatus(self):
        self.assertEqual(self.event.status, "started")
        postponement = RescheduleMultidayEventPage(owner = self.user,
                                             overrides = self.event,
                                             except_date = dt.date(1990,2,6),
                                             postponement_title   = "Quick Session",
                                             date      = dt.date(1990,2,6),
                                             num_days  = 1,
                                             time_from = dt.time(10),
                                             time_to   = dt.time(16,30))
        self.event.add_child(instance=postponement)
        postponement.save_revision().publish()
        self.assertIsNone(self.event.status)

    def testRemoveContentPanels(self):
        RescheduleMultidayEventPage._removeContentPanels(["tz", "location"])
        RescheduleMultidayEventPage._removeContentPanels("website")
        removed = ("tz", "location", "website")
        panels = RescheduleMultidayEventPage.content_panels
        self.assertFalse(any(field in removed
                             for panel in panels
                             for field in panel.required_fields()))

    @freeze_timetz("1990-01-11 18:00")
    def testStatus(self):
        self.assertEqual(self.postponement.status, "started")
        self.assertEqual(self.postponement.status_text, "This event has started.")

    def testAt(self):
        self.assertEqual(self.postponement.at.strip(), "1pm")

    @freeze_timetz("1990-01-11 18:00")
    def testCurrentDt(self):
        self.assertEqual(self.postponement._current_datetime_from,
                         datetimetz(1990,1,9,13,0))

    @freeze_timetz("1990-01-11 18:00")
    def testFutureDt(self):
        self.assertIsNone(self.postponement._future_datetime_from)

    def testPastDt(self):
        self.assertEqual(self.postponement._past_datetime_from,
                         datetimetz(1990,1,9,13,0))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
