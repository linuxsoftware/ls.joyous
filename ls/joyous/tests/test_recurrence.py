# ------------------------------------------------------------------------------
import sys
import datetime as dt
from dateutil.rrule import rrule
from django.test import TestCase
from ls.joyous.utils.recurrence import Recurrence, Weekday
from ls.joyous.utils.recurrence import MO, TU, WE, TH, FR, SA, SU
from ls.joyous.utils.recurrence import YEARLY, MONTHLY, WEEKLY, DAILY
from .testutils import datetimetz

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
    def testInitStr(self):
        with self.assertRaises(ValueError):
            Recurrence("DTSTART:19970902T090000\n"
                       "RRULE:FREQ=DAILY;INTERVAL=3\n"
                       "RRULE:FREQ=DAILY;INTERVAL=4")

    def testInitRecurrence(self):
        rr1 = Recurrence(dtstart=dt.date(2009, 1, 1),
                         freq=WEEKLY,
                         byweekday=[MO,TU,WE,TH,FR])
        rr2 = Recurrence(rr1)
        self.assertEqual(rr2.freq, WEEKLY)

    def testInitRrule(self):
        rr1 = rrule(dtstart=dt.date(2009, 1, 1),
                    freq=WEEKLY,
                    byweekday=[MO,TU,WE,TH,FR])
        rr2 = Recurrence(rr1)
        self.assertEqual(rr2.freq, WEEKLY)

    def testEq(self):
        rr1 = rrule(dtstart=dt.datetime(2009, 1, 1, 0, 0, 1),
                    freq=WEEKLY,
                    byweekday=[MO,TU,WE,TH,FR])
        rr2 = Recurrence(dtstart=dt.date(2009, 1, 1),
                         freq=WEEKLY,
                         byweekday=[MO,TU,WE,TH,FR])
        rr3 = Recurrence("DTSTART:20090101\n"
                         "RRULE:FREQ=WEEKLY;WKST=SU;BYDAY=MO,TU,WE,TH,FR")
        rr4 = rrule(dtstart=dt.date(2009, 1, 1),
                    freq=WEEKLY,
                    byweekday=[MO,TU,WE,TH,FR],
                    until=dt.date(2009, 1, 10))
        self.assertEqual(Recurrence(rr1), rr2)
        self.assertEqual(rr2, rr1)
        self.assertEqual(rr1, rr2)
        self.assertEqual(rr2, rr2)
        self.assertEqual(rr2, rr3)
        self.assertNotEqual(rr2, 99)
        self.assertNotEqual(rr2, rr4)

    def testRepr(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=WEEKLY,
                        count=9,
                        byweekday=[MO,TU,WE,TH,FR])
        self.assertEqual(repr(rr),
                        "DTSTART:20090101\n"
                        "RRULE:FREQ=WEEKLY;WKST=SU;COUNT=9;BYDAY=MO,TU,WE,TH,FR")
        self.assertEqual(rr.count, rr.getCount())
        rr = Recurrence(dtstart=dt.date(2011, 1, 1),
                        freq=DAILY,
                        interval=2,
                        until=dt.date(2011,1,11))
        self.assertEqual(repr(rr),
                        "DTSTART:20110101\n"
                        "RRULE:FREQ=DAILY;INTERVAL=2;WKST=SU;UNTIL=20110111")
        rr = Recurrence(dtstart=dt.date(2012, 1, 1),
                        freq=YEARLY,
                        bymonth=[1,2],
                        byweekday=range(7),
                        until=dt.date(2012,1,31))
        self.assertEqual(repr(rr),
                        "DTSTART:20120101\n"
                        "RRULE:FREQ=YEARLY;WKST=SU;UNTIL=20120131;"
                        "BYDAY=MO,TU,WE,TH,FR,SA,SU;BYMONTH=1,2")
        rr = Recurrence(dtstart=dt.date(2015, 10, 1),
                        freq=MONTHLY,
                        bymonth=range(1,12),
                        byweekday=[(SU(-1))])
        self.assertEqual(repr(rr),
                        "DTSTART:20151001\n"
                        "RRULE:FREQ=MONTHLY;WKST=SU;BYDAY=-1SU;BYMONTH=1,2,3,4,5,6,7,8,9,10,11")

    def testParse(self):
        rr = Recurrence("DTSTART:20090101\n"
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

    def testFrequency(self):
        rr = Recurrence(freq=10)
        self.assertEqual(rr.frequency, "unsupported_frequency_10")

    def testGetRrule(self):
        rr = Recurrence(dtstart=dt.date(2011, 1, 1),
                        freq=DAILY,
                        interval=2,
                        until=dt.date(2011,1,11))
        self.assertEqual(rr._getRrule(),
                        "FREQ=DAILY;INTERVAL=2;WKST=SU;UNTIL=20110111")
        with self.assertRaises(TypeError):
            rr._getRrule(untilDt=dt.datetime(2011,1,11))
        self.assertEqual(rr._getRrule(untilDt=dt.datetime(2011,1,11,23,59,59,
                                                          tzinfo=dt.timezone.utc)),
                        "FREQ=DAILY;INTERVAL=2;WKST=SU;UNTIL=20110111T235959Z")

# ------------------------------------------------------------------------------
class TestGetWhen(TestCase):
    def testDaily(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1), freq=DAILY)
        self.assertEqual(rr._getWhen(2), "Daily")

    def testEvery2Days(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        interval=2,
                        freq=DAILY)
        self.assertEqual(rr._getWhen(3), "Every 2 days")

    def testMonEveryFortnight(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        interval=2,
                        freq=WEEKLY,
                        byweekday=MO)
        self.assertEqual(rr._getWhen(0), "Fortnightly on Mondays")

    def testMonEvery6Weeks(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        interval=6,
                        freq=WEEKLY,
                        byweekday=MO)
        self.assertEqual(rr._getWhen(0), "Every 6 weeks on Mondays")

    def testEveryday(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        byweekday=[MO,TU,WE,TH,FR,SA,SU])
        self.assertEqual(rr._getWhen(0), "Everyday")

    def testFirstMonMonthly(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        byweekday=MO(1))
        self.assertEqual(rr._getWhen(0), "The first Monday of the month")

    def testMonEvery2Months(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        interval=2,
                        freq=MONTHLY,
                        byweekday=MO)
        self.assertEqual(rr._getWhen(0), "Every Monday, every 2 months")

    def testLastSatSeptEvery2Years(self):
        rr = Recurrence(dtstart=dt.date(2018, 9, 29),
                        interval=2,
                        freq=YEARLY,
                        byweekday=SA(-1),
                        bymonth=9)
        self.assertEqual(rr._getWhen(0, numDays=5), "The last Saturday of September, every 2 years for 5 days")

    def test1st(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        bymonthday=1)
        self.assertEqual(rr._getWhen(0), "The first day of the month")

    def test22ndOffsetNeg1(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=YEARLY,
                        bymonthday=22,
                        bymonth=5)
        self.assertEqual(rr._getWhen(-1), "The 21st day of May")

    def test30thOffset1(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        bymonthday=30)
        self.assertEqual(rr._getWhen(1), "The day after the 30th day of the month")

    def testMonWedFriOffset1(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=WEEKLY,
                        count=9,
                        byweekday=[MO,WE,FR])
        self.assertEqual(rr._getWhen(1), "Tuesdays, Thursdays and Saturdays")

    def test2ndAnd4thFriOffsetNeg1(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        byweekday=[FR(2),FR(4)])
        self.assertEqual(rr._getWhen(-1), "The Thursday before the second Friday and "
                                          "Thursday before the fourth Friday of the month")

    def test1stOffsetNeg1(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        bymonthday=1,
                        until=dt.date(2010,5,1))
        self.assertEqual(rr._getWhen(-1), "The last day of the month (until 30 April 2010)")

    def test3rdOffset2(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        bymonthday=3)
        self.assertEqual(rr._getWhen(2), "The fifth day of the month")

    def test1stJanAprMayOffsetNeg1(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=YEARLY,
                        bymonthday=1,
                        bymonth=[1,4,5])
        self.assertEqual(rr._getWhen(-1), "The last day of December, March and April")

    def testLastJulAugSepDecOffset1(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=YEARLY,
                        bymonthday=-1,
                        bymonth=[7,8,9,12])
        self.assertEqual(rr._getWhen(1),
                         "The first day of August, September, October and January")

    def test1stAndLast(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        bymonthday=[1,-1])
        self.assertEqual(rr._getWhen(0), "The first and the last day of the month")

    def test1stAndLastOffsetNeg1(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=MONTHLY,
                        bymonthday=[1,-1])
        self.assertEqual(rr._getWhen(-1), "The day before the first and the last day of the month")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
