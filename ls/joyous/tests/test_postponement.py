# ------------------------------------------------------------------------------
# Test Postponement Page
# ------------------------------------------------------------------------------
import sys
import pytz
import datetime as dt
from django.test import RequestFactory
from django_bs_test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page
import wagtail.core.models
from wagtail.tests.utils.form_data import nested_form_data, rich_text
from ls.joyous.models import (GeneralCalendarPage, RecurringEventPage,
        CancellationPage, PostponementPage)
from ls.joyous.utils.recurrence import Recurrence, WEEKLY, MONTHLY, MO, TU, WE, FR
from .testutils import freeze_timetz, getPage, datetimetz

# ------------------------------------------------------------------------------
class Test(TestCase):
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
        title, page, url = evod.days_events[0]
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
        title, page, url = evod.days_events[0]
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

    @freeze_timetz("1990-10-11 16:29:00")
    def testStatusStarted(self):
        self.assertEqual(self.postponement.status, "started")
        self.assertEqual(self.postponement.status_text, "This event has started.")

    def testWhen(self):
        self.assertEqual(self.postponement.when, "Thursday 11th of October 1990 at 1pm to 4:30pm")

    def testWhatPostponed(self):
        self.assertEqual(self.postponement.what, "Postponed")

    def testWhatRescheduled(self):
        reschedule = PostponementPage(owner = self.user,
                                      overrides = self.event,
                                      except_date = dt.date(1991, 1, 7),
                                      date        = dt.date(1991, 1, 6),
                                      postponement_title = "Rescheduled")
        self.event.add_child(instance=reschedule)
        self.assertEqual(reschedule.what, "Rescheduled")

    def testWhatSameTime(self):
        change = PostponementPage(owner = self.user,
                                  overrides = self.event,
                                  except_date = dt.date(1991, 1, 7),
                                  date        = dt.date(1991, 1, 7),
                                  time_from   = dt.time(13,30),
                                  time_to     = dt.time(16),
                                  postponement_title = "Small Change")
        self.event.add_child(instance=change)
        self.assertIsNone(change.what)

    def testPostponedFrom(self):
        self.assertEqual(self.postponement.postponed_from,
                         "Wednesday 10th of October 1990")

    def testPostponedTo(self):
        self.assertEqual(self.postponement.postponed_to,
                         "Thursday 11th of October 1990")

    @freeze_timetz("2017-05-01")
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

    def testCurrentDt(self):
        self.assertIsNone(self.postponement._current_datetime_from)

    def testFutureDt(self):
        self.assertIsNone(self.postponement._future_datetime_from)

    def testPastDt(self):
        self.assertEqual(self.postponement._past_datetime_from,
                         datetimetz(1990,10,11,13,0))

    def testCancellationView(self):
        response = self.client.get("/events/test-meeting/1990-10-10-postponement/from/")
        select = response.soup.select
        self.assertEqual(response.status_code, 200)
        title = select('.joy-title h1')[0]
        self.assertEqual(title.string.strip(), "Meeting Postponed")
        details = select('.joy-ev-details .rich-text')[0]
        self.assertEqual(details.string.strip(),
                         "The meeting has been postponed until tomorrow")
        toLink = select('.joy-ev-to-when a')[0]
        self.assertEqual(toLink.string.strip(),
                         "Thursday 11th of October 1990 at 1pm to 4:30pm")
        self.assertEqual(toLink['href'],
                         "/events/test-meeting/1990-10-10-postponement/")

    def testCancellationUrl(self):
        self.assertEqual(self.postponement.getCancellationUrl(self.request),
                         "/events/test-meeting/1990-10-10-postponement/from/")
        was = wagtail.core.models.WAGTAIL_APPEND_SLASH
        wagtail.core.models.WAGTAIL_APPEND_SLASH = False
        self.assertEqual(self.postponement.getCancellationUrl(self.request),
                         "/events/test-meeting/1990-10-10-postponement/from")
        wagtail.core.models.WAGTAIL_APPEND_SLASH = was

# ------------------------------------------------------------------------------
class TestTZ(TestCase):
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
        self.assertEqual(self.postponement.local_title,
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
        title, page, url = evod0.days_events[0]
        self.assertEqual(title, "Delayed Meeting")
        self.assertIs(type(page), PostponementPage)
        evod1 = events[11]
        self.assertEqual(evod1.date, dt.date(1990,10,12))
        self.assertEqual(len(evod1.days_events), 0)
        self.assertEqual(len(evod1.continuing_events), 1)
        title, page, url = evod1.continuing_events[0]
        self.assertEqual(title, "Delayed Meeting")
        self.assertIs(type(page), PostponementPage)

# ------------------------------------------------------------------------------
class TestPageForm(TestCase):
    Form = PostponementPage.get_edit_handler().get_form_class()

    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@bar.test', 's3(r3t')
        self.calendar = GeneralCalendarPage(owner = self.user,
                                            slug  = "events",
                                            title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "committee-meeting",
                                        title     = "Committee Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(2017,1,1),
                                                               freq=MONTHLY,
                                                               byweekday=[MO(1), MO(3)]),
                                        time_from = dt.time(13),
                                        time_to   = dt.time(15,30))
        self.calendar.add_child(instance=self.event)

    def testValidEndTimeBeforeStartTime(self):
        page = PostponementPage(owner=self.user)
        form = self.Form({'overrides':    self.event,
                          'except_date':  "2017-02-06",
                          'date':         "2017-02-07",
                          'time_from':    "13:00:00",
                          'time_to':      "16:00:00",
                          'cancellation_title': "Meeting postponed",
                          'cancellation_details': 
                                  rich_text("The meeting has been postponed until tomorrow"),
                          'postponement_title': "Committee Meeting"},
                          instance=page,
                          parent_page=self.event)
        self.assertTrue(form.is_valid())
        self.assertDictEqual(form.errors, {})

    def testEndTimeBeforeStartTime(self):
        page = PostponementPage(owner=self.user)
        form = self.Form({'overrides':    self.event,
                          'except_date':  "2017-02-06",
                          'date':         "2017-02-07",
                          'time_from':    "13:00:00",
                          'time_to':      "04:00:00",
                          'cancellation_title': "Meeting postponed",
                          'cancellation_details': 
                                  rich_text("The meeting has been postponed until tomorrow"),
                          'postponement_title': "Committee Meeting"},
                          instance=page,
                          parent_page=self.event)
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors,
                             {'time_to': ['Event cannot end before it starts']})

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
