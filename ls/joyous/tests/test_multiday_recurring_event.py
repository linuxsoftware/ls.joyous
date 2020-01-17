# ------------------------------------------------------------------------------
# Test Multiday Recurring Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
import calendar
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page, PageViewRestriction
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import DAILY, WEEKLY, YEARLY
from ls.joyous.utils.recurrence import SA, MO, TU, TH, FR
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import MultidayRecurringEventPage, ExtraInfoPage
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

    def testNextOn(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        oldEvent = MultidayRecurringEventPage(
                               owner = self.user,
                               slug  = "same-old-thing",
                               title = "Same Ol'",
                               repeat = Recurrence(dtstart=dt.date(1971,1,1),
                                                   until=dt.date(1982,1,1),
                                                   freq=WEEKLY,
                                                   byweekday=SA(1)),
                               num_days  = 2)
        self.calendar.add_child(instance=oldEvent)
        oldEvent.save_revision().publish()
        with freeze_timetz("1974-08-01 17:00:00"):
            self.assertEqual(oldEvent.next_date, dt.date(1974, 8, 3))
            self.assertEqual(oldEvent._nextOn(request), "Saturday 3rd of August ")
        with freeze_timetz("1982-01-01 17:00:00"):
            self.assertIsNone(oldEvent.next_date)
            self.assertEqual(oldEvent._nextOn(request), None)

    def testWhen(self):
        self.assertEqual(self.event.when,
                         "The first Friday of August for 3 days "
                         "starting at 6pm finishing at 4:30pm")

    def testAt(self):
        self.assertEqual(self.event.at.strip(), "6pm")

    @freeze_timetz("2035-04-03 10:00:00")
    def testPrevDate(self):
        self.assertEqual(self.event.prev_date, dt.date(2034, 8, 4))

    @freeze_timetz("2018-04-03 10:00:00")
    def testFutureExceptions(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        info2018 = ExtraInfoPage(owner = self.user,
                                 overrides = self.event,
                                 except_date = dt.date(2018, 8, 3),
                                 extra_title = "Team Retreat 2018",
                                 extra_information = "Weekend at Bernie's")
        self.event.add_child(instance=info2018)
        exceptions = self.event._futureExceptions(request)
        self.assertEqual(len(exceptions), 1)
        info = exceptions[0]
        self.assertEqual(info.slug, "2018-08-03-extra-info")
        self.assertEqual(info.extra_title, "Team Retreat 2018")

    @freeze_timetz("2018-08-04 02:00:00")
    def testPastExcludeExtraInfo(self):
        info2018 = ExtraInfoPage(owner = self.user,
                                 overrides = self.event,
                                 except_date = dt.date(2018, 8, 3),
                                 extra_title = "Team Retreat 2018",
                                 extra_information = "Weekend at Bernie's")
        self.event.add_child(instance=info2018)
        before = self.event._past_datetime_from
        self.assertEqual(before, datetimetz(2017, 8, 4, 18))

# ------------------------------------------------------------------------------
class Test40Day(TestCase):
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
                               slug  = "ice-festival",
                               title = "Ice Festival",
                               repeat = Recurrence(dtstart=dt.date(2000,12,25),
                                                   until=dt.date(2020,1,31),
                                                   freq=YEARLY,
                                                   bymonth=12,
                                                   byweekday=MO(4)),
                               num_days  = 40)
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByDay(self):
        events = MultidayRecurringEventPage.events.byDay(dt.date(2020,1,1),
                                                         dt.date(2020,1,31))
        self.assertEqual(len(events), 31)
        evod = events[0]
        self.assertEqual(evod.date, dt.date(2020,1,1))
        self.assertEqual(len(evod.days_events), 0)
        self.assertEqual(len(evod.continuing_events), 1)
        thisEvent = evod.continuing_events[0]
        self.assertEqual(thisEvent.title, "Ice Festival")
        evod = events[10]
        self.assertEqual(evod.date, dt.date(2020,1,11))
        self.assertEqual(len(evod.continuing_events), 1)
        thisEvent = evod.continuing_events[0]
        self.assertEqual(thisEvent.title, "Ice Festival")

    def testStatus(self):
        with freeze_timetz("2019-12-20 13:00:00"):
            self.assertEqual(self.event.status_text, "")
        with freeze_timetz("2020-01-02 13:00:00"):
            self.assertEqual(self.event.status_text, "This event has started.")
        with freeze_timetz("2020-02-03 17:00:00"):
            self.assertEqual(self.event.status_text, "These events have finished.")

    def testAt(self):
        self.assertEqual(self.event.at.strip(), "")

    @freeze_timetz("2035-04-03 10:00:00")
    def testNextDate(self):
        self.assertEqual(self.event.next_date, None)

    @freeze_timetz("2035-04-03 10:00:00")
    def testPrevDate(self):
        self.assertEqual(self.event.prev_date, dt.date(2019, 12, 23))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
