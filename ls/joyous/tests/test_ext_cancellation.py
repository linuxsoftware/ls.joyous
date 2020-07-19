# ------------------------------------------------------------------------------
# Test Extended Cancellation Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from itertools import islice
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page, PageViewRestriction
from wagtail.tests.utils.form_data import rich_text
from ls.joyous.models import CalendarPage
from ls.joyous.models import RecurringEventPage
from ls.joyous.models import ExtCancellationPage
from ls.joyous.utils.recurrence import Recurrence, WEEKLY, MONTHLY, MO, WE, FR
from .testutils import freeze_timetz, datetimetz


# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "test-meeting",
                                        title     = "Test Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(2010,1,1),
                                                               freq=WEEKLY,
                                                               byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13),
                                        time_to   = dt.time(14,30))
        self.calendar.add_child(instance=self.event)
        self.shutdown = ExtCancellationPage(owner = self.user,
                                            overrides = self.event,
                                            cancelled_from_date=dt.date(2020,3,20),
                                            cancelled_to_date=dt.date(2020,6,1),
                                            cancellation_title="No Meeting during Shutdown")
        self.event.add_child(instance=self.shutdown)
        self.shutdown.save_revision().publish()

    @freeze_timetz("2020-10-11")
    def testInit(self):
        self.assertEqual(self.shutdown.title,
                         "Cancellation from Friday 20th of March to Monday 1st of June")
        self.assertEqual(self.shutdown.local_title,
                         "Cancellation from Friday 20th of March to Monday 1st of June")
        self.assertEqual(self.shutdown.slug,  "2020-03-20-2020-06-01-cancellation")

    def testGetEventsByDay(self):
        shutdown0 = ExtCancellationPage(owner = self.user,
                                        overrides = self.event,
                                        cancelled_from_date=dt.date(2020,3,2),
                                        cancelled_to_date=dt.date(2020,3,6))
        self.event.add_child(instance=shutdown0)
        shutdown0.save_revision().publish()
        events = RecurringEventPage.events.byDay(dt.date(2020,3,1),
                                                 dt.date(2020,3,31))
        self.assertEqual(len(events), 31)
        evod = events[1]
        self.assertEqual(evod.date, dt.date(2020,3,2))
        self.assertEqual(len(evod.days_events), 0)
        self.assertEqual(len(evod.continuing_events), 0)
        evod = events[8]
        self.assertEqual(evod.date, dt.date(2020,3,9))
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        title, page, url = evod.days_events[0]
        self.assertEqual(title, "Test Meeting")
        evod = events[19]
        self.assertEqual(evod.date, dt.date(2020,3,20))
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        title, page, url = evod.days_events[0]
        self.assertEqual(title, "No Meeting during Shutdown")
        self.assertIs(type(page), ExtCancellationPage)

    @freeze_timetz("2020-04-04")
    def testEventFutureExceptions(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        exceptions = self.event._futureExceptions(request)
        self.assertEqual(len(exceptions), 1)
        shutdown = exceptions[0]
        self.assertEqual(shutdown.title,
                         "Cancellation from Friday 20th of March to Monday 1st of June")
        self.assertEqual(shutdown.cancellation_title, "No Meeting during Shutdown")
        self.assertEqual(shutdown._future_datetime_from, datetimetz(2020,4,6,13))

    @freeze_timetz("2020-08-31")
    def testPast(self):
        self.assertEqual(list(ExtCancellationPage.events.past()), [self.shutdown])
        self.assertEqual(ExtCancellationPage.events.past().count(), 1)
        self.assertEqual(ExtCancellationPage.events.future().count(), 0)

    @freeze_timetz("2020-05-04")
    def testFuture(self):
        self.assertEqual(list(ExtCancellationPage.events.future()), [self.shutdown])
        self.assertEqual(ExtCancellationPage.events.past().count(), 1)
        self.assertEqual(ExtCancellationPage.events.future().count(), 1)

    @freeze_timetz("2020-06-01 14:00:00")
    def testCurrent(self):
        self.assertEqual(list(ExtCancellationPage.events.current()), [self.shutdown])
        self.assertEqual(ExtCancellationPage.events.past().count(), 1)
        self.assertEqual(ExtCancellationPage.events.current().count(), 1)
        self.assertEqual(ExtCancellationPage.events.future().count(), 0)

    def testEventOccursOn(self):
        self.assertIs(self.event._occursOn(dt.date(2020, 5, 11)), False)

    @freeze_timetz("2020-05-31")
    def testEventNextDate(self):
        self.assertEqual(self.event.next_date, dt.date(2020,6,3))

    @freeze_timetz("2020-06-01")
    def testEventPastDatetime(self):
        self.assertEqual(self.event._past_datetime_from, datetimetz(2020,3,18,13,0))

    @freeze_timetz("2020-06-01")
    def testEventFutureDatetime(self):
        shutdown = ExtCancellationPage(owner = self.user,
                                       overrides = self.event,
                                       cancelled_from_date = dt.date(2020,5,13))
        self.event.add_child(instance=shutdown)
        shutdown.save_revision().publish()
        self.assertIsNone(self.event._future_datetime_from)

    @freeze_timetz("2020-06-16")
    def testGetUpcomingEvents(self):
        event = RecurringEventPage(slug      = "lemon",
                                   title     = "Lemonade Stand",
                                   repeat    = Recurrence(dtstart=dt.date(2021,1,1),
                                                          freq=WEEKLY,
                                                          byweekday=[FR]),
                                   time_from = dt.time(11),
                                   time_to   = dt.time(13))
        self.calendar.add_child(instance=event)
        shutdown = ExtCancellationPage(owner = self.user,
                                       overrides = event,
                                       cancelled_from_date = dt.date(2021,2,13),
                                       cancellation_title = "Gone fishing")
        event.add_child(instance=shutdown)
        shutdown.save_revision().publish()
        events = ExtCancellationPage.events.exclude(cancellation_title="")   \
                                      .upcoming().this()                     \
                                      .descendant_of(event)
        self.assertEqual(len(events), 1)
        title, page, url  = events[0]
        self.assertEqual(title, "Gone fishing")
        self.assertEqual(page._future_datetime_from, datetimetz(2021,2,19,11,0))
        self.assertEqual(url, "/events/lemon/2021-02-13--cancellation/")

    @freeze_timetz("2020-06-16")
    def testGetPastEvents(self):
        events = ExtCancellationPage.events.past().this()
        self.assertEqual(len(events), 1)
        title, page, url  = events[0]
        self.assertEqual(title, "No Meeting during Shutdown")
        self.assertEqual(page._past_datetime_from, datetimetz(2020,6,1,13,0))
        self.assertEqual(url, "/events/test-meeting/2020-03-20-2020-06-01-cancellation/")

    def testGetMyDates(self):
        dates = list(self.shutdown._getMyDates())
        self.assertEqual(dates,                                  [dt.date(2020,3,20),
                          dt.date(2020,3,23), dt.date(2020,3,25), dt.date(2020,3,27),
                          dt.date(2020,3,30), dt.date(2020,4, 1), dt.date(2020,4, 3),
                          dt.date(2020,4, 6), dt.date(2020,4, 8), dt.date(2020,4,10),
                          dt.date(2020,4,13), dt.date(2020,4,15), dt.date(2020,4,17),
                          dt.date(2020,4,20), dt.date(2020,4,22), dt.date(2020,4,24),
                          dt.date(2020,4,27), dt.date(2020,4,29), dt.date(2020,5, 1),
                          dt.date(2020,5, 4), dt.date(2020,5, 6), dt.date(2020,5, 8),
                          dt.date(2020,5,11), dt.date(2020,5,13), dt.date(2020,5,15),
                          dt.date(2020,5,18), dt.date(2020,5,20), dt.date(2020,5,22),
                          dt.date(2020,5,25), dt.date(2020,5,27), dt.date(2020,5,29),
                          dt.date(2020,6, 1)])

    def testGetMyRawDates(self):
        dates = list(self.shutdown._getMyRawDates(dt.date(2020,5,30),
                                                  dt.date(2020,6,10)))
        self.assertEqual(dates,
                         [dt.date(2020,5,30), dt.date(2020,5,31), dt.date(2020,6,1)])

    def testClosedOn(self):
        shutdown2 = ExtCancellationPage(owner = self.user,
                                        overrides = self.event,
                                        cancelled_from_date=dt.date(2020,9,2))
        self.event.add_child(instance=shutdown2)
        shutdown2.save_revision().publish()
        self.assertIs(shutdown2._closedOn(dt.date(2020, 9, 21)), True)
        self.assertIs(self.shutdown._closedOn(dt.date(2020, 3, 24)), True)
        self.assertIs(self.shutdown._closedOn(dt.date(2020, 6, 22)), False)

    def testStatus(self):
        self.assertEqual(self.shutdown.status, "cancelled")
        self.assertEqual(self.shutdown.status_text, "This event has been cancelled.")

    def testWhen(self):
        self.assertEqual(self.shutdown.when,
                         "Cancelled from Friday 20th of March to Monday 1st of June")

    def testWhenEver(self):
        event = RecurringEventPage(slug      = "OpQ",
                                   title     = "Orangepurple Quagga",
                                   repeat    = Recurrence(dtstart=dt.date(2020,1,1),
                                                          freq=MONTHLY,
                                                          byweekday=[FR(-1)]),
                                   time_from = dt.time(19))
        self.calendar.add_child(instance=event)
        shutdown = ExtCancellationPage(owner = self.user,
                                       overrides = event,
                                       cancelled_from_date = dt.date(2020,4,1))
        event.add_child(instance=shutdown)
        shutdown.save_revision().publish()
        self.assertEqual(shutdown.when,
                         "Cancelled from Wednesday 1st of April until further notice")

    def testAt(self):
        self.assertEqual(self.shutdown.at.strip(), "1pm")

    @freeze_timetz("2020-03-25 14:00")
    def testCurrentDt(self):
        self.assertEqual(self.shutdown._current_datetime_from,
                         datetimetz(2020,3,25,13,0))

    @freeze_timetz("2020-03-25 14:00")
    def testFutureDt(self):
        self.assertEqual(self.shutdown._future_datetime_from,
                         datetimetz(2020,3,27,13,0))

    @freeze_timetz("2020-03-25 14:00")
    def testPastDt(self):
        self.assertEqual(self.shutdown._past_datetime_from,
                         datetimetz(2020,3,25,13,0))

    def testUnexplainedCancellation(self):
        shutdown = ExtCancellationPage(owner = self.user,
                                       overrides = self.event,
                                       cancelled_from_date = dt.date(2019, 2, 8),
                                       cancellation_title   = "Restructure Pending",
                                       cancellation_details = "Keep it quiet")
        self.event.add_child(instance=shutdown)
        PASSWORD = PageViewRestriction.PASSWORD
        restriction = PageViewRestriction.objects.create(restriction_type = PASSWORD,
                                                         password = "s3cr3t",
                                                         page = shutdown)
        restriction.save()
        events = RecurringEventPage.events.byDay(dt.date(2019,2,1),
                                                 dt.date(2019,2,28))
        self.assertEqual(len(events), 28)
        evod = events[7]
        self.assertEqual(evod.date, dt.date(2019,2,8))
        self.assertEqual(len(evod.days_events), 0)
        self.assertEqual(len(evod.continuing_events), 0)

    def testGroup(self):
        self.assertIsNone(self.shutdown.group)

    def testOverridesRepeat(self):
        self.assertEqual(self.shutdown.overrides_repeat, self.event.repeat)

    def testGetContext(self):
        request = RequestFactory().get("/test")
        context = self.shutdown.get_context(request)
        self.assertIn('overrides', context)

# ------------------------------------------------------------------------------
class TestPageForm(TestCase):
    Form = ExtCancellationPage.get_edit_handler().get_form_class()

    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@bar.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
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
        self.shutdown = ExtCancellationPage(owner = self.user,
                                            overrides = self.event,
                                            cancelled_from_date=dt.date(2020,3,2),
                                            cancelled_to_date=dt.date(2020,3,6))
        self.event.add_child(instance=self.shutdown)
        self.shutdown.save_revision().publish()

    def testValid(self):
        page = ExtCancellationPage(owner = self.user)
        form = self.Form({'overrides':    self.event,
                          'cancelled_from_date':  "2020-03-10"},
                          instance = page, parent_page = self.event)
        self.assertTrue(form.is_valid())         # is_valid() calls full_clean()
        self.assertDictEqual(form.errors, {})

    def testExceptionAlreadyExists(self):
        page = ExtCancellationPage(owner=self.user)
        form = self.Form({'overrides':         self.event,
                          'cancelled_from_date':  "2020-03-02"},
                          instance=page,
                          parent_page=self.event)
        self.assertFalse(form.is_valid())
        self.assertDictEqual(form.errors,
                             {'cancelled_from_date':
                              ['There is already an extended cancellation for then']})

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
