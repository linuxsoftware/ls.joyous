# ------------------------------------------------------------------------------
# Test Event Pages
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.contrib.auth.models import User
from django.contrib.auth.models import Group, Permission
from wagtail.tests.utils import WagtailPageTests
from wagtail.tests.utils.form_data import nested_form_data, rich_text
from wagtail.core.models import Page
from ls.joyous.models.events import SimpleEventPage, MultidayEventPage, RecurringEventPage
from ls.joyous.models.events import ExtraInfoPage, CancellationPage, PostponementPage
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models.groups import get_group_model
GroupPage = get_group_model()
from ls.joyous.recurrence import Recurrence, WEEKLY, MO, WE, FR
from .testutils import skipUnlessSetup

class PageClassTests(WagtailPageTests):
    """
    Tests on the class definitions of pages - no instances required
    """
    def testCanCreateCalendar(self):
        self.assertCanCreateAt(Page, CalendarPage)

    def testCanCreateGroup(self):
        self.assertCanCreateAt(Page, GroupPage)

    def testCanCreateSimpleEvent(self):
        self.assertCanCreateAt(CalendarPage, SimpleEventPage)
        self.assertCanCreateAt(GroupPage, SimpleEventPage)
        self.assertCanNotCreateAt(Page, SimpleEventPage)

    def testCanCreateMultidayEvent(self):
        self.assertCanCreateAt(CalendarPage, MultidayEventPage)
        self.assertCanCreateAt(GroupPage, MultidayEventPage)
        self.assertCanNotCreateAt(Page, MultidayEventPage)
        self.assertCanNotCreateAt(SimpleEventPage, MultidayEventPage)

    def testCanCreateRecurringEvent(self):
        self.assertCanCreateAt(CalendarPage, RecurringEventPage)
        self.assertCanCreateAt(GroupPage, RecurringEventPage)
        self.assertCanNotCreateAt(Page, RecurringEventPage)

    def testCanCreateExtraInfo(self):
        self.assertCanCreateAt(RecurringEventPage, ExtraInfoPage)
        self.assertCanNotCreateAt(CalendarPage, ExtraInfoPage)
        self.assertCanNotCreateAt(Page, ExtraInfoPage)

    def testCanCreateCancellation(self):
        self.assertCanCreateAt(RecurringEventPage, CancellationPage)
        self.assertCanNotCreateAt(CalendarPage, CancellationPage)
        self.assertCanNotCreateAt(GroupPage, CancellationPage)

    def testCanCreatePostponement(self):
        self.assertCanCreateAt(RecurringEventPage, PostponementPage)
        self.assertCanNotCreateAt(CalendarPage, PostponementPage)
        self.assertCanNotCreateAt(MultidayEventPage, PostponementPage)

    def testSimpleEventAllows(self):
        self.assertAllowedParentPageTypes(SimpleEventPage,
                                          {CalendarPage, GroupPage})
        self.assertAllowedSubpageTypes(SimpleEventPage, {})

    def testMultidayEventAllows(self):
        self.assertAllowedParentPageTypes(MultidayEventPage,
                                          {CalendarPage, GroupPage})
        self.assertAllowedSubpageTypes(MultidayEventPage, {})

    def testRecurringEventAllows(self):
        self.assertAllowedParentPageTypes(RecurringEventPage,
                                          {CalendarPage, GroupPage})
        self.assertAllowedSubpageTypes(RecurringEventPage,
                                       {ExtraInfoPage, CancellationPage,
                                        PostponementPage})

    def testExtraInfoAllows(self):
        self.assertAllowedParentPageTypes(ExtraInfoPage, {RecurringEventPage})
        self.assertAllowedSubpageTypes(ExtraInfoPage, {})

    def testCancellationAllows(self):
        self.assertAllowedParentPageTypes(CancellationPage, {RecurringEventPage})
        self.assertAllowedSubpageTypes(CancellationPage, {})

    def testPostponementAllows(self):
        self.assertAllowedParentPageTypes(PostponementPage, {RecurringEventPage})
        self.assertAllowedSubpageTypes(PostponementPage, {})


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
                                               'intro': rich_text("<h4>What's happening</h4>")}))

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

