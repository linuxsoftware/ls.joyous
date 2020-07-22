# ------------------------------------------------------------------------------
# Test ical Format
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from icalendar import vDatetime
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from wagtail.core.models import Site, Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, MultidayRecurringEventPage,
        CancellationPage, ExtraInfoPage, PostponementPage)
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import DAILY, WEEKLY, MONTHLY, TU, SA
from ls.joyous.formats.ical import (SimpleVEvent, MultidayVEvent,
        RecurringVEvent, MultidayRecurringVEvent, ExtraInfoVEvent,
        PostponementVEvent, CancellationVEvent, VEventFactory, VEvent)
from freezegun import freeze_time

# ------------------------------------------------------------------------------
class TestBase(TestCase):
    def testMakePage(self):
        vev = VEvent()
        with self.assertRaises(NotImplementedError):
            vev.makePage()

# ------------------------------------------------------------------------------
class TestSimple(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    def testFromPage(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "pet-show",
                               title = "Pet Show",
                               date  = dt.date(1987,6,5),
                               time_from = dt.time(11),
                               time_to   = dt.time(17,30),
                               tz = pytz.timezone("Australia/Sydney"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vev = VEventFactory().makeFromPage(page, self.calendar)
        self.assertIs(type(vev), SimpleVEvent)
        tz = pytz.timezone("Australia/Sydney")
        self.assertEqual(vev['DTSTART'].dt,
                         tz.localize(dt.datetime(1987,6,5,11,0)))

# ------------------------------------------------------------------------------
class TestMultiday(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    def testFromPage(self):
        page = MultidayEventPage(owner = self.user,
                                 slug  = "niuekulele2018",
                                 title = "Niuekulele Ukulele Music Festival",
                                 date_from = dt.date(2018,3,16),
                                 date_to   = dt.date(2018,3,20),
                                 tz = pytz.timezone("Pacific/Niue"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vev = VEventFactory().makeFromPage(page, self.calendar)
        self.assertIs(type(vev), MultidayVEvent)
        tz = pytz.timezone("Pacific/Niue")
        self.assertEqual(vev['DTSTART'].dt,
                         tz.localize(dt.datetime(2018,3,16,0,0)))
        self.assertEqual(vev['DTEND'].dt,
                         tz.localize(dt.datetime(2018,3,20,23,59,59,999999)))

# ------------------------------------------------------------------------------
class TestRecurring(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    @freeze_time("2017-08-15")
    def testFromPage(self):
        page = RecurringEventPage(owner = self.user,
                                  slug  = "code-for-boston",
                                  title = "Code for Boston",
                                  repeat    = Recurrence(dtstart=dt.date(2017,1,1),
                                                         freq=WEEKLY,
                                                         byweekday=[TU],
                                                         until=dt.date(2017,12,26)),
                                  time_from = dt.time(19),
                                  time_to   = dt.time(21,30),
                                  tz = pytz.timezone("US/Eastern"),
                                  location  = "4th Floor, 1 Broadway, Cambridge, MA")
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vev = VEventFactory().makeFromPage(page, self.calendar)
        self.assertIs(type(vev), RecurringVEvent)
        vev.set('UID', "this-is-not-a-unique-identifier")
        codeForBoston = b"\r\n".join([
                b"BEGIN:VEVENT",
                b"SUMMARY:Code for Boston",
                b"DTSTART;TZID=US/Eastern:20170103T190000",
                b"DTEND;TZID=US/Eastern:20170103T213000",
                b"DTSTAMP:20170815T000000Z",
                b"UID:this-is-not-a-unique-identifier",
                b"SEQUENCE:1",
                b"RRULE:FREQ=WEEKLY;UNTIL=20171227T045959Z;BYDAY=TU;WKST=SU",
                b"CREATED:20170815T000000Z",
                b"DESCRIPTION:",
                b"LAST-MODIFIED:20170815T000000Z",
                b"LOCATION:4th Floor\\, 1 Broadway\\, Cambridge\\, MA",
                b"URL:http://joy.test/events/code-for-boston/",
                b"END:VEVENT",
                b""])
        self.assertEqual(vev.to_ical(), codeForBoston)

    @freeze_time("2018-05-10")
    def testExdate(self):
        page = RecurringEventPage(owner = self.user,
                                  slug  = "sleep",
                                  title = "Sleep In",
                                  repeat    = Recurrence(dtstart=dt.date(2018,5,1),
                                                         freq=MONTHLY,
                                                         byweekday=[SA(+2)]),
                                  time_from = dt.time(7),
                                  time_to   = dt.time(10,30),
                                  tz = pytz.timezone("Pacific/Auckland"),
                                  details = "<p>zzzZZZZZZZZZ</p>",
                                  location  = "Bed")
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        except1 = CancellationPage(owner = self.user,
                                   slug  = "2018-06-09-cancellation",
                                   title = "Cancellation for Saturday 9th of June",
                                   overrides = page,
                                   except_date = dt.date(2018,6,9))
        page.add_child(instance=except1)
        except1.save_revision().publish()
        except2 = CancellationPage(owner = self.user,
                                   slug  = "2018-07-14-cancellation",
                                   title = "Cancellation for Saturday 14th of July",
                                   overrides = page,
                                   except_date = dt.date(2018,7,14))
        page.add_child(instance=except2)
        except2.save_revision().publish()
        vev = VEventFactory().makeFromPage(except1, self.calendar)
        self.assertIs(type(vev), RecurringVEvent)
        vev.set('UID', "this-is-not-a-unique-identifier")
        tz = pytz.timezone("Pacific/Auckland")
        exDates = [exDate.dt for exDate in vev['EXDATE'].dts]
        self.assertEqual(exDates, [tz.localize(dt.datetime(2018,6,9,7)),
                                   tz.localize(dt.datetime(2018,7,14,7))])
        sleepIn = b"\r\n".join([b"BEGIN:VEVENT",
                                b"SUMMARY:Sleep In",
                                b"DTSTART;TZID=Pacific/Auckland:20180512T070000",
                                b"DTEND;TZID=Pacific/Auckland:20180512T103000",
                                b"DTSTAMP:20180510T000000Z",
                                b"UID:this-is-not-a-unique-identifier",
                                b"SEQUENCE:1",
                                b"RRULE:FREQ=MONTHLY;BYDAY=+2SA;WKST=SU",
                                b"EXDATE;TZID=Pacific/Auckland:20180609T070000,20180714T070000",
                                b"CREATED:20180510T000000Z",
                                b"DESCRIPTION:zzzZZZZZZZZZ",
                                b"LAST-MODIFIED:20180510T000000Z",
                                b"LOCATION:Bed",
                                b"URL:http://joy.test/events/sleep/",
                                b"X-ALT-DESC;FMTTYPE=text/html:<p>zzzZZZZZZZZZ</p>",
                                b"END:VEVENT",
                                b""])
        self.assertEqual(vev.to_ical(), sleepIn)

    @freeze_time("2017-05-15")
    def testExtraInfo(self):
        page = RecurringEventPage(owner = self.user,
                                  slug  = "code-for-boston",
                                  title = "Code for Boston",
                                  repeat    = Recurrence(dtstart=dt.date(2017,1,1),
                                                         freq=WEEKLY,
                                                         byweekday=[TU],
                                                         until=dt.date(2017,12,26)),
                                  time_from = dt.time(19),
                                  time_to   = dt.time(21,30),
                                  tz = pytz.timezone("US/Eastern"),
                                  location  = "4th Floor, 1 Broadway, Cambridge, MA")
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        info = ExtraInfoPage(owner = self.user,
                             slug  = "2017-06-06-extra-info",
                             title = "Extra Information for Tuesday 6th of June",
                             overrides = page,
                             except_date = dt.date(2017,6,6),
                             extra_title = "Handling Time Zones with Python")
        page.add_child(instance=info)
        info.save_revision().publish()
        vev = VEventFactory().makeFromPage(page, self.calendar)
        self.assertIs(type(vev), RecurringVEvent)
        vev.set('UID', "this-is-not-a-unique-identifier")
        codeForBoston = b"\r\n".join([
                b"BEGIN:VEVENT",
                b"SUMMARY:Code for Boston",
                b"DTSTART;TZID=US/Eastern:20170103T190000",
                b"DTEND;TZID=US/Eastern:20170103T213000",
                b"DTSTAMP:20170515T000000Z",
                b"UID:this-is-not-a-unique-identifier",
                b"SEQUENCE:1",
                b"RRULE:FREQ=WEEKLY;UNTIL=20171227T045959Z;BYDAY=TU;WKST=SU",
                b"CREATED:20170515T000000Z",
                b"DESCRIPTION:",
                b"LAST-MODIFIED:20170515T000000Z",
                b"LOCATION:4th Floor\\, 1 Broadway\\, Cambridge\\, MA",
                b"URL:http://joy.test/events/code-for-boston/",
                b"END:VEVENT",
                b""])
        self.assertEqual(vev.to_ical(), codeForBoston)
        self.assertEqual(len(vev.vchildren), 1)
        vchild = vev.vchildren[0]
        vchild.set('UID', "this-is-not-a-unique-identifier")
        self.assertIs(type(vchild), ExtraInfoVEvent)
        talk = b"\r\n".join([
                b"BEGIN:VEVENT",
                b"SUMMARY:Handling Time Zones with Python",
                b"DTSTART;TZID=US/Eastern:20170606T190000",
                b"DTEND;TZID=US/Eastern:20170606T213000",
                b"DTSTAMP:20170515T000000Z",
                b"UID:this-is-not-a-unique-identifier",
                b"RECURRENCE-ID;TZID=US/Eastern:20170606T190000",
                b"SEQUENCE:1",
                b"CREATED:20170515T000000Z",
                b"DESCRIPTION:",
                b"LAST-MODIFIED:20170515T000000Z",
                b"LOCATION:4th Floor\\, 1 Broadway\\, Cambridge\\, MA",
                b"URL:http://joy.test/events/code-for-boston/2017-06-06-extra-info/" ,
                b"END:VEVENT",
                b""])
        self.assertEqual(vchild.to_ical(), talk)

    @freeze_time("2017-05-15")
    def testPostponement(self):
        page = RecurringEventPage(owner = self.user,
                                  slug  = "code-for-boston",
                                  title = "Code for Boston",
                                  repeat    = Recurrence(dtstart=dt.date(2017,1,1),
                                                         freq=WEEKLY,
                                                         byweekday=[TU],
                                                         until=dt.date(2017,12,26)),
                                  time_from = dt.time(19),
                                  time_to   = dt.time(21,30),
                                  tz = pytz.timezone("US/Eastern"),
                                  location  = "4th Floor, 1 Broadway, Cambridge, MA")
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        post = PostponementPage(owner = self.user,
                                slug  = "2017-06-13-postponement",
                                title = "Postponement for Tuesday 13th of June",
                                postponement_title = "Code for Boston (on Weds)",
                                overrides = page,
                                except_date = dt.date(2017,6,13),
                                date = dt.date(2017,6,14)
                                )
        page.add_child(instance=post)
        post.save_revision().publish()
        vev = VEventFactory().makeFromPage(page, self.calendar)
        self.assertIs(type(vev), RecurringVEvent)
        self.assertEqual(len(vev.vchildren), 1)
        vchild = vev.vchildren[0]
        vchild.set('UID', "this-is-not-a-unique-identifier")
        self.assertIs(type(vchild), PostponementVEvent)
        talk = b"\r\n".join([
                b"BEGIN:VEVENT",
                b"SUMMARY:Code for Boston (on Weds)",
                b"DTSTART;TZID=US/Eastern:20170614T000000",
                b"DTEND;TZID=US/Eastern:20170614T235959",
                b"DTSTAMP:20170515T000000Z",
                b"UID:this-is-not-a-unique-identifier",
                b"RECURRENCE-ID;TZID=US/Eastern:20170613T190000",
                b"SEQUENCE:1",
                b"CREATED:20170515T000000Z",
                b"DESCRIPTION:",
                b"LAST-MODIFIED:20170515T000000Z",
                b"LOCATION:",
                b"URL:http://joy.test/events/code-for-boston/2017-06-13-postponement/",
                b"END:VEVENT",
                b""])
        self.assertEqual(vchild.to_ical(), talk)

    @freeze_time("2017-05-15")
    def testCancellation(self):
        # NOTE:
        # Cancellations are represented by EXDATE in VEVENT not as their own
        # VEVENT instance.  Yes, this means the cancellation_title and
        # cancellation_details are lost.
        page = RecurringEventPage(owner = self.user,
                                  slug  = "sleep",
                                  title = "Sleep In",
                                  repeat    = Recurrence(dtstart=dt.date(2018,5,1),
                                                         freq=MONTHLY,
                                                         byweekday=[SA(+2)]),
                                  time_from = dt.time(7),
                                  time_to   = dt.time(10,30),
                                  tz = pytz.timezone("Pacific/Auckland"),
                                  details = "<p>zzzZZZZZZZZZ</p>",
                                  location  = "Bed")
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        except1 = CancellationPage(owner = self.user,
                                   slug  = "2018-06-09-cancellation",
                                   title = "Cancellation for Saturday 9th of June",
                                   cancellation_title = "Get up early",
                                   overrides = page,
                                   except_date = dt.date(2018,6,9))
        page.add_child(instance=except1)
        except1.save_revision().publish()
        vexcept = CancellationVEvent.fromPage(except1)
        self.assertEqual(vexcept['SUMMARY'], "Get up early")
        self.assertEqual(vexcept['DESCRIPTION'], "")
        self.assertEqual(vexcept.to_ical(), b"\r\n")

# ------------------------------------------------------------------------------
class TestMultidayRecurring(TestCase):
    def setUp(self):
        site = Site.objects.get(is_default_site=True)
        site.hostname = "joy.test"
        site.save()
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    @freeze_time("2017-08-15")
    def testFromPage(self):
        page = MultidayRecurringEventPage(owner = self.user,
                                  slug   = "bought-from-rubber-man",
                                  title  = "Bought from a Rubber Man",
                                  repeat = Recurrence(dtstart=dt.date(2019,4,2),
                                                      freq=WEEKLY,
                                                      byweekday=[TU]),
                                  num_days  = 3,
                                  time_from = dt.time(16),
                                  time_to   = dt.time(18),
                                  tz = pytz.timezone("Pacific/Auckland"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vev = VEventFactory().makeFromPage(page, self.calendar)
        self.assertIs(type(vev), MultidayRecurringVEvent)
        tz = pytz.timezone("Pacific/Auckland")
        self.assertEqual(vev['DTSTART'].dt,
                         tz.localize(dt.datetime(2019,4,2,16,0)))
        self.assertEqual(vev['DTEND'].dt,
                         tz.localize(dt.datetime(2019,4,4,18,0)))
        self.assertEqual(vev['RRULE']['FREQ'],  ["WEEKLY"])
        self.assertEqual(vev['RRULE']['BYDAY'], ["TU"])

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
