# ------------------------------------------------------------------------------
# Test Recurrence
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase
from ls.joyous.recurrence import Recurrence, Weekday
from ls.joyous.recurrence import MO, TU, WE, TH, FR, SA, SU
from ls.joyous.recurrence import YEARLY, MONTHLY, WEEKLY, DAILY

# ------------------------------------------------------------------------------
class TestWeekday(TestCase):
    def testStr(self):
        self.assertEqual(str(Weekday(0)), "Monday")
        self.assertEqual(str(Weekday(4,1)), "first Friday")
        self.assertEqual(str(Weekday(4,-1)), "last Friday")
        self.assertEqual(str(SA), "Saturday")
        self.assertEqual(str(FR(3)), "third Friday")

    def testGetWhen(self):
        self.assertEqual(Weekday(0)._getWhen(0), "Monday")
        self.assertEqual(FR(1)._getWhen(0), "first Friday")
        self.assertEqual(SU._getWhen(1), "Monday")
        self.assertEqual(WE._getWhen(-2), "Monday")
        self.assertEqual(FR(1)._getWhen(-1), "Thursday before the first Friday")
        self.assertEqual(SU(1)._getWhen(2), "Tuesday after the first Sunday")

    def testRepr(self):
        self.assertEqual(repr(Weekday(0)), "MO")
        self.assertEqual(repr(Weekday(4,2)), "+2FR")
        self.assertEqual(repr(SA), "SA")
        self.assertEqual(repr(FR(3)), "+3FR")
        self.assertEqual(repr(WE(-2)), "-2WE")

# ------------------------------------------------------------------------------
class TestRecurrence(TestCase):
    def testRepr(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=WEEKLY,
                        count=9,
                        byweekday=[MO,TU,WE,TH,FR])
        self.assertEqual(repr(rr),
                        "DTSTART:20090101\n" \
                        "RRULE:FREQ=WEEKLY;WKST=SU;COUNT=9;BYDAY=MO,TU,WE,TH,FR")
        self.assertEqual(rr.count, rr.getCount())
        rr = Recurrence(dtstart=dt.date(2011, 1, 1),
                        freq=DAILY,
                        interval=2,
                        until=dt.date(2011,1,11))
        self.assertEqual(repr(rr),
                        "DTSTART:20110101\n" \
                        "RRULE:FREQ=DAILY;INTERVAL=2;WKST=SU;UNTIL=20110111")
        rr = Recurrence(dtstart=dt.date(2012, 1, 1),
                        freq=YEARLY,
                        bymonth=[1,2],
                        byweekday=range(7),
                        until=dt.date(2012,1,31))
        self.assertEqual(repr(rr),
                        "DTSTART:20120101\n" \
                        "RRULE:FREQ=YEARLY;WKST=SU;UNTIL=20120131;" \
                        "BYDAY=MO,TU,WE,TH,FR,SA,SU;BYMONTH=1,2")
        rr = Recurrence(dtstart=dt.date(2015, 10, 1),
                        freq=MONTHLY,
                        bymonth=range(1,12),
                        byweekday=[(SU(-1))])
        self.assertEqual(repr(rr),
                        "DTSTART:20151001\n" \
                        "RRULE:FREQ=MONTHLY;WKST=SU;BYDAY=-1SU;BYMONTH=1,2,3,4,5,6,7,8,9,10,11")

    def testParse(self):
        rr = Recurrence("DTSTART:20090101\n" \
                        "RRULE:FREQ=WEEKLY;WKST=SU;BYDAY=MO,TU,WE,TH,FR;COUNT=9")
        self.assertEqual(rr.dtstart, dt.date(2009, 1, 1))
        self.assertEqual(rr.count, 9)
        self.assertCountEqual(rr.byweekday, [MO,TU,WE,TH,FR])

    def testParseNoDtstart(self):
        rr = Recurrence("RRULE:FREQ=DAILY;WKST=SU")
        self.assertEqual(rr.freq, DAILY)

    def testRoundtrip(self):
        rrStr = "DTSTART:20151001\n" \
                "RRULE:FREQ=MONTHLY;WKST=SU;BYDAY=-1SU;BYMONTH=1,2,3,4,5,6,7,8,9,10,11"
        self.assertEqual(repr(Recurrence(rrStr)), rrStr)
        rrStr = "DTSTART:20141001\n" \
                "RRULE:FREQ=MONTHLY;WKST=SU;UNTIL=20141001;BYMONTHDAY=1,-1"   # first&last
        self.assertEqual(repr(Recurrence(rrStr)), rrStr)

    def testGetWhen(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=WEEKLY,
                        count=9,
                        byweekday=[MO,WE,FR])
        self.assertEqual(rr._getWhen(1), "Tuesdays, Thursdays and Saturdays")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
