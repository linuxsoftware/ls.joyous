# ------------------------------------------------------------------------------
# Test Signals
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from wagtail.core.models import Page
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from ls.joyous.models import RecurringEventPage, PostponementPage, GeneralCalendarPage
from ls.joyous.utils.recurrence import Recurrence, WEEKLY, MO, WE, FR
from ls.joyous.signals import identifyExpectantParent
from .testutils import freeze_timetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('j', 'j@joy.test', 's3(r3t')
        calendar = GeneralCalendarPage(owner = self.user,
                                       slug  = "events",
                                       title = "Events")
        self.home.add_child(instance=calendar)
        calendar.save_revision().publish()
        self.event = RecurringEventPage(slug   = "test-meeting",
                                        title  = "Test Meeting",
                                        repeat = Recurrence(dtstart=dt.date(1990,1,1),
                                                            freq=WEEKLY,
                                                            byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13,30),
                                        time_to   = dt.time(16))
        calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    @freeze_timetz("1991-01-01 15:00")
    def testIdentifyExpectantParent(self):
        postponement = PostponementPage()
        identifyExpectantParent(self.testIdentifyExpectantParent,
                                parent=self.event, page=postponement)
        self.assertEqual(postponement.overrides, self.event)
        self.assertEqual(postponement.except_date, dt.date(1991,1,2))
        self.assertEqual(postponement.date, dt.date(1991,1,3))
        self.assertEqual(postponement.postponement_title, "Test Meeting")
        self.assertIsNone(postponement.category)
        self.assertEqual(postponement.num_days, 1)
        self.assertEqual(postponement.time_from, dt.time(13,30))
        self.assertEqual(postponement.time_to, dt.time(16))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
