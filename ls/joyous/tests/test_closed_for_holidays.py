# ------------------------------------------------------------------------------
# Test ClosedForHolidays Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from itertools import islice
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import RecurringEventPage, CancellationPage
from ls.joyous.models.events import ClosedForHolidaysPage, ClosedFor
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
                                        repeat    = Recurrence(dtstart=dt.date(1989,1,1),
                                                               freq=WEEKLY,
                                                               byweekday=[MO,WE,FR]),
                                        time_from = dt.time(13),
                                        time_to   = dt.time(15,30),
                                        holidays = self.calendar.holidays)
        self.calendar.add_child(instance=self.event)
        self.closedHols = ClosedForHolidaysPage(owner = self.user,
                                                overrides = self.event,
                                                all_holidays = True,
                                                holidays = self.calendar.holidays)
        self.event.add_child(instance=self.closedHols)
        self.closedHols.save_revision().publish()

    def testCanCreateOnlyOne(self):
        self.assertFalse(ClosedForHolidaysPage.can_create_at(self.event))

    def testInit(self):
        self.assertEqual(self.closedHols.all_holidays, True)
        self.assertEqual(self.closedHols.title, "Closed for holidays")
        self.assertEqual(self.closedHols.local_title, "Closed for holidays")
        self.assertEqual(self.closedHols.slug,  "closed-for-holidays")

    def testGetEventsByDay(self):
        events = RecurringEventPage.events.byDay(dt.date(1989,1,1),
                                                 dt.date(1989,1,31),
                                                 self.calendar.holidays)
        self.assertEqual(len(events), 31)
        evod = events[0]
        self.assertEqual(evod.date, dt.date(1989,1,1))
        self.assertEqual(evod.holiday, "New Year's Day")
        self.assertEqual(len(evod.days_events), 0)
        self.assertEqual(len(evod.continuing_events), 0)

    @freeze_timetz("1990-10-11 16:29:00")
    def testGetUpcomingEvents(self):
        event = RecurringEventPage(slug      = "RST",
                                   title     = "Ruritania secret taxidermy",
                                   repeat    = Recurrence(dtstart=dt.date(1980,1,1),
                                                          freq=MONTHLY,
                                                          byweekday=[MO(1)]),
                                   time_from = dt.time(20),
                                   holidays = self.calendar.holidays)
        self.calendar.add_child(instance=event)
        closedHols = ClosedForHolidaysPage(owner = self.user,
                                           overrides = event,
                                           all_holidays = False,
                                           cancellation_title = "Closed for the holiday",
                                           holidays = self.calendar.holidays)
        closedHols.closed_for = [ ClosedFor(name="Wellington Anniversary Day"),
                                  ClosedFor(name="Auckland Anniversary Day"),
                                  ClosedFor(name="Nelson Anniversary Day"),
                                  ClosedFor(name="Taranaki Anniversary Day"),
                                  ClosedFor(name="Otago Anniversary Day"),
                                  ClosedFor(name="Southland Anniversary Day"),
                                  ClosedFor(name="South Canterbury Anniversary Day"),
                                  ClosedFor(name="Hawke's Bay Anniversary Day"),
                                  ClosedFor(name="Marlborough Anniversary Day"),
                                  ClosedFor(name="Canterbury Anniversary Day"),
                                  ClosedFor(name="Chatham Islands Anniversary Day"),
                                  ClosedFor(name="Westland Anniversary Day") ]
        event.add_child(instance=closedHols)
        closedHols.save_revision().publish()
        events = ClosedForHolidaysPage.events.exclude(cancellation_title="")   \
                                      .upcoming().this(self.calendar.holidays) \
                                      .descendant_of(event)
        self.assertEqual(len(events), 1)
        title, page, url  = events[0]
        self.assertEqual(title, "Closed for the holiday")
        self.assertEqual(page._future_datetime_from, datetimetz(1990,12,3,20,0))
        self.assertEqual(url, "/events/RST/closed-for-holidays/")

    @freeze_timetz("1990-10-11 16:29:00")
    def testGetPastEvents(self):
        events = ClosedForHolidaysPage.events.past().this(self.calendar.holidays)
        self.assertEqual(len(events), 1)
        title, page, url  = events[0]
        self.assertEqual(title, "")
        self.assertEqual(page._past_datetime_from, datetimetz(1990,9,24,13,0))
        self.assertEqual(url, "/events/test-meeting/closed-for-holidays/")

    @freeze_timetz("1990-10-11 16:29:00")
    def testWombatGetEventsByDay(self):
        event = RecurringEventPage(slug      = "UVW",
                                   title     = "Underwater viking wombats",
                                   repeat    = Recurrence(dtstart=dt.date(1989,1,1),
                                                          freq=MONTHLY,
                                                          byweekday=[MO(1)]),
                                   time_from = dt.time(19),
                                   holidays = self.calendar.holidays)
        self.calendar.add_child(instance=event)
        closedHols = ClosedForHolidaysPage(owner = self.user,
                                           overrides = event,
                                           all_holidays = False,
                                           cancellation_title = "UVW Cancelled",
                                           holidays = self.calendar.holidays)
        closedHols.closed_for = [ ClosedFor(name="New Year's Day"),
                                  ClosedFor(name="Day after New Year's Day"),
                                  ClosedFor(name="Good Friday"),
                                  ClosedFor(name="Easter Monday"),
                                  ClosedFor(name="Christmas Day"),
                                  ClosedFor(name="Boxing Day") ]
        event.add_child(instance=closedHols)
        closedHols.save_revision().publish()
        events = RecurringEventPage.events.byDay(dt.date(1989,1,1),
                                                 dt.date(1989,1,31),
                                                 self.calendar.holidays)
        self.assertEqual(len(events), 31)
        evod = events[1]
        self.assertEqual(evod.date, dt.date(1989,1,2))
        self.assertEqual(evod.holiday, "Day after New Year's Day")
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        title, page, url = evod.all_events[0]
        self.assertEqual(title, "UVW Cancelled")
        self.assertEqual(page.title, "Closed for holidays")
        self.assertEqual(page.at, "7pm")
        self.assertEqual(url, "/events/UVW/closed-for-holidays/")

    @freeze_timetz("1990-11-11 16:29:00")
    def testFutureExceptions(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        exceptions = self.event._futureExceptions(request)
        self.assertEqual(len(exceptions), 1)
        c4h = exceptions[0]
        self.assertEqual(c4h.title, "Closed for holidays")
        self.assertEqual(c4h._future_datetime_from, datetimetz(1990,11,16,13,0))

    def testClosedForDates(self):
        dates10 = list(islice(self.closedHols._closed_for_dates, 10))
        self.assertEqual(dates10, [ dt.date(1989,1,2),
                                    dt.date(1989,1,16),
                                    dt.date(1989,1,23),
                                    dt.date(1989,1,30),
                                    dt.date(1989,2,6),
                                    dt.date(1989,3,13),
                                    dt.date(1989,3,20),
                                    dt.date(1989,3,24),
                                    dt.date(1989,3,27),
                                    dt.date(1989,6,5) ])

    def testOccursOn(self):
        self.event.holidays = self.calendar.holidays
        self.assertIs(self.event._occursOn(dt.date(1989, 1, 1)), False)
        self.assertIs(self.event._occursOn(dt.date(1989, 1, 2)), False)
        self.assertIs(self.event._occursOn(dt.date(1989, 1, 6)), True)
        self.assertIs(self.event._occursOn(dt.date(1989, 1, 16)), False)

    def testStatus(self):
        self.assertEqual(self.closedHols.status, "cancelled")
        self.assertEqual(self.closedHols.status_text, "Closed for holidays.")

    def testWhen(self):
        self.assertEqual(self.closedHols.when, "Closed for holidays")

    def testWhenEver(self):
        event = RecurringEventPage(slug      = "XYZ",
                                   title     = "Xylophone yacht zombies",
                                   repeat    = Recurrence(dtstart=dt.date(1989,1,1),
                                                          freq=WEEKLY,
                                                          byweekday=[FR]),
                                   time_from = dt.time(19),
                                   holidays = self.calendar.holidays)
        self.calendar.add_child(instance=event)
        closedHols = ClosedForHolidaysPage(owner = self.user,
                                           overrides = event,
                                           all_holidays = False,
                                           cancellation_title = "XYZ Cancelled",
                                           holidays = self.calendar.holidays)
        closedHols.closed_for = [ ClosedFor(name="Good Friday"),
                                  ClosedFor(name="Easter Monday") ]
        event.add_child(instance=closedHols)
        closedHols.save_revision().publish()
        self.assertEqual(closedHols.when, "Closed for Good Friday and Easter Monday")
        self.assertIs(event._occursOn(dt.date(1989, 3, 24)), False)

    def testAt(self):
        self.assertEqual(self.closedHols.at.strip(), "1pm")

    @freeze_timetz("1989-02-15")
    def testCurrentDt(self):
        # Taranaki Anniversary Day
        self.assertEqual(self.closedHols._current_datetime_from,
                         datetimetz(1989,3,13,13,0))

    @freeze_timetz("1989-02-15")
    def testFutureDt(self):
        # Taranaki Anniversary Day
        self.assertEqual(self.closedHols._future_datetime_from,
                         datetimetz(1989,3,13,13,0))

    @freeze_timetz("1989-02-15")
    def testPastDt(self):
        # Waitangi Day
        self.assertEqual(self.closedHols._past_datetime_from,
                         datetimetz(1989,2,6,13,0))

    def testGroup(self):
        self.assertIsNone(self.closedHols.group)

    def testOverridesRepeat(self):
        self.assertEqual(self.closedHols.overrides_repeat, self.event.repeat)

    def testGetContext(self):
        request = RequestFactory().get("/test")
        context = self.closedHols.get_context(request)
        self.assertIn('overrides', context)

    def testClosedForStr(self):
        xmas = ClosedFor(name="☧mas")
        self.assertEqual(str(xmas), "☧mas")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
