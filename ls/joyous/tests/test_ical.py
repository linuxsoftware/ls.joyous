# ------------------------------------------------------------------------------
# Test ical Format
# ------------------------------------------------------------------------------
import sys
import datetime as dt
import pytz
from django.contrib.auth.models import User
from django.test import TestCase
from wagtail.core.models import Site, Page
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, CancellationPage)
from ls.joyous.recurrence import Recurrence
from ls.joyous.recurrence import WEEKLY, MONTHLY, TU, SA
from ls.joyous.formats.ical import (VEvent, SimpleVEvent, MultidayVEvent,
        RecurringVEvent, VCalendar, ICalendarHander)
from freezegun import freeze_time
from .testutils import datetimetz


class TestVCalendar(TestCase):
    def setUp(self):
        Site.objects.update(hostname="joy.test")
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')

    @freeze_time("2018-05-12")
    def testMakeVCalendar(self):
        calendar = CalendarPage(owner = self.user,
                                slug  = "events",
                                title = "Events")
        self.home.add_child(instance=calendar)
        calendar.save_revision().publish()
        page = SimpleEventPage(owner = self.user,
                               slug  = "pet-show",
                               title = "Pet Show",
                               date  = dt.date(1987,6,5),
                               time_from = dt.time(11),
                               time_to   = dt.time(17,30),
                               tz = pytz.timezone("Australia/Sydney"))
        calendar.add_child(instance=page)
        page.save_revision().publish()
        vcal = ICalendarHander().makeVCalendar(page)
        export = vcal.export()
        aest = b'\r\n'.join([
                 b"BEGIN:STANDARD",
                 b"DTSTART;VALUE=DATE-TIME:19870315T020000",
                 b"TZNAME:AEST",
                 b"TZOFFSETFROM:+1100",
                 b"TZOFFSETTO:+1000",
                 b"END:STANDARD", ])
        aedt  = b'\r\n'.join([
                 b"BEGIN:DAYLIGHT",
                 b"DTSTART;VALUE=DATE-TIME:19871025T030000",
                 b"TZNAME:AEDT",
                 b"TZOFFSETFROM:+1000",
                 b"TZOFFSETTO:+1100",
                 b"END:DAYLIGHT", ])
        props = [b"SUMMARY:Pet Show",
                 b"DTSTART;TZID=Australia/Sydney:19870605T110000",
                 b"DTEND;TZID=Australia/Sydney:19870605T173000",
                 b"DTSTAMP:20180512T000000Z",
                 b"UID:4-pet-show@joy.test",
                 b"SEQUENCE:1",
                 b"CREATED:20180512T000000Z",
                 b"DESCRIPTION:",
                 b"LAST-MODIFIED:20180512T000000Z",
                 b"LOCATION:",
                 b"URL:http://joy.test/events/pet-show/",
                 aest,
                 aedt]
        for prop in props:
            with self.subTest(prop=prop.split(b'\r\n',1)[0]):
                self.assertIn(prop, export)

    def testEmptyCalendar(self):
        vcal = VCalendar()
        idParts = vcal['prodid'].split("//")
        self.assertEqual(len(idParts), 4)
        self.assertEqual(idParts[0], "-")
        self.assertEqual(idParts[1], "linuxsoftware.nz")
        self.assertEqual(idParts[2], "NONSGML Joyous v0.3")
        self.assertEqual(idParts[3], "EN")
        self.assertEqual(vcal['version'], "2.0")


class TestSimpleVEvent(TestCase):
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

    def testInit(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "pet-show",
                               title = "Pet Show",
                               date  = dt.date(1987,6,5),
                               time_from = dt.time(11),
                               time_to   = dt.time(17,30),
                               tz = pytz.timezone("Australia/Sydney"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vev = SimpleVEvent(page)
        tz = pytz.timezone("Australia/Sydney")
        self.assertEqual(vev['dtstart'].dt,
                         tz.localize(dt.datetime(1987,6,5,11,0)))


class TestMultidayVEvent(TestCase):
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

    def testInit(self):
        page = MultidayEventPage(owner = self.user,
                                 slug  = "niuekulele2018",
                                 title = "Niuekulele Ukulele Music Festival",
                                 date_from = dt.date(2018,3,16),
                                 date_to   = dt.date(2018,3,20),
                                 tz = pytz.timezone("Pacific/Niue"))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vev = MultidayVEvent(page)
        tz = pytz.timezone("Pacific/Niue")
        self.assertEqual(vev['dtstart'].dt,
                         tz.localize(dt.datetime(2018,3,16,0,0)))
        self.assertEqual(vev['dtend'].dt,
                         tz.localize(dt.datetime(2018,3,20,23,59,59,999999)))


class TestRecurringVEvent(TestCase):
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
    def testInit(self):
        page = RecurringEventPage(owner = self.user,
                                  slug  = "code-for-boston",
                                  title = "Code for Boston",
                                  repeat    = Recurrence(dtstart=dt.date(2017,1,1),
                                                         freq=WEEKLY,
                                                         byweekday=[TU]),
                                  time_from = dt.time(19),
                                  time_to   = dt.time(21,30),
                                  tz = pytz.timezone("US/Eastern"),
                                  location  = "4th Floor, 1 Broadway, Cambridge, MA")
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        vev = RecurringVEvent(page)
        codeForBoston = b"\r\n".join([
                b"BEGIN:VEVENT",
                b"SUMMARY:Code for Boston",
                b"DTSTART;TZID=US/Eastern:20170103T190000",
                b"DTEND;TZID=US/Eastern:20170103T213000",
                b"DTSTAMP:20170815T000000Z",
                b"UID:4-code-for-boston@joy.test",
                b"SEQUENCE:1",
                b"RRULE:FREQ=WEEKLY;BYDAY=TU;WKST=SU",
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
        vev = RecurringVEvent(page)
        tz = pytz.timezone("Pacific/Auckland")
        self.assertEqual(vev.exDates, [tz.localize(dt.datetime(2018,6,9,7)),
                                       tz.localize(dt.datetime(2018,7,14,7))])
        sleepIn = b"\r\n".join([b"BEGIN:VEVENT",
                                b"SUMMARY:Sleep In",
                                b"DTSTART;TZID=Pacific/Auckland:20180512T070000",
                                b"DTEND;TZID=Pacific/Auckland:20180512T103000",
                                b"DTSTAMP:20180510T000000Z",
                                b"UID:4-sleep@joy.test",
                                b"SEQUENCE:1",
                                b"RRULE:FREQ=MONTHLY;BYDAY=+2SA;WKST=SU",
                                b"EXDATE;TZID=Pacific/Auckland:20180609T070000,20180714T070000",
                                b"CREATED:20180510T000000Z",
                                b"DESCRIPTION:<p>zzzZZZZZZZZZ</p>",
                                b"LAST-MODIFIED:20180510T000000Z",
                                b"LOCATION:Bed",
                                b"URL:http://joy.test/events/sleep/",
                                b"END:VEVENT",
                                b""])
        self.assertEqual(vev.to_ical(), sleepIn)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
