# ------------------------------------------------------------------------------
# Test Recurrence
# ------------------------------------------------------------------------------
import sys
from datetime import datetime
from dateutil.rrule import YEARLY, MONTHLY, WEEKLY, DAILY
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU

from django.test import TestCase
from ls.joyous.recurrence import Recurrence

class TestRecurrence(TestCase):
    def testRepr(self):
        rr = Recurrence(dtstart=datetime(2009, 1, 1),
                        freq=WEEKLY,
                        count=9,
                        byweekday=[MO,TU,WE,TH,FR])
        self.assertEqual(repr(rr),
                        "DTSTART:20090101\n" \
                        "RRULE:FREQ=WEEKLY;WKST=SU;COUNT=9;BYDAY=MO,TU,WE,TH,FR")
        self.assertEqual(rr.count, rr.getCount())
        rr = Recurrence(dtstart=datetime(2011, 1, 1),
                        freq=DAILY,
                        interval=2,
                        until=datetime(2011,1,11))
        self.assertEqual(repr(rr),
                        "DTSTART:20110101\n" \
                        "RRULE:FREQ=DAILY;INTERVAL=2;WKST=SU;UNTIL=20110111")
        rr = Recurrence(dtstart=datetime(2012, 1, 1),
                        freq=YEARLY,
                        bymonth=[1,2],
                        byweekday=range(7),
                        until=datetime(2012,1,31))
        self.assertEqual(repr(rr),
                        "DTSTART:20120101\n" \
                        "RRULE:FREQ=YEARLY;WKST=SU;UNTIL=20120131;" \
                        "BYDAY=MO,TU,WE,TH,FR,SA,SU;BYMONTH=1,2")
        rr = Recurrence(dtstart=datetime(2015, 10, 1),
                        freq=MONTHLY,
                        bymonth=range(1,12),
                        byweekday=[(SU(-1))])
        self.assertEqual(repr(rr),
                        "DTSTART:20151001\n" \
                        "RRULE:FREQ=MONTHLY;WKST=SU;BYDAY=-1SU;BYMONTH=1,2,3,4,5,6,7,8,9,10,11")

    def testParse(self):
        rr = Recurrence("DTSTART:20090101\n" \
                        "RRULE:FREQ=WEEKLY;WKST=SU;BYDAY=MO,TU,WE,TH,FR;COUNT=9")
        self.assertEqual(rr.dtstart, datetime(2009, 1, 1))
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

