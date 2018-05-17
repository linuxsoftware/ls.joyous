# ------------------------------------------------------------------------------
# Test Simple Event Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from freezegun import freeze_time
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser, Group
from django.utils import timezone
from wagtail.core.models import Page, PageViewRestriction
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import SimpleEventPage, ThisEvent, EventsOnDay
from ls.joyous.models.groups import get_group_model
from .testutils import datetimetz
GroupPage = get_group_model()

class TestSimpleEvent(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = SimpleEventPage(owner = self.user,
                                     slug   = "pet-show",
                                     title  = "Pet Show",
                                     date      = dt.date(1987,6,5),
                                     time_from = dt.time(11),
                                     time_to   = dt.time(17,30))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def testGetEventsByDay(self):
        events = SimpleEventPage.events.byDay(dt.date(1987,6,1),
                                              dt.date(1987,6,30))
        self.assertEqual(len(events), 30)
        evod = events[4]
        self.assertEqual(evod.date, dt.date(1987,6,5))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)

    def testStatus(self):
        self.assertEqual(self.event.status, "finished")
        self.assertEqual(self.event.status_text, "This event has finished.")
        now = timezone.localtime()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = SimpleEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date      = now.date(),
                                   time_from = earlier.time(),
                                   time_to   = dt.time.max)
        self.assertEqual(nowEvent.status, "started")
        self.assertEqual(nowEvent.status_text, "This event has started.")
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        futureEvent = SimpleEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date  = tomorrow)
        self.calendar.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent.status)
        self.assertEqual(futureEvent.status_text, "")

    def testWhen(self):
        self.assertEqual(self.event.when,
                         "Friday 5th of June 1987 at 11am to 5:30pm")

    def testAt(self):
        self.assertEqual(self.event.at, "11am")

    def testUpcomingDt(self):
        self.assertIsNone(self.event._upcoming_datetime_from)
        now = timezone.localtime()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = SimpleEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date      = now.date(),
                                   time_from = earlier.time(),
                                   time_to   = dt.time.max)
        self.calendar.add_child(instance=nowEvent)
        self.assertIsNone(nowEvent._upcoming_datetime_from)
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        futureEvent = SimpleEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date  = tomorrow)
        self.calendar.add_child(instance=futureEvent)
        self.assertEqual(futureEvent._upcoming_datetime_from,
                         datetimetz(tomorrow, dt.time.max))

    def testPastDt(self):
        self.assertEqual(self.event._past_datetime_from, datetimetz(1987,6,5,11,0))
        now = timezone.localtime()
        earlier = now - dt.timedelta(hours=1)
        if earlier.date() != now.date():
            earlier = dt.datetime.combine(now.date(), dt.time.min)
        nowEvent = SimpleEventPage(owner = self.user,
                                   slug  = "now",
                                   title = "Now Event",
                                   date      = now.date(),
                                   time_from = earlier.time(),
                                   time_to   = dt.time.max)
        self.calendar.add_child(instance=nowEvent)
        self.assertEqual(nowEvent._past_datetime_from, earlier)
        tomorrow = timezone.localdate() + dt.timedelta(days=1)
        futureEvent = SimpleEventPage(owner = self.user,
                                      slug  = "tomorrow",
                                      title = "Tomorrow's Event",
                                      date  = tomorrow)
        self.calendar.add_child(instance=futureEvent)
        self.assertIsNone(futureEvent._past_datetime_from)

    def testGroup(self):
        self.assertIsNone(self.event.group)
        group = GroupPage(slug  = "runners",
                          title = "Runners")
        self.home.add_child(instance=group)
        race = SimpleEventPage(owner = self.user,
                               slug  = "race",
                               title = "Race",
                               date  = dt.date(2008, 6, 3))
        group.add_child(instance=race)
        self.assertEqual(race.group, group)

class TestSimpleEventTZ(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = SimpleEventPage(owner = self.user,
                                     slug   = "pet-show",
                                     title  = "Pet Show",
                                     date   = dt.date(1987,6,5),
                                     time_from = dt.time(11),
                                     time_to   = dt.time(17,30),
                                     tz = pytz.timezone("Australia/Sydney"))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    @timezone.override("America/Los_Angeles")
    def testGetEventsByLocalDay(self):
        evods = SimpleEventPage.events.byDay(dt.date(1987,6,1),
                                             dt.date(1987,6,30))
        self.assertEqual(len(evods), 30)
        evod1 = evods[3]
        self.assertEqual(evod1.date, dt.date(1987,6,4))
        self.assertEqual(len(evod1.days_events), 1)
        self.assertEqual(len(evod1.continuing_events), 0)
        evod2 = evods[4]
        self.assertEqual(evod2.date, dt.date(1987,6,5))
        self.assertEqual(len(evod2.days_events), 0)
        self.assertEqual(len(evod2.continuing_events), 1)
        self.assertEqual(evod1.all_events[0], evod2.all_events[0])
        self.assertIs(evod1.all_events[0].page, evod2.all_events[0].page)

    @timezone.override("America/Los_Angeles")
    def testLocalWhen(self):
        self.assertEqual(self.event.when,
                         "Thursday 4th of June 1987 at 6pm to Friday 5th of June 1987 at 12:30am")

    @timezone.override("America/Los_Angeles")
    def testLocalAt(self):
        self.assertEqual(self.event.at, "6pm")

    @timezone.override("America/Los_Angeles")
    def testUpcomingLocalDt(self):
        self.assertIsNone(self.event._upcoming_datetime_from)

    @timezone.override("America/Los_Angeles")
    def testPastLocalDt(self):
        when = self.event._past_datetime_from
        self.assertEqual(when.tzinfo.zone, "America/Los_Angeles")
        self.assertEqual(when.time(), dt.time(18))
        self.assertEqual(when.date(), dt.date(1987,6,4))

    @timezone.override("Pacific/Tongatapu")
    def testGetEventsAcrossDateline(self):
        showDay = SimpleEventPage(owner = self.user,
                                  slug  = "tamakautoga-village-show-day",
                                  title = "Tamakautoga Village Show Day",
                                  date      = dt.date(2016,7,30),
                                  tz = pytz.timezone("Pacific/Niue"))
        self.calendar.add_child(instance=showDay)
        evods = SimpleEventPage.events.byDay(dt.date(2016,7,31),
                                             dt.date(2016,7,31))
        self.assertEqual(len(evods[0].days_events), 1)
        self.assertEqual(len(evods[0].continuing_events), 0)
        event = evods[0].days_events[0].page
        self.assertEqual(event.at, "")
        self.assertEqual(event.when, "Sunday 31st of July 2016")

class TestSimpleEventQuerySet(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = SimpleEventPage(owner = self.user,
                                     slug   = "agfest",
                                     title  = "AgFest",
                                     date   = dt.date(2015,6,5),
                                     time_from = dt.time(11),
                                     time_to   = dt.time(17,30))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    @freeze_time("2017-05-31")
    def testPast(self):
        self.assertEqual(list(SimpleEventPage.events.past()), [self.event])
        self.assertEqual(SimpleEventPage.events.past().count(), 1)
        self.assertEqual(SimpleEventPage.events.upcoming().count(), 0)

    @freeze_time("2012-03-04")
    def testUpcoming(self):
        self.assertEqual(list(SimpleEventPage.events.upcoming()), [self.event])
        self.assertEqual(SimpleEventPage.events.past().count(), 0)
        self.assertEqual(SimpleEventPage.events.upcoming().count(), 1)

    def testThis(self):
        events = list(SimpleEventPage.events.this())
        self.assertEqual(len(events), 1)
        this = events[0]
        self.assertTrue(isinstance(this, ThisEvent))
        self.assertEqual(this.title, "AgFest")
        self.assertEqual(this.page, self.event)

    def testByDay(self):
        evods = SimpleEventPage.events.byDay(dt.date(2015,6,5),
                                             dt.date(2015,6,5))
        self.assertEqual(len(evods), 1)
        evod = evods[0]
        self.assertTrue(isinstance(evod, EventsOnDay))
        self.assertEqual(evod.date, dt.date(2015,6,5))
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)
        self.assertEqual(evod.days_events[0].title, "AgFest")
        self.assertEqual(evod.days_events[0].page, self.event)

    def testPasswordAuth(self):
        PASSWORD = PageViewRestriction.PASSWORD
        KEY      = PageViewRestriction.passed_view_restrictions_session_key
        meeting = SimpleEventPage(owner = self.user,
                                  slug   = "club-meet",
                                  title  = "Club Meeting",
                                  date   = dt.date(2009,10,21))
        self.calendar.add_child(instance=meeting)
        meeting.save_revision().publish()
        restriction = PageViewRestriction.objects.create(restriction_type = PASSWORD,
                                                         password = "s3cr3t",
                                                         page = meeting)
        self.assertEqual(list(SimpleEventPage.events.all()),
                         [self.event, meeting])
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        self.assertEqual(list(SimpleEventPage.events.auth(request)),
                         [self.event])
        request.session[KEY] = [restriction.id]
        self.assertEqual(list(SimpleEventPage.events.auth(request)),
                         [self.event, meeting])

    def testLoginAuth(self):
        LOGIN = PageViewRestriction.LOGIN
        bee = SimpleEventPage(owner = self.user,
                              slug   = "bee",
                              title  = "Working Bee",
                              date   = dt.date(2013,3,30),
                              time_from = dt.time(10))
        self.calendar.add_child(instance=bee)
        bee.save_revision().publish()
        PageViewRestriction.objects.create(restriction_type = LOGIN,
                                           page = bee)
        self.assertEqual(list(SimpleEventPage.events.all()),
                         [self.event, bee])
        request = RequestFactory().get("/test")
        request.user = AnonymousUser()
        request.session = {}
        self.assertEqual(list(SimpleEventPage.events.auth(request)),
                         [self.event])
        request.user = self.user
        self.assertEqual(list(SimpleEventPage.events.auth(request)),
                         [self.event, bee])

    def testGroupsAuth(self):
        GROUPS = PageViewRestriction.GROUPS
        presidium = Group.objects.create(name = "Presidium")
        secretariat = Group.objects.create(name = "Secretariat")
        assembly = Group.objects.create(name = "Assembly")
        meeting = SimpleEventPage(owner = self.user,
                                  slug   = "admin-cmte",
                                  title  = "Administration Committee Meeting",
                                  date   = dt.date(2015,6,20),
                                  time_from = dt.time(16,30))
        self.calendar.add_child(instance=meeting)
        meeting.save_revision().publish()
        restriction = PageViewRestriction.objects.create(restriction_type = GROUPS,
                                                         page = meeting)
        restriction.groups.set([presidium, secretariat])
        restriction.save()
        self.assertEqual(list(SimpleEventPage.events.all()),
                         [self.event, meeting])
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        self.assertEqual(list(SimpleEventPage.events.auth(request)),
                         [self.event])
        request.user = User.objects.create_superuser('joe', 'joe@joy.test', 's3cr3t')
        self.assertEqual(list(SimpleEventPage.events.auth(request)),
                         [self.event, meeting])
        request.user = User.objects.create_user('jill', 'jill@joy.test', 's3cr3t')
        request.user.groups.set([secretariat, assembly])
        self.assertEqual(list(SimpleEventPage.events.auth(request)),
                         [self.event, meeting])
