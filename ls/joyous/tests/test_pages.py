# ------------------------------------------------------------------------------
# Test Event Pages
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.contrib.auth.models import User
from django.contrib.auth.models import Group, Permission
from django.utils import translation
from wagtail.tests.utils import WagtailPageTests
from wagtail.tests.utils.form_data import nested_form_data, rich_text
from wagtail.core.models import Page
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, MultidayRecurringEventPage, ExtraInfoPage,
        CancellationPage, PostponementPage, RescheduleMultidayEventPage,
        CalendarPage, SpecificCalendarPage, GeneralCalendarPage)
from ls.joyous.models.groups import get_group_model
GroupPage = get_group_model()
from ls.joyous.utils.recurrence import Recurrence, WEEKLY, MO, WE, FR
from .testutils import skipUnlessSetup

# ------------------------------------------------------------------------------
class PageClassTests(WagtailPageTests):
    """
    Tests on the class definitions of pages - no instances required
    """
    def testCanCreateCalendar(self):
        self.assertCanCreateAt(Page, CalendarPage)

    def testCanCreateSpecificCalendar(self):
        self.assertCanCreateAt(Page, SpecificCalendarPage)

    def testCanCreateGeneralCalendar(self):
        self.assertCanCreateAt(Page, GeneralCalendarPage)

    def testCanCreateGroup(self):
        self.assertCanCreateAt(Page, GroupPage)

    def testCanCreateSimpleEvent(self):
        self.assertCanCreateAt(CalendarPage, SimpleEventPage)
        self.assertCanCreateAt(SpecificCalendarPage, SimpleEventPage)
        self.assertCanCreateAt(GeneralCalendarPage, SimpleEventPage)
        self.assertCanCreateAt(GroupPage, SimpleEventPage)
        self.assertCanNotCreateAt(Page, SimpleEventPage)

    def testCanCreateMultidayEvent(self):
        self.assertCanCreateAt(CalendarPage, MultidayEventPage)
        self.assertCanCreateAt(SpecificCalendarPage, MultidayEventPage)
        self.assertCanCreateAt(GeneralCalendarPage, MultidayEventPage)
        self.assertCanCreateAt(GroupPage, MultidayEventPage)
        self.assertCanNotCreateAt(Page, MultidayEventPage)
        self.assertCanNotCreateAt(SimpleEventPage, MultidayEventPage)

    def testCanCreateRecurringEvent(self):
        self.assertCanCreateAt(CalendarPage, RecurringEventPage)
        self.assertCanCreateAt(SpecificCalendarPage, RecurringEventPage)
        self.assertCanCreateAt(GeneralCalendarPage, RecurringEventPage)
        self.assertCanCreateAt(GroupPage, RecurringEventPage)
        self.assertCanNotCreateAt(Page, RecurringEventPage)

    def testCanCreateMultidayRecurringEvent(self):
        self.assertCanCreateAt(CalendarPage, MultidayRecurringEventPage)
        self.assertCanCreateAt(SpecificCalendarPage, MultidayRecurringEventPage)
        self.assertCanCreateAt(GeneralCalendarPage, MultidayRecurringEventPage)
        self.assertCanCreateAt(GroupPage, MultidayRecurringEventPage)
        self.assertCanNotCreateAt(Page, MultidayRecurringEventPage)

    def testCanCreateExtraInfo(self):
        self.assertCanCreateAt(RecurringEventPage, ExtraInfoPage)
        self.assertCanCreateAt(MultidayRecurringEventPage, ExtraInfoPage)
        self.assertCanNotCreateAt(CalendarPage, ExtraInfoPage)
        self.assertCanNotCreateAt(SpecificCalendarPage, ExtraInfoPage)
        self.assertCanNotCreateAt(GeneralCalendarPage, ExtraInfoPage)
        self.assertCanNotCreateAt(Page, ExtraInfoPage)

    def testCanCreateCancellation(self):
        self.assertCanCreateAt(RecurringEventPage, CancellationPage)
        self.assertCanCreateAt(MultidayRecurringEventPage, CancellationPage)
        self.assertCanNotCreateAt(CalendarPage, CancellationPage)
        self.assertCanNotCreateAt(SpecificCalendarPage, ExtraInfoPage)
        self.assertCanNotCreateAt(GeneralCalendarPage, ExtraInfoPage)
        self.assertCanNotCreateAt(GroupPage, CancellationPage)

    def testCanCreatePostponement(self):
        self.assertCanCreateAt(RecurringEventPage, PostponementPage)
        self.assertCanCreateAt(MultidayRecurringEventPage, RescheduleMultidayEventPage)
        self.assertCanNotCreateAt(CalendarPage, PostponementPage)
        self.assertCanNotCreateAt(SpecificCalendarPage, ExtraInfoPage)
        self.assertCanNotCreateAt(GeneralCalendarPage, ExtraInfoPage)
        self.assertCanNotCreateAt(MultidayEventPage, PostponementPage)

    def testSimpleEventAllows(self):
        self.assertAllowedParentPageTypes(SimpleEventPage, {CalendarPage,
                                                            SpecificCalendarPage,
                                                            GeneralCalendarPage,
                                                            GroupPage})
        self.assertAllowedSubpageTypes(SimpleEventPage, {})

    def testMultidayEventAllows(self):
        self.assertAllowedParentPageTypes(MultidayEventPage, {CalendarPage,
                                                              SpecificCalendarPage,
                                                              GeneralCalendarPage,
                                                              GroupPage})
        self.assertAllowedSubpageTypes(MultidayEventPage, {})

    def testRecurringEventAllows(self):
        self.assertAllowedParentPageTypes(RecurringEventPage, {CalendarPage,
                                                               SpecificCalendarPage,
                                                               GeneralCalendarPage,
                                                               GroupPage})
        self.assertAllowedSubpageTypes(RecurringEventPage,
                                       {ExtraInfoPage, CancellationPage,
                                        PostponementPage})


    def testMultidayRecurringEventAllows(self):
        self.assertAllowedParentPageTypes(MultidayRecurringEventPage,
                                          {CalendarPage,
                                           SpecificCalendarPage,
                                           GeneralCalendarPage,
                                           GroupPage})
        self.assertAllowedSubpageTypes(MultidayRecurringEventPage,
                                       {ExtraInfoPage, CancellationPage,
                                        RescheduleMultidayEventPage})

    def testExtraInfoAllows(self):
        self.assertAllowedParentPageTypes(ExtraInfoPage,
                                          {RecurringEventPage,
                                           MultidayRecurringEventPage})
        self.assertAllowedSubpageTypes(ExtraInfoPage, {})

    def testCancellationAllows(self):
        self.assertAllowedParentPageTypes(CancellationPage,
                                          {RecurringEventPage,
                                           MultidayRecurringEventPage})
        self.assertAllowedSubpageTypes(CancellationPage, {})

    def testPostponementAllows(self):
        self.assertAllowedParentPageTypes(PostponementPage,
                                          {RecurringEventPage})
        self.assertAllowedSubpageTypes(PostponementPage, {})

    def testRescheduleMultidayEventAllows(self):
        self.assertAllowedParentPageTypes(RescheduleMultidayEventPage,
                                          {MultidayRecurringEventPage})
        self.assertAllowedSubpageTypes(RescheduleMultidayEventPage, {})

    def testCalendarVerboseName(self):
        self.assertEqual(CalendarPage.get_verbose_name(),
                         "Calendar page")

    def testSpecificCalendarVerboseName(self):
        self.assertEqual(SpecificCalendarPage.get_verbose_name(),
                         "Specific calendar page")

    def testGeneralCalendarVerboseName(self):
        self.assertEqual(GeneralCalendarPage.get_verbose_name(),
                         "General calendar page")

    def testSimpleEventVerboseName(self):
        self.assertEqual(SimpleEventPage.get_verbose_name(),
                         "Event page")

    def testMultidayEventVerboseName(self):
        self.assertEqual(MultidayEventPage.get_verbose_name(),
                         "Multiday event page")

    def testRecurringEventVerboseName(self):
        self.assertEqual(RecurringEventPage.get_verbose_name(),
                         "Recurring event page")

    def testMultidayRecurringEventVerboseName(self):
        self.assertEqual(MultidayRecurringEventPage.get_verbose_name(),
                         "Multiday recurring event page")

    def testExtraInfoVerboseName(self):
        self.assertEqual(ExtraInfoPage.get_verbose_name(),
                         "Extra event information")

    def testCancellationVerboseName(self):
        self.assertEqual(CancellationPage.get_verbose_name(),
                         "Cancellation")

    def testPostponementVerboseName(self):
        self.assertEqual(PostponementPage.get_verbose_name(),
                         "Postponement")

    def testRescheduleMultidayEventVerboseName(self):
        self.assertEqual(RescheduleMultidayEventPage.get_verbose_name(),
                         "Postponement")

# ------------------------------------------------------------------------------
class PageClassTestsFrançais(WagtailPageTests):
    def setUp(self):
        translation.activate('fr')

    def tearDown(self):
        translation.deactivate()

    def testCalendarVerboseName(self):
        self.assertEqual(CalendarPage.get_verbose_name(),
                         "Page de calendrier")

    def testSpecificCalendarVerboseName(self):
        self.assertEqual(SpecificCalendarPage.get_verbose_name(),
                         "Page de calendrier spécifique")

    def testGeneralCalendarVerboseName(self):
        self.assertEqual(GeneralCalendarPage.get_verbose_name(),
                         "Page de calendrier générale")

    def testSimpleEventVerboseName(self):
        self.assertEqual(SimpleEventPage.get_verbose_name(),
                         "Page de l'événement")

    def testMultidayEventVerboseName(self):
        self.assertEqual(MultidayEventPage.get_verbose_name(),
                         "Page de l'événement sur plusieurs jours")

    def testRecurringEventVerboseName(self):
        self.assertEqual(RecurringEventPage.get_verbose_name(),
                         "Page d'événement récurrent")

    def testMultidayRecurringEventVerboseName(self):
        self.assertEqual(MultidayRecurringEventPage.get_verbose_name(),
                         "Page d'événements récurrents sur plusieurs jours")

    def testExtraInfoVerboseName(self):
        self.assertEqual(ExtraInfoPage.get_verbose_name(),
                         "Informations supplémentaires sur l'événement")

    def testCancellationVerboseName(self):
        self.assertEqual(CancellationPage.get_verbose_name(),
                         "Annulation")

    def testPostponementVerboseName(self):
        self.assertEqual(PostponementPage.get_verbose_name(),
                         "Report")

    def testRescheduleMultidayEventVerboseName(self):
        self.assertEqual(RescheduleMultidayEventPage.get_verbose_name(),
                         "Report")

# ------------------------------------------------------------------------------
class PageInstanceTests(WagtailPageTests):
    """
    Tests with instantiated pages
    """
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3(r3t')
        self.user.groups.add(Group.objects.get(name="Moderators"))
        self.client.force_login(self.user)
        try:
            self.home = Page.objects.get(slug='home')
            self.group = GroupPage(slug  = "test-group",
                                   title = "Test Group")
            self.home.add_child(instance=self.group)
            self.event = RecurringEventPage(slug      = "test-meeting",
                                            title     = "Test Meeting",
                                            repeat    = Recurrence(dtstart=dt.date(2009,8,7),
                                                                   freq=WEEKLY,
                                                                   byweekday=[MO,WE,FR]),
                                            time_from = dt.time(13))
            self.group.add_child(instance=self.event)
        except:
            pass

    def testCanCreateCalendar(self):
        self.assertCanCreate(self.home, CalendarPage,
                             nested_form_data({'title': "Calendar",
                                               'intro': rich_text("<h4>What's happening</h4>"),
                                               'default_view': "M"}))

    def testCanCreateSpecificCalendar(self):
        SpecificCalendarPage.is_creatable = True
        self.assertCanCreate(self.home, SpecificCalendarPage,
                             nested_form_data({'title': "Calendar",
                                               'intro': rich_text("<h4>What's happening</h4>"),
                                               'default_view': "M"}))

    def testCanCreateGeneralCalendar(self):
        GeneralCalendarPage.is_creatable = True
        self.assertCanCreate(self.home, GeneralCalendarPage,
                             nested_form_data({'title': "Calendar",
                                               'intro': rich_text("<h4>What's happening</h4>"),
                                               'default_view': "L"}))

    def testCanCreateGroup(self):
        self.assertCanCreate(self.home, GroupPage,
                             nested_form_data({'title': "Moreporks Club",
                                               'intro': rich_text("<h4>Welcome to the club</h4>")}))

    @skipUnlessSetup("group")
    def testCanCreateSimpleEvent(self):
        self.assertCanCreate(self.group, SimpleEventPage,
                             nested_form_data({'title':      "Mouse Hunt",
                                               'date':       dt.date(1987,6,5),
                                               'tz':         pytz.timezone("Pacific/Auckland"),
                                               'details':    rich_text("<p>Hello Micee</p>")}))

    @skipUnlessSetup("group")
    def testCanCreateMultidayEvent(self):
        self.assertCanCreate(self.group, MultidayEventPage,
                             nested_form_data({'title':      "Camp QA",
                                               'date_from':  dt.date(1987,7,10),
                                               'date_to':    dt.date(1987,7,12),
                                               'time_from':  dt.time(17),
                                               'time_to':    dt.time(14,30),
                                               'tz':         pytz.timezone("Pacific/Auckland"),
                                               'details':    rich_text("<p>Hello World</p>")}))

    @skipUnlessSetup("group")
    def testCanCreateRecurringEvent(self):
        self.assertCanCreate(self.group, RecurringEventPage,
                             nested_form_data({'title':      "Stand up",
                                               'repeat_0':   dt.date(1987,6,7),
                                               'repeat_1':   2,                    # weekly
                                               'repeat_2':   1,                    # every week
                                               'repeat_3':   {0:0, 1:1, 2:2, 4:4}, # Mon,Tue,Wed,Fri
                                               'time_from':  dt.time(9),
                                               'time_to':    dt.time(10),
                                               'tz':         pytz.timezone("Pacific/Auckland"),
                                               'details':
                                                   rich_text("<p>Stand up straight!</p>")}))

    @skipUnlessSetup("group")
    def testCanCreateMultidayRecurringEvent(self):
        self.assertCanCreate(self.group, MultidayRecurringEventPage,
                             nested_form_data({'title':      "Team Retreat",
                                               'repeat_0':   dt.date(1987,8,7),
                                               'repeat_1':   0,                    # yearly
                                               'repeat_2':   1,                    # every year
                                               'repeat_6':   1,                    # the first
                                               'repeat_7':   4,                    # Friday of
                                               'repeat_12':  {8:8},                # August
                                               'num_days':   3,
                                               'time_from':  dt.time(17),
                                               'tz':         pytz.timezone("Pacific/Auckland"),
                                               'details':
                                                   rich_text("<p>Three days of T-E-A-M</p>")}))

    @skipUnlessSetup("event")
    def testCanCreateExtraInfo(self):
        self.assertCanCreate(self.event, ExtraInfoPage,
                             nested_form_data({'overrides':  self.event.id,
                                               'except_date':dt.date(2009,8,14),
                                               'extra_information':
                                                   rich_text("<h3>A special announcement</h3>")}))

    @skipUnlessSetup("event")
    def testCanCreateCancellation(self):
        self.assertCanCreate(self.event, CancellationPage,
                             nested_form_data({'overrides':            self.event.id,
                                               'except_date':          dt.date(2009,8,14),
                                               'cancellation_title':   "Meeting Cancelled",
                                               'cancellation_details':
                                                   rich_text("<p>No meeting today</p>")}))

    @skipUnlessSetup("event")
    def testCanCreatePostponement(self):
        self.assertCanCreate(self.event, PostponementPage,
                             nested_form_data({'overrides':            self.event.id,
                                               'except_date':          dt.date(2009,8,16),
                                               'cancellation_title':   "Meeting Postponed",
                                               'cancellation_details':
                                                   rich_text("<p>Meeting will be held tommorrow</p>"),
                                               'postponement_title':   "Test Meeting",
                                               'date':                 dt.date(2009,8,15),
                                               'time_from':            dt.time(13)}))

    def testCanCancelMultidayEvent(self):
        event2 = MultidayRecurringEventPage(slug      = "test-session",
                                            title     = "Test Session",
                                            repeat    = Recurrence(dtstart=dt.date(2009,8,7),
                                                                   freq=WEEKLY,
                                                                   byweekday=[MO,WE,FR]),
                                            num_days  = 2,
                                            time_from = dt.time(10))
        self.group.add_child(instance=event2)
        self.assertCanCreate(event2, CancellationPage,
                             nested_form_data({'overrides':            self.event.id,
                                               'except_date':          dt.date(2009,8,14),
                                               'cancellation_title':   "Session Cancelled" }))

    def testCanRescheduleMultidayEvent(self):
        event2 = MultidayRecurringEventPage(slug      = "test-session",
                                            title     = "Test Session",
                                            repeat    = Recurrence(dtstart=dt.date(2009,8,7),
                                                                   freq=WEEKLY,
                                                                   byweekday=[MO,WE,FR]),
                                            num_days  = 2,
                                            time_from = dt.time(10))
        self.group.add_child(instance=event2)
        self.assertCanCreate(event2, RescheduleMultidayEventPage,
                             nested_form_data({'overrides':            self.event.id,
                                               'except_date':          dt.date(2009,8,16),
                                               'postponement_title':   "Shortened cycle",
                                               'date':                 dt.date(2009,8,16),
                                               'num_days':             1,
                                               'time_from':            dt.time(10)}))

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
