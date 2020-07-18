# ------------------------------------------------------------------------------
# Test Recurring Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
import calendar
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Site, Page
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import DAILY, WEEKLY, MONTHLY
from ls.joyous.utils.recurrence import TU, TH, SA, SU, EVERYWEEKDAY
from ls.joyous.models import CalendarPage
from ls.joyous.models import (RecurringEventPage, CancellationPage,
                              PostponementPage)
from .testutils import datetimetz, freeze_timetz

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        Site.objects.update(hostname="joy.test")
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        Page.objects.get(slug='home').add_child(instance=self.calendar)
        self.calendar.save()
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(owner = self.user,
                                        slug  = "lug-meetup",
                                        title = "Linux Users Group Meetup",
                                        repeat = Recurrence(dtstart=dt.date(2017,8,5),
                                                            freq=MONTHLY,
                                                            byweekday=[TU(1)]),
                                        time_from = dt.time(18,30),
                                        time_to   = dt.time(20),
                                        location  = "6 Mackay St, Greymouth (upstairs)")
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByDay(self):
        events = RecurringEventPage.events.byDay(dt.date(2017,8,1),
                                                 dt.date(2017,10,31))
        self.assertEqual(len(events), 92)
        evod = events[35]
        self.assertEqual(evod.date, dt.date(2017,9,5))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)

    def testStatus(self):
        pastEvent = RecurringEventPage(owner = self.user,
                                       slug  = "past",
                                       title = "Past Event",
                                       repeat = Recurrence(dtstart=dt.date(2008,2,1),
                                                           until=dt.date(2008,5,4),
                                                           freq=WEEKLY,
                                                           byweekday=[SA,SU]))
        self.calendar.add_child(instance=pastEvent)
        self.assertEqual(pastEvent.status, "finished")
        self.assertEqual(pastEvent.status_text, "These events have finished.")
        now = timezone.localtime()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = datetimetz(now.date(), dt.time.min)
        nowEvent = RecurringEventPage(owner = self.user,
                                      slug  = "now",
                                      title = "Now Event",
                                      repeat = Recurrence(dtstart=dt.date(2010,1,1),
                                                          freq=DAILY),
                                      time_from = earlier.time(),
                                      time_to   = dt.time.max)
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent.status, "started")
        self.assertEqual(nowEvent.status_text, "This event has started.")
        today = timezone.localdate()
        notToday = [weekday for weekday in EVERYWEEKDAY if weekday.weekday != today.weekday()]
        pastAndFutureEvent = RecurringEventPage(owner = self.user,
                                                slug  = "not-today",
                                                title = "Any day but today",
                                                repeat = Recurrence(dtstart=dt.date(2009,8,7),
                                                                    freq=WEEKLY,
                                                                    byweekday=notToday))
        self.calendar.add_child(instance=pastAndFutureEvent)
        self.assertIsNone(pastAndFutureEvent.status)
        self.assertEqual(pastAndFutureEvent.status_text, "")

    @freeze_timetz("2008-05-04 09:01")
    def testJustFinishedStatus(self):
        event = RecurringEventPage(owner = self.user,
                                   slug  = "breakfast1",
                                   title = "Breakfast-in-bed",
                                   repeat = Recurrence(dtstart=dt.date(2008,2,1),
                                                       until=dt.date(2008,5,9),
                                                       freq=WEEKLY,
                                                       byweekday=[SA,SU]),
                                      time_from = dt.time(8),
                                      time_to   = dt.time(9))
        self.calendar.add_child(instance=event)
        self.assertEqual(event.status, "finished")

    @freeze_timetz("2008-05-04 07:00")
    def testLastOccurenceCancelledStatus(self):
        event = RecurringEventPage(owner = self.user,
                                   slug  = "breakfast2",
                                   title = "Breakfast-in-bed",
                                   repeat = Recurrence(dtstart=dt.date(2008,2,1),
                                                       until=dt.date(2008,5,9),
                                                       freq=WEEKLY,
                                                       byweekday=[SA,SU]),
                                   time_from = dt.time(8),
                                   time_to   = dt.time(9))
        self.calendar.add_child(instance=event)
        cancellation = CancellationPage(owner = self.user,
                                        overrides = event,
                                        except_date = dt.date(2008, 5, 4),
                                        cancellation_title   = "Fire in the kitchen",
                                        cancellation_details = "The bacon fat is burning")
        event.add_child(instance=cancellation)
        self.assertEqual(event.status, "finished")

    @freeze_timetz("2008-05-04 12:00")
    def testPostponementOccurenceLast(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        event = RecurringEventPage(owner = self.user,
                                   slug  = "breakfast3",
                                   title = "Breakfast-in-bed",
                                   repeat = Recurrence(dtstart=dt.date(2008,2,1),
                                                       until=dt.date(2008,5,9),
                                                       freq=WEEKLY,
                                                       byweekday=[SA,SU]),
                                   time_from = dt.time(8),
                                   time_to   = dt.time(9))
        self.calendar.add_child(instance=event)
        postponement = PostponementPage(owner = self.user,
                                        overrides = event,
                                        except_date = dt.date(2008, 5, 3),
                                        postponement_title = "Breakfast in Bed owed from May",
                                        date      = dt.date(2008, 5, 24),
                                        time_from = dt.time(8),
                                        time_to   = dt.time(9))
        event.add_child(instance=postponement)
        self.assertIsNone(event.status)
        self.assertEqual(event._nextOn(request),
                         '<a class="inline-link" href="/events/breakfast3/2008-05-03-postponement/">Saturday 24th of May at 8am</a>')

    def testWhen(self):
        self.assertEqual(self.event.when, "The first Tuesday of the month at 6:30pm to 8pm")

    def testAt(self):
        self.assertEqual(self.event.at.strip(), "6:30pm")

    def testCurrentDt(self):
        lugDt = self.event._current_datetime_from
        self.assertEqual(lugDt.time(), dt.time(18,30))
        self.assertEqual(lugDt.date().weekday(), 1)
        self.assertLess(lugDt.date().day, 8)
        movieNight = RecurringEventPage(owner = self.user,
                                        slug  = "movies",
                                        title = "Movies",
                                        repeat = Recurrence(dtstart=dt.date(2005,2,1),
                                                            freq=WEEKLY,
                                                            byweekday=[TH,]),
                                        time_from = dt.time(20,15),
                                        time_to   = dt.time(21,30))
        self.calendar.add_child(instance=movieNight)
        now = timezone.localtime()
        myday = now.date()
        startTime = dt.time(20,15)
        if now.time() > startTime:
            myday += dt.timedelta(days=1)
        thursday = myday + dt.timedelta(days=(3-myday.weekday())%7)
        self.assertEqual(movieNight._current_datetime_from,
                         datetimetz(thursday, startTime))

    def testFutureDt(self):
        lugDt = self.event._future_datetime_from
        self.assertEqual(lugDt.time(), dt.time(18,30))
        self.assertEqual(lugDt.date().weekday(), 1)
        self.assertLess(lugDt.date().day, 8)
        movieNight = RecurringEventPage(owner = self.user,
                                        slug  = "movies",
                                        title = "Movies",
                                        repeat = Recurrence(dtstart=dt.date(2005,2,1),
                                                            freq=WEEKLY,
                                                            byweekday=[TH,]),
                                        time_from = dt.time(20,15),
                                        time_to   = dt.time(21,30))
        self.calendar.add_child(instance=movieNight)
        now = timezone.localtime()
        myday = now.date()
        startTime = dt.time(20,15)
        if now.time() > startTime:
            myday += dt.timedelta(days=1)
        thursday = myday + dt.timedelta(days=(3-myday.weekday())%7)
        self.assertEqual(movieNight._future_datetime_from,
                         datetimetz(thursday, startTime))

    def testPastDt(self):
        lugDt = self.event._past_datetime_from
        self.assertEqual(lugDt.time(), dt.time(18,30))
        self.assertEqual(lugDt.date().weekday(), 1)
        self.assertLess(lugDt.date().day, 8)
        movieNight = RecurringEventPage(owner = self.user,
                                        slug  = "movies",
                                        title = "Movies",
                                        repeat = Recurrence(dtstart=dt.date(2005,2,1),
                                                            freq=WEEKLY,
                                                            byweekday=[TH,]),
                                        time_from = dt.time(20,15),
                                        time_to   = dt.time(21,30))
        self.calendar.add_child(instance=movieNight)
        now = timezone.localtime()
        myday = now.date()
        startTime = dt.time(20,15)
        if now.time() < startTime:
            myday -= dt.timedelta(days=1)
        thursday = myday - dt.timedelta(days=(myday.weekday()-3)%7)
        self.assertEqual(movieNight._past_datetime_from,
                         datetimetz(thursday, startTime))

    def testGroup(self):
        self.assertIsNone(self.event.group)

    def testOccursOn(self):
        self.assertIs(self.event._occursOn(dt.date(2018,3,6)), True)
        self.assertIs(self.event._occursOn(dt.date(2018,3,13)), False)

# ------------------------------------------------------------------------------
class TestTZ(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@ok.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(owner = self.user,
                                        slug  = "code-for-boston",
                                        title = "Code for Boston",
                                        repeat    = Recurrence(dtstart=dt.date(2017,1,1),
                                                               freq=WEEKLY,
                                                               byweekday=[TU]),
                                        time_from = dt.time(19),
                                        time_to   = dt.time(21,30),
                                        tz = pytz.timezone("US/Eastern"),
                                        location  = "4th Floor, 1 Broadway, Cambridge, MA")
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByLocalDay(self):
        events = RecurringEventPage.events.byDay(dt.date(2018,4,1),
                                                 dt.date(2018,4,30))
        self.assertEqual(len(events), 30)
        evod1 = events[3]
        self.assertEqual(evod1.date, dt.date(2018,4,4))
        self.assertEqual(len(evod1.days_events), 1)
        self.assertEqual(len(evod1.continuing_events), 0)

    @freeze_timetz("2017-05-31")
    def testLocalWhen(self):
        with timezone.override("America/Los_Angeles"):
            self.assertEqual(self.event.when,
                             "Tuesdays at 4pm to 6:30pm")
        with timezone.override("Australia/Perth"):
            self.assertEqual(self.event.when,
                             "Wednesdays at 7am to 9:30am")

    @timezone.override("America/Los_Angeles")
    def testLocalAt(self):
        self.assertEqual(self.event.at, "4pm")

    @timezone.override("America/Los_Angeles")
    def testCurrentLocalDt(self):
        when = self.event._current_datetime_from
        self.assertEqual(when.tzinfo.zone, "America/Los_Angeles")
        self.assertEqual(when.weekday(), calendar.TUESDAY)

    @timezone.override("America/Los_Angeles")
    def testFutureLocalDt(self):
        when = self.event._future_datetime_from
        self.assertEqual(when.tzinfo.zone, "America/Los_Angeles")
        self.assertEqual(when.weekday(), calendar.TUESDAY)

    @timezone.override("Pacific/Auckland")
    def testPastLocalDt(self):
        when = self.event._past_datetime_from
        self.assertEqual(when.tzinfo.zone, "Pacific/Auckland")
        self.assertEqual(when.weekday(), calendar.WEDNESDAY)

    @timezone.override("Pacific/Kiritimati")
    def testExtremeTimeZones(self):
        lions = RecurringEventPage(owner = self.user,
                                   slug  = "pago-pago-lions",
                                   title = "Pago Pago Lions Club",
                                   repeat = Recurrence(dtstart=dt.date(2015,2,1),
                                                       freq=MONTHLY,
                                                       byweekday=[TH(1),TH(3)]),
                                   time_from = dt.time(23,0),
                                   tz = pytz.timezone("Pacific/Pago_Pago"),
                                   location = "Lions Den, Tafuna, PagoPago",
                                   website = "http://www.lionsclubs.org.nz")
        self.calendar.add_child(instance=lions)
        self.assertEqual(lions.when,
                         "The Saturday after the first Thursday and "
                         "Saturday after the third Thursday of the month at 12am")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
