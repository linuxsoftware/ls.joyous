# ------------------------------------------------------------------------------
# Test Get Event Functions
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
import calendar
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.core.models import Page
from ls.joyous.recurrence import Recurrence
from ls.joyous.recurrence import DAILY, WEEKLY, MONTHLY, MO, TU, WE, TH, FR, WEEKEND, EVERYDAY
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.events import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, PostponementPage, ExtraInfoPage)
from ls.joyous.models.events import (getAllEventsByDay, getAllEventsByWeek,
        getAllUpcomingEvents, getAllPastEvents, getGroupUpcomingEvents)
from ls.joyous.models.groups import get_group_model
from .testutils import datetimetz

GroupPage = get_group_model()

class TestGetEvents(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@foo.test', 's3cr3t')
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.calendar = CalendarPage(owner = self.user,
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
                                    time_to   = dt.time(17,30))
        self.calendar.add_child(instance=self.show)

        self.party = MultidayEventPage(owner = self.user,
                                       slug  = "allnighter",
                                       title = "All Night",
                                       date_from = dt.date(2012,12,31),
                                       date_to   = dt.date(2013,1,1),
                                       time_from = dt.time(23),
                                       time_to   = dt.time(3))
        self.calendar.add_child(instance=self.party)

        self.standup = RecurringEventPage(slug   = "test-meeting",
                                          title  = "Test Meeting",
                                          repeat = Recurrence(dtstart=dt.date(2013,1,1),
                                                              until=dt.date(2013,5,31),
                                                              freq=WEEKLY,
                                                              byweekday=[MO,WE,FR]),
                                          time_from = dt.time(13,30),
                                          time_to   = dt.time(16))
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
        evod = events[0]
        self.assertEqual(evod.date, dt.date(2013,1,1))
        self.assertEqual(len(evod.all_events), 1)
        self.assertEqual(len(evod.days_events), 0)
        self.assertEqual(len(evod.continuing_events), 1)

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
        events = getAllUpcomingEvents(self.request, self.home)
        self.assertEqual(len(events), 1)
        title, event = events[0]
        self.assertEqual(title, "Tomorrow's Event")
        self.assertEqual(event.slug, "tomorrow")
        events0 = getAllUpcomingEvents(self.request)
        self.assertEqual(len(events0), 1)

    def testGetAllPastEvents(self):
        events = getAllPastEvents(self.request)
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0].title, "Test Meeting")
        self.assertEqual(events[1].title, "A Meeting")
        self.assertEqual(events[2].title, "Pet Show")
        self.assertEqual(events[3].title, "All Night")

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

