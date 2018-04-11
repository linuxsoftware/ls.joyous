# ------------------------------------------------------------------------------
# Test Widgets
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from dateutil.rrule import YEARLY, MONTHLY, WEEKLY, DAILY
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU

from django.test import TestCase
from ls.joyous.recurrence import Recurrence, RecurrenceWidget

class TestRecurrenceWidget(TestCase):
    def testDecompressNull(self):
        widget = RecurrenceWidget()
        self.assertEqual(widget.decompress(None),
                         [None, None, 1, [], None, None,      #5
                          101, 200, None, None, None,         #10
                          None, []])

    def testDecompressWeekdays(self):
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=WEEKLY,
                        count=9,
                        byweekday=[MO,TU,WE,TH,FR])
        widget = RecurrenceWidget()
        self.assertEqual(widget.decompress(rr),
                         [dt.date(2009, 1, 1), WEEKLY, 1,
                          [0,1,2,3,4], 9, None,               #5
                          101, 200, None, None, None,         #10
                          None, []])

    def testDecompressEverydayInJanuary(self):
        rr = Recurrence(dtstart=dt.date(2014, 12, 1),
                        freq=YEARLY,
                        byweekday=[MO,TU,WE,TH,FR,SA,SU],
                        bymonth=[1])
        widget = RecurrenceWidget()
        self.assertEqual(widget.decompress(rr),
                         [dt.date(2014, 12, 1), YEARLY, 1,
                          [], None, None,                     #5
                          100, 200, None, None, None,         #10
                          None, [1]])

    def testNullValue(self):
        widget = RecurrenceWidget()
        self.assertEqual(widget.value_from_datadict({}, {}, 'repeat'), None)

    def testWeekdaysValue(self):
        widget = RecurrenceWidget()
        data = {'repeat_0':  '2009-01-01',
                'repeat_1':  '2',
                'repeat_2':  '1',
                'repeat_3':  ['0','1','2','3','4'],
                'repeat_5':  '2012-01-31',
                'repeat_6':  '101',
                'repeat_7':  '200',
                'repeat_8':  None,
                'repeat_9':  None,
                'repeat_10': None,
                'repeat_11': None,
                'repeat_12': ['1']}
        rr = Recurrence(dtstart=dt.date(2009, 1, 1),
                        freq=WEEKLY,
                        byweekday=[MO,TU,WE,TH,FR],
                        until=dt.date(2012,1,31))
        self.assertEqual(str(widget.value_from_datadict(data, {}, 'repeat')),
                         str(rr))

    def testEverydayInJanuaryValue(self):
        widget = RecurrenceWidget()
        data = {'repeat_0':  '2014-12-1',
                'repeat_1':  '0',
                'repeat_2':  '1',
                'repeat_5':  '',
                'repeat_6':  '100',
                'repeat_7':  '200',
                'repeat_8':  None,
                'repeat_9':  None,
                'repeat_10': None,
                'repeat_11': None,
                'repeat_12': ['1']}
        rr = Recurrence(dtstart=dt.date(2014, 12, 1),
                        freq=YEARLY,
                        byweekday=[MO,TU,WE,TH,FR,SA,SU],
                        bymonth=[1])
        self.assertEqual(str(widget.value_from_datadict(data, {}, 'repeat')),
                         str(rr))
