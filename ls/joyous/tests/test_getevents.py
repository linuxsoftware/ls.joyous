# ------------------------------------------------------------------------------
# Test Get Event Functions
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
import calendar
from django.test import RequestFactory, TestCase, override_settings
from django.contrib.auth.models import User, AnonymousUser, Group
from django.core.exceptions import (MultipleObjectsReturned, ObjectDoesNotExist,
                                    PermissionDenied)
from django.utils import timezone
from wagtail.core.models import Site, Page, PageViewRestriction
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import WEEKLY, MONTHLY, MO, TU, WE, FR, SU
from ls.joyous.models import GeneralCalendarPage
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, PostponementPage, CancellationPage, ExtraInfoPage)
from ls.joyous.models import (getAllEventsByDay, getAllEventsByWeek,
        getAllUpcomingEvents, getAllPastEvents, getGroupUpcomingEvents,
        getEventFromUid)
from ls.joyous.models import get_group_model
from .testutils import datetimetz

GroupPage = get_group_model()

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@foo.test', 's3cr3t')
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.calendar = GeneralCalendarPage(owner = self.user,
                                            slug  = "events",
                                            title = "Events")
        self.home.add_child(instance=self.calendar)
        self.group = GroupPage(slug = "initech", title = "Initech Corporation")
        self.home.add_child(instance=self.group)

        self.show = SimpleEventPage(owner = self.user,
                                    slug   = "pet-show",
                                    title  = "Pet Show",
                                    date      = dt.date(2013,1,5),
                                    time_from = dt.time(11),
                                    time_to   = dt.time(17,30),
                                    uid       = "29daefed-fed1-4e47-9408-43ec9b06a06d")
        self.calendar.add_child(instance=self.show)

        GROUPS = PageViewRestriction.GROUPS
        self.friends = Group.objects.create(name = "Friends")
        self.rendezvous = SimpleEventPage(owner = self.user,
                                          slug   = "rendezvous",
                                          title  = "Private Rendezvous",
                                          date      = dt.date(2013,1,10),
                                          uid       = "80af64e7-84e6-40d9-8b4f-7edf92aab9f7")
        self.calendar.add_child(instance=self.rendezvous)
        self.rendezvous.save_revision().publish()
        restriction = PageViewRestriction.objects.create(restriction_type = GROUPS,
                                                         page = self.rendezvous)
        restriction.groups.set([self.friends])
        restriction.save()

        self.party = MultidayEventPage(owner = self.user,
                                       slug  = "allnighter",
                                       title = "All Night",
                                       date_from = dt.date(2012,12,31),
                                       date_to   = dt.date(2013,1,1),
                                       time_from = dt.time(23),
                                       time_to   = dt.time(3),
                                       uid       = "initiative+technology")
        self.calendar.add_child(instance=self.party)

        self.standup = RecurringEventPage(slug   = "test-meeting",
                                          title  = "Test Meeting",
                                          repeat = Recurrence(dtstart=dt.date(2013,1,1),
                                                              until=dt.date(2013,5,31),
                                                              freq=WEEKLY,
                                                              byweekday=[MO,WE,FR]),
                                          time_from = dt.time(13,30),
                                          time_to   = dt.time(16),
                                          uid       = "initiative+technology")
        self.group.add_child(instance=self.standup)

        self.postponement = PostponementPage(owner = self.user,
                                             slug  = "2013-01-09-postponement",
                                             title = "Postponement for Wednesday 16th of October",
                                             overrides = self.standup,
                                             except_date = dt.date(2013,1,16),
                                             cancellation_title   = "Meeting Postponed",
                                             cancellation_details =
                                                 "The meeting has been postponed until tomorrow",
                                             postponement_title   = "A Meeting",
                                             date      = dt.date(2013,1,17),
                                             time_from = dt.time(13),
                                             time_to   = dt.time(16,30),
                                             details   = "Yes a test meeting on a Thursday")
        self.standup.add_child(instance=self.postponement)

        cancelTuesday = CancellationPage(owner = self.user,
                                         slug  = "2013-01-01-cancellation",
                                         title = "CancellationPage for Tuesday 1st of January",
                                         overrides = self.standup,
                                         except_date = dt.date(2013,1,1),
                                         cancellation_title   = "Meeting Cancelled")
        self.standup.add_child(instance=cancelTuesday)

    def testGetAllEventsByDay(self):
        events = getAllEventsByDay(self.request,
                                   dt.date(2013,1,1), dt.date(2013,1,31),
                                   holidays=self.calendar.holidays)
        self.assertEqual(len(events), 31)
        evod1 = events[0]
        self.assertEqual(evod1.date, dt.date(2013,1,1))
        self.assertEqual(len(evod1.all_events), 1)
        self.assertEqual(len(evod1.days_events), 0)
        self.assertEqual(len(evod1.continuing_events), 1)
        evod10 = events[9]
        self.assertEqual(evod10.date, dt.date(2013,1,10))
        self.assertEqual(len(evod10.all_events), 0)

    def testAuthGetAllEventsByDay(self):
        self.request.user.groups.set([self.friends])
        events = getAllEventsByDay(self.request, dt.date(2013,1,1), dt.date(2013,1,31))
        self.assertEqual(len(events), 31)
        evod10 = events[9]
        self.assertEqual(evod10.date, dt.date(2013,1,10))
        self.assertEqual(len(evod10.all_events), 1)
        self.assertEqual(len(evod10.days_events), 1)
        event = evod10.days_events[0]
        self.assertEqual(event.title, "Private Rendezvous")

    def testGetAllEventsByWeek(self):
        weeks = getAllEventsByWeek(self.request, 2013, 1)
        self.assertEqual(len(weeks), 5)
        self.assertIsNone(weeks[0][0])
        self.assertIsNone(weeks[0][1])
        self.assertIsNone(weeks[4][5])
        self.assertIsNone(weeks[4][6])
        evod = weeks[2][4]
        self.assertEqual(evod.date, dt.date(2013,1,17))
        self.assertEqual(len(evod.days_events), 1)
        self.assertEqual(len(evod.continuing_events), 0)

    def testGetAllUpcomingEvents(self):
        today = timezone.localdate()
        futureEvent = MultidayEventPage(owner = self.user,
                                        slug  = "tomorrow",
                                        title = "Tomorrow's Event",
                                        date_from = today + dt.timedelta(days=1),
                                        date_to   = today + dt.timedelta(days=3),
                                        time_from = dt.time(17),
                                        time_to   = dt.time(10,30))
        self.calendar.add_child(instance=futureEvent)
        events = getAllUpcomingEvents(self.request, home=self.home,
                                      holidays=self.calendar.holidays)
        self.assertEqual(len(events), 1)
        title, event, url = events[0]
        self.assertEqual(title, "Tomorrow's Event")
        self.assertEqual(event.slug, "tomorrow")
        events0 = getAllUpcomingEvents(self.request)
        self.assertEqual(len(events0), 1)

    @override_settings(JOYOUS_UPCOMING_INCLUDES_STARTED = True)
    def testGetAllCurrentEvents(self):
        today = timezone.localdate()
        futureEvent = MultidayEventPage(owner = self.user,
                                        slug  = "yesterday",
                                        title = "Yesterday's Event",
                                        date_from = today - dt.timedelta(days=1),
                                        date_to   = today + dt.timedelta(days=3),
                                        time_from = dt.time(17),
                                        time_to   = dt.time(10,30))
        self.calendar.add_child(instance=futureEvent)
        events = getAllUpcomingEvents(self.request, home=self.home)
        self.assertEqual(len(events), 1)
        title, event, url = events[0]
        self.assertEqual(title, "Yesterday's Event")
        self.assertEqual(event.slug, "yesterday")
        events0 = getAllUpcomingEvents(self.request)
        self.assertEqual(len(events0), 1)

    def testGetAllPastEvents(self):
        events = getAllPastEvents(self.request)
        self.assertEqual(len(events), 5)
        self.assertEqual(events[0].title, "Test Meeting")
        self.assertEqual(events[1].title, "A Meeting")
        self.assertEqual(events[2].title, "Meeting Postponed")
        self.assertEqual(events[3].title, "Pet Show")
        self.assertEqual(events[4].title, "All Night")

    def testGetGroupUpcomingEvents(self):
        meeting = RecurringEventPage(owner = self.user,
                                     slug  = "plan-plan",
                                     title = "Planning to Plan",
                                     repeat    = Recurrence(dtstart=dt.date(2018,5,1),
                                                            freq=WEEKLY,
                                                            byweekday=[TU]),
                                     time_from = dt.time(18,30),
                                     time_to   = dt.time(20),
                                     group_page = self.group)
        self.calendar.add_child(instance=meeting)
        memo = ExtraInfoPage(owner = self.user,
                             slug  = "plan-plan-extra-info",
                             title = "Extra Information Planning to Plan",
                             overrides = meeting,
                             except_date = meeting.next_date,
                             extra_title = "Gap Analysis",
                             extra_information = "Analyse your gaps")
        meeting.add_child(instance=memo)
        events = getGroupUpcomingEvents(self.request, self.group)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].title, "Gap Analysis")
        self.assertEqual(events[1].title, "Planning to Plan")

    def testGetGroupUpcomingEventsDupGroup(self):
        meeting = RecurringEventPage(owner = self.user,
                                     slug  = "plan-plan",
                                     title = "Planning to Plan",
                                     repeat    = Recurrence(dtstart=dt.date(2018,5,2),
                                                            freq=WEEKLY,
                                                            byweekday=[WE]),
                                     time_from = dt.time(18,30),
                                     time_to   = dt.time(20),
                                     group_page = self.group)
        self.group.add_child(instance=meeting)
        events = getGroupUpcomingEvents(self.request, self.group)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Planning to Plan")
        self.assertEqual(events[0].page.group, self.group)

    def testGetGroupUpcomingEvents2Groups(self):
        rival = GroupPage(slug = "initrode", title = "Initrode Corporation")
        self.home.add_child(instance=rival)
        meeting = RecurringEventPage(owner = self.user,
                                     slug  = "plan-plan",
                                     title = "Planning to Plan",
                                     repeat    = Recurrence(dtstart=dt.date(2018,5,2),
                                                            freq=WEEKLY,
                                                            byweekday=[WE]),
                                     time_from = dt.time(18,30),
                                     time_to   = dt.time(20),
                                     group_page = rival)
        self.group.add_child(instance=meeting)
        events = getGroupUpcomingEvents(self.request, rival)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Planning to Plan")
        # being a child of self.group trumps having group_page set
        self.assertEqual(events[0].page.group, self.group)
        events = getGroupUpcomingEvents(self.request, self.group)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, "Planning to Plan")
        self.assertEqual(events[0].page.group, self.group)

    def testGetEventFromUid(self):
        event = getEventFromUid(self.request, "29daefed-fed1-4e47-9408-43ec9b06a06d")
        self.assertEqual(event.title, "Pet Show")

    def testMultiGetEventFromUid(self):
        with self.assertRaises(MultipleObjectsReturned):
            getEventFromUid(self.request, "initiative+technology")

    def testMissingGetEventFromUid(self):
        with self.assertRaises(ObjectDoesNotExist):
            getEventFromUid(self.request, "d12971fb-e694-4a04-aba2-fb1a4a7166b9")

    def testAuthGetEventFromUid(self):
        with self.assertRaises(PermissionDenied):
            event = getEventFromUid(self.request, "80af64e7-84e6-40d9-8b4f-7edf92aab9f7")
        self.request.user.groups.set([self.friends])
        event = getEventFromUid(self.request, "80af64e7-84e6-40d9-8b4f-7edf92aab9f7")
        self.assertIsNotNone(event.title)
        self.assertEqual(event.title, "Private Rendezvous")

# ------------------------------------------------------------------------------
class TestTZ(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@foo.test', 's3cr3t')
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.calendar = GeneralCalendarPage(owner = self.user,
                                            slug  = "events",
                                            title = "Events")
        self.home.add_child(instance=self.calendar)

        self.night = RecurringEventPage(slug   = "pacnight",
                                        title  = "Pacific Night",
                                        repeat = Recurrence(dtstart=dt.date(2018,12,1),
                                                            count=1,
                                                            freq=MONTHLY,
                                                            byweekday=[SU(-1)]),
                                        time_from = dt.time(23,0),
                                        time_to   = dt.time(23,30),
                                        tz = pytz.timezone("Pacific/Pago_Pago"))
        self.calendar.add_child(instance=self.night)
        self.night.save_revision().publish()

    @timezone.override("Pacific/Kiritimati")
    def testExtremeTZGetAllEventsByDay(self):
        events = getAllEventsByDay(self.request, dt.date(2019,1,1), dt.date(2019,1,31))
        self.assertEqual(len(events), 31)
        evod1 = events[0]
        self.assertEqual(evod1.date, dt.date(2019,1,1))
        self.assertEqual(len(evod1.all_events), 1)
        self.assertEqual(len(evod1.days_events), 1)
        self.assertEqual(evod1.days_events[0].title, "Pacific Night")

# ------------------------------------------------------------------------------
class TestNoCalendar(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@foo.test', 's3cr3t')
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.request.site = Site.objects.get(is_default_site=True)
        self.group = GroupPage(slug = "initech", title = "Initech Corporation")
        self.home.add_child(instance=self.group)
        self.standup = RecurringEventPage(slug   = "test-meeting",
                                          title  = "Test Meeting",
                                          repeat = Recurrence(dtstart=dt.date(2013,1,1),
                                                              until=dt.date(2013,5,31),
                                                              freq=WEEKLY,
                                                              byweekday=[MO,WE,FR]),
                                          time_from = dt.time(13,30),
                                          time_to   = dt.time(16),
                                          uid       = "initiative+technology")
        self.group.add_child(instance=self.standup)
        self.postponement = PostponementPage(owner = self.user,
                                             slug  = "2013-01-09-postponement",
                                             title = "Postponement for Wednesday 16th of October",
                                             overrides = self.standup,
                                             except_date = dt.date(2013,1,16),
                                             cancellation_title   = "Meeting Postponed",
                                             cancellation_details =
                                                 "The meeting has been postponed until tomorrow",
                                             postponement_title   = "A Meeting",
                                             date      = dt.date(2013,1,17),
                                             time_from = dt.time(13),
                                             time_to   = dt.time(16,30),
                                             details   = "Yes a test meeting on a Thursday")
        self.standup.add_child(instance=self.postponement)

    def testGetAllEventsByDay(self):
        events = getAllEventsByDay(self.request, dt.date(2013,1,1), dt.date(2013,1,31))
        self.assertEqual(len(events), 31)
        evod2 = events[1]
        self.assertEqual(evod2.date, dt.date(2013,1,2))
        self.assertEqual(len(evod2.all_events), 1)
        self.assertEqual(len(evod2.continuing_events), 0)
        self.assertEqual(len(evod2.days_events), 1)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
