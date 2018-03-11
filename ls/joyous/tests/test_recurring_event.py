# ------------------------------------------------------------------------------
# Test Recurring Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase
from django.contrib.auth.models import User
from wagtail.core.models import Page
from ls.joyous.recurrence import Recurrence
from ls.joyous.recurrence import DAILY, WEEKLY, MONTHLY, TU, TH, WEEKEND, EVERYDAY
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import RecurringEventPage


class TestRecurringEvent(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('i', 'i@foo.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        Page.objects.get(slug='home').add_child(instance=self.calendar)
        self.calendar.save()
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(owner = self.user,
                                        slug  = "lug-meetup",
                                        title = "Linux Users Group Meetup",
                                        repeat    = Recurrence(dtstart=dt.date(2017,8,5),
                                                               freq=MONTHLY,
                                                               byweekday=[TU(1)]),
                                        time_from = dt.time(18,30),
                                        time_to   = dt.time(20),
                                        location  = "6 Mackay St, Greymouth (upstairs)")
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByDay(self):
        events = RecurringEventPage.getEventsByDay(dt.date(2017,8,1),
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
                                       repeat    = Recurrence(dtstart=dt.date(2008,2,1),
                                                              until=dt.date(2008,5,4),
                                                              freq=WEEKLY,
                                                              byweekday=WEEKEND))
        self.calendar.add_child(instance=pastEvent)
        self.assertEqual(pastEvent.status, "finished")
        self.assertEqual(pastEvent.status_text, "These events have finished.")
        now = dt.datetime.now()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = RecurringEventPage(owner = self.user,
                                      slug  = "now",
                                      title = "Now Event",
                                      repeat    = Recurrence(dtstart=dt.date(2010,1,1),
                                                             freq=DAILY),
                                      time_from = earlier.time(),
                                      time_to   = dt.time.max)
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent.status, "started")
        self.assertEqual(nowEvent.status_text, "This event has started.")
        today = dt.date.today()
        notToday = [weekday for weekday in EVERYDAY if weekday.weekday != today.weekday()]
        pastAndFutureEvent = RecurringEventPage(owner = self.user,
                                                slug  = "not-today",
                                                title = "Any day but today",
                                                repeat   = Recurrence(dtstart=dt.date(2009,8,7),
                                                                      freq=WEEKLY,
                                                                      byweekday=notToday))
        self.calendar.add_child(instance=pastAndFutureEvent)
        self.assertIsNone(pastAndFutureEvent.status)
        self.assertEqual(pastAndFutureEvent.status_text, "")

    def testWhen(self):
        self.assertEqual(self.event.when, "The first Tuesday of the month at 6:30pm to 8pm")

    def testAt(self):
        self.assertEqual(self.event.at.strip(), "6:30pm")

    def testUpcomingDt(self):
        lugDt = self.event._upcoming_datetime_from
        self.assertEqual(lugDt.time(), dt.time(18,30))
        self.assertEqual(lugDt.date().weekday(), 1)
        self.assertLess(lugDt.date().day, 8)
        movieNight = RecurringEventPage(owner = self.user,
                                        slug  = "movies",
                                        title = "Movies",
                                        repeat    = Recurrence(dtstart=dt.date(2005,2,1),
                                                               freq=WEEKLY,
                                                               byweekday=[TH,]),
                                        time_from = dt.time(20,15),
                                        time_to   = dt.time(21,30))
        self.calendar.add_child(instance=movieNight)
        now = dt.datetime.now()
        myday = now.date()
        startTime = dt.time(20,15)
        if now.time() > startTime:
            myday += dt.timedelta(days=1)
        thursday = myday + dt.timedelta(days=(3-myday.weekday())%7)
        self.assertEqual(movieNight._upcoming_datetime_from,
                         dt.datetime.combine(thursday, startTime))

    def testPastDt(self):
        lugDt = self.event._past_datetime_from
        self.assertEqual(lugDt.time(), dt.time(18,30))
        self.assertEqual(lugDt.date().weekday(), 1)
        self.assertLess(lugDt.date().day, 8)
        movieNight = RecurringEventPage(owner = self.user,
                                        slug  = "movies",
                                        title = "Movies",
                                        repeat    = Recurrence(dtstart=dt.date(2005,2,1),
                                                               freq=WEEKLY,
                                                               byweekday=[TH,]),
                                        time_from = dt.time(20,15),
                                        time_to   = dt.time(21,30))
        self.calendar.add_child(instance=movieNight)
        now = dt.datetime.now()
        myday = now.date()
        startTime = dt.time(20,15)
        if now.time() < startTime:
            myday -= dt.timedelta(days=1)
        thursday = myday - dt.timedelta(days=(myday.weekday()-3)%7)
        self.assertEqual(movieNight._past_datetime_from,
                         dt.datetime.combine(thursday, startTime))

    def testGroup(self):
        self.assertIsNone(self.event.group)

    def testOccursOn(self):
        self.assertIs(self.event.occursOn(dt.date(2018,3,6)), True)
        self.assertIs(self.event.occursOn(dt.date(2018,3,13)), False)
