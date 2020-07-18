# ------------------------------------------------------------------------------
# Test Extra Info Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import translation
from django.utils import timezone
from wagtail.core.models import Page
from wagtail.tests.utils.form_data import nested_form_data, rich_text
from ls.joyous.models import CalendarPage
from ls.joyous.models import RecurringEventPage, MultidayRecurringEventPage
from ls.joyous.models import ExtraInfoPage
from ls.joyous.utils.recurrence import Recurrence, WEEKLY, MO, WE, FR
from .testutils import datetimetz, freeze_timetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@bar.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "test-meeting",
                                        title     = "Test Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(1988,1,1),
                                                               freq=WEEKLY,
                                                               byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13),
                                        time_to   = dt.time(15,30))
        self.calendar.add_child(instance=self.event)
        self.info = ExtraInfoPage(owner = self.user,
                                  overrides = self.event,
                                  except_date = dt.date(1988,11,11),
                                  extra_title = "System Demo",
                                  extra_information = "<h3>System Demo</h3>")
        self.event.add_child(instance=self.info)
        self.info.save_revision().publish()

    def testGetEventsByDay(self):
        events = RecurringEventPage.events.byDay(dt.date(1988,11,1),
                                                 dt.date(1988,11,30))
        self.assertEqual(len(events), 30)
        evod = events[10]
        self.assertEqual(evod.date, dt.date(1988,11,11))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        title, page, url = evod.days_events[0]
        self.assertEqual(title, "System Demo")
        self.assertIs(type(page), ExtraInfoPage)

    def testStatus(self):
        self.assertEqual(self.info.status, "finished")
        self.assertEqual(self.info.status_text, "This event has finished.")
        now = timezone.localtime()
        myday = now.date() + dt.timedelta(days=1)
        friday = myday + dt.timedelta(days=(4-myday.weekday())%7)
        futureInfo = ExtraInfoPage(owner = self.user,
                                   overrides = self.event,
                                   except_date = friday,
                                   extra_title = "It's Friday",
                                   extra_information = "Special")
        self.event.add_child(instance=futureInfo)
        self.assertIsNone(futureInfo.status)
        self.assertEqual(futureInfo.status_text, "")

    @freeze_timetz("1988-11-11 14:00:00")
    def testStatusStarted(self):
        self.assertEqual(self.info.status, "started")
        self.assertEqual(self.info.status_text, "This event has started.")

    def testWhen(self):
        self.assertEqual(self.info.when, "Friday 11th of November 1988 at 1pm to 3:30pm")

    def testAt(self):
        self.assertEqual(self.info.at.strip(), "1pm")

    def testCurrentDt(self):
        self.assertIsNone(self.info._current_datetime_from)

    def testFutureDt(self):
        self.assertIsNone(self.info._future_datetime_from)

    def testPastDt(self):
        self.assertEqual(self.info._past_datetime_from,
                         datetimetz(1988,11,11,13,0))

    def testNeverOccursOn(self):
        info = ExtraInfoPage(owner = self.user,
                             overrides = self.event,
                             except_date = dt.date(1988,3,1),
                             extra_title = "Tuesday",
                             extra_information = "Standard")
        self.event.add_child(instance=info)
        self.assertIsNone(info._current_datetime_from)
        self.assertIsNone(info._future_datetime_from)
        self.assertIsNone(info._past_datetime_from)

    def testGroup(self):
        self.assertIsNone(self.info.group)

    def testOverridesRepeat(self):
        self.assertEqual(self.info.overrides_repeat, self.event.repeat)

# ------------------------------------------------------------------------------
class TestMultiday(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@bar.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "schedule",
                                     title = "Schedule")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = MultidayRecurringEventPage(slug = "test-session",
                                                title = "Test Session",
                                                repeat = Recurrence(
                                                        dtstart=dt.date(2018,1,8),
                                                        freq=WEEKLY,
                                                        byweekday=[MO],
                                                        until=dt.date(2018,4,25)),
                                                num_days  = 3,
                                                time_from = dt.time(10),
                                                time_to   = dt.time(12,30))
        self.calendar.add_child(instance=self.event)
        self.info = ExtraInfoPage(owner = self.user,
                                  overrides = self.event,
                                  except_date = dt.date(2018,2,12),
                                  extra_title = "System Demo",
                                  extra_information = "<h3>System Demo</h3>")
        self.event.add_child(instance=self.info)
        self.info.save_revision().publish()

    def testStatusFinished(self):
        self.assertEqual(self.info.status, "finished")
        self.assertEqual(self.info.status_text, "This event has finished.")

    @freeze_timetz("2018-02-13 14:00:00")
    def testStatusStarted(self):
        self.assertEqual(self.info.status, "started")
        self.assertEqual(self.info.status_text, "This event has started.")

    def testWhen(self):
        self.assertEqual(self.info.when,
                         "Monday 12th of February 2018 for 3 days "
                         "starting at 10am finishing at 12:30pm")

    def testAt(self):
        self.assertEqual(self.info.at.strip(), "10am")

    @freeze_timetz("2018-02-13 17:00:00")
    def testCurrentDt(self):
        self.assertEqual(self.info._current_datetime_from,
                         datetimetz(2018,2,12,10,0))

    @freeze_timetz("2018-02-13 14:00:00")
    def testFutureDt(self):
        self.assertIsNone(self.info._future_datetime_from)

    def testPastDt(self):
        self.assertEqual(self.info._past_datetime_from,
                         datetimetz(2018,2,12,10,0))

# ------------------------------------------------------------------------------
class TestPageForm(TestCase):
    Form = ExtraInfoPage.get_edit_handler().get_form_class()

    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@bar.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "test-meeting",
                                        title     = "Test Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(1988,1,1),
                                                               freq=WEEKLY,
                                                               byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13),
                                        time_to   = dt.time(15,30))
        self.calendar.add_child(instance=self.event)
        self.info = ExtraInfoPage(owner = self.user,
                                  overrides = self.event,
                                  except_date = dt.date(1999,1,5),
                                  extra_title = "Fri-day",
                                  extra_information = "Special Friday")
        self.event.add_child(instance=self.info)
        self.info.save_revision().publish()

    def testExceptionAlreadyExists(self):
        page = ExtraInfoPage(owner=self.user)
        form = self.Form({'overrides':         self.event,
                          'except_date':       "1999-01-05",
                          'extra_title':       "It's Friday",
                          'extra_information': rich_text("Special Special Friday")},
                          instance=page,
                          parent_page=self.event)
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors,
                             {'except_date': ['That date already has extra information']})

# ------------------------------------------------------------------------------
class TestPageFormDeutsche(TestCase):
    Form = ExtraInfoPage.get_edit_handler().get_form_class()

    def setUp(self):
        translation.activate('de')
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@bar.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "ereignisse",
                                     title = "Ereignisse")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "meeting",
                                        title     = "Testen Sie Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(1988,1,1),
                                                               freq=WEEKLY,
                                                               byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13),
                                        time_to   = dt.time(15,30))
        self.calendar.add_child(instance=self.event)
        self.info = ExtraInfoPage(owner = self.user,
                                  overrides = self.event,
                                  except_date = dt.date(1999,1,5),
                                  extra_title = "Freitag",
                                  extra_information = "Besonderer Freitag")
        self.event.add_child(instance=self.info)
        self.info.save_revision().publish()

    def tearDown(self):
        translation.deactivate()

    def testExceptionAlreadyExists(self):
        page = ExtraInfoPage(owner=self.user)
        form = self.Form({'overrides':         self.event,
                          'except_date':       "1999-01-05",
                          'extra_title':       "Es ist Freitag",
                          'extra_information': rich_text("Besonderer spezieller Freitag")},
                          instance=page,
                          parent_page=self.event)
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors,
                             {'except_date': ['Dieses Datum enthält bereits zusätzliche information']})

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
