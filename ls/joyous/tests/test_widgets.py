# ------------------------------------------------------------------------------
# Test Widgets
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import TestCase
from wagtail.admin.widgets import AdminTimeInput, AdminDateInput
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import YEARLY, WEEKLY, MONTHLY
from ls.joyous.utils.recurrence import MO, TU, WE, TH, FR, SA, SU
from ls.joyous.widgets import RecurrenceWidget, Time12hrInput, ExceptionDateInput
from .testutils import datetimetz, freeze_timetz, getPage

# ------------------------------------------------------------------------------
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

    def testDecompressDayOfMonth(self):
        rr = Recurrence(dtstart=dt.date(2019, 1, 1),
                        freq=MONTHLY,
                        bymonthday=1)
        widget = RecurrenceWidget()
        self.assertEqual(widget.decompress(rr),
                         [dt.date(2019, 1, 1), MONTHLY, 1,
                          [], None, None,                     #5
                          101, 200, None, None, None,         #10
                          None, []])

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
                'repeat_12': []}
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
        self.assertEqual(widget.value_from_datadict(data, {}, 'repeat'), rr)

    def testSameDayOfMonthValue(self):
        widget = RecurrenceWidget()
        data = {'repeat_0':  '2019-01-01',
                'repeat_1':  '1',
                'repeat_2':  '1',
                'repeat_5':  '',
                'repeat_6':  '101',
                'repeat_7':  '200'}
        rr = Recurrence(dtstart=dt.date(2019, 1, 1), freq=MONTHLY)
        self.assertEqual(widget.value_from_datadict(data, {}, 'repeat'), rr)

    def testDayOfMonthValue(self):
        widget = RecurrenceWidget()
        data = {'repeat_0':  '2019-01-01',
                'repeat_1':  '1',
                'repeat_2':  '1',
                'repeat_5':  '',
                'repeat_6':  '2',
                'repeat_7':  '200'}
        rr = Recurrence(dtstart=dt.date(2019, 1, 1), freq=MONTHLY, bymonthday=[2])
        self.assertEqual(widget.value_from_datadict(data, {}, 'repeat'), rr)

    def testMonthOfTuesdaysValue(self):
        widget = RecurrenceWidget()
        data = {'repeat_0':  '2010-01-05',
                'repeat_1':  '1',
                'repeat_2':  '1',
                'repeat_5':  '2010-01-26',
                'repeat_6':  '100',
                'repeat_7':  '1',
                'repeat_8':  None,
                'repeat_9':  None,
                'repeat_10': None,
                'repeat_11': None }
        rr = Recurrence(dtstart=dt.date(2010, 1, 5),
                        freq=MONTHLY,
                        byweekday=[TU],
                        until=dt.date(2010,1,26))
        self.assertEqual(widget.value_from_datadict(data, {}, 'repeat'), rr)

    def testSameTuesdayValue(self):
        widget = RecurrenceWidget()
        data = {'repeat_0':  '2010-01-12',
                'repeat_1':  '1',
                'repeat_2':  '1',
                'repeat_6':  '101',
                'repeat_7':  '1',
                'repeat_8':  None,
                'repeat_9':  None,
                'repeat_10': None,
                'repeat_11': None }
        rr = Recurrence(dtstart=dt.date(2010, 1, 12),
                        freq=MONTHLY,
                        byweekday=[TU(2)])
        self.assertEqual(widget.value_from_datadict(data, {}, 'repeat'), rr)

    def test135WednesdaysValue(self):
        widget = RecurrenceWidget()
        data = {'repeat_0':  '2010-01-12',
                'repeat_1':  '1',
                'repeat_2':  '1',
                'repeat_6':  '1',
                'repeat_7':  '2',
                'repeat_8':  '3',
                'repeat_9':  '2',
                'repeat_10': '5',
                'repeat_11': '2' }
        rr = Recurrence(dtstart=dt.date(2010, 1, 12),
                        freq=MONTHLY,
                        byweekday=[WE(1),WE(3),WE(5)])
        self.assertEqual(widget.value_from_datadict(data, {}, 'repeat'), rr)

    def testGetContext(self):
        rr = Recurrence(dtstart=dt.date(2014, 12, 1),
                        freq=MONTHLY,
                        byweekday=[MO(1),MO(3),MO(5)])
        attrs = {'id': "id_repeat"}
        widget = RecurrenceWidget(attrs)
        context = widget.get_context("repeat", rr, None)
        self.assertEqual(list(context.keys()), ["widget"])
        ctx = context['widget']
        self.assertEqual(ctx['attrs'], attrs)
        self.assertEqual(ctx['name'], "repeat")
        self.assertIsInstance(ctx['subwidgets'], list)
        self.assertEqual(len(ctx['subwidgets']), 13)
        self.assertEqual(ctx['template_name'],
                         "joyous/widgets/recurrence_widget.html")
        when = "The first Monday, third Monday and fifth Monday of the month"
        self.assertEqual(ctx['value'], when)
        self.assertEqual(ctx['value_s'], when)
        self.assertEqual(ctx['value_r'], "DTSTART:20141201\n"
                         "RRULE:FREQ=MONTHLY;WKST=SU;BYDAY=+1MO,+3MO,+5MO")

    def testMedia(self):
        widget = RecurrenceWidget()
        self.assertIn("/static/joyous/css/recurrence_admin.css" ,widget.media._css['all'])
        self.assertIn("/static/joyous/js/recurrence_admin.js", widget.media._js)

# ------------------------------------------------------------------------------
class TestTime12hrInput(TestCase):
    def setUp(self):
        self.newTime = AdminTimeInput().attrs.get('autocomplete', "new-time")

    def testNullValue(self):
        widget = Time12hrInput()
        self.assertEqual(widget.value_from_datadict({}, {}, 'time'), None)

    def testRenderNone(self):
        widget = Time12hrInput()
        out = widget.render('time', None, {'id': "time_id"})
        self.assertHTMLEqual(out, """
<input type="text" name="time" id="time_id" autocomplete="{0.newTime}">
<script>
$(function() {{
    initTime12hrChooser("time_id");
}});
</script>""".format(self))

    def testRenderValues(self):
        attrs = {'id': "time_id"}
        widget = Time12hrInput()
        out = widget.render('time', dt.time(10,15,54,89123), attrs)
        self.assertHTMLEqual(out, """
<input type="text" name="time" id="time_id" autocomplete="{0.newTime}" value="10:15am">
<script>
$(function() {{
    initTime12hrChooser("time_id");
}});
</script>""".format(self))
        out = widget.render('time', dt.time(12,51,34,89123), attrs)
        self.assertHTMLEqual(out, """
<input type="text" name="time" id="time_id" autocomplete="{0.newTime}" value="12:51pm">
<script>
$(function() {{
    initTime12hrChooser("time_id");
}});
</script>""".format(self))

    def testRenderFromString(self):
        attrs = {'id': "time_id"}
        widget = Time12hrInput()
        out = widget.render('time', "1pm", attrs)
        self.assertHTMLEqual(out, """
<input type="text" name="time" id="time_id" autocomplete="{0.newTime}" value="1pm">
<script>
$(function() {{
    initTime12hrChooser("time_id");
}});
</script>""".format(self))

    def testMedia(self):
        widget = Time12hrInput()
        self.assertEqual(widget.media._css, {})
        self.assertEqual(widget.media._js, 
                         ["/static/joyous/js/vendor/moment-2.22.0.min.js",
                          "/static/joyous/js/time12hr_admin.js"])

# ------------------------------------------------------------------------------
class TestExceptionDateInput(TestCase):
    def setUp(self):
        self.newDate = AdminDateInput().attrs.get('autocomplete', "new-date")

    def testNullValue(self):
        widget = ExceptionDateInput()
        self.assertEqual(widget.value_from_datadict({}, {}, 'xdate'), None)

    def testRenderNone(self):
        widget = ExceptionDateInput()
        out = widget.render('xdate', None, {'id': "id_xdate"})
        lines = [line for line in out.split("\n") if line]
        self.assertHTMLEqual(lines[0], """
<input type="text" name="xdate" id="id_xdate" autocomplete="{0.newDate}">""".format(self))
        self.assertIn('<script>initExceptionDateChooser("id_xdate", null, ', lines[1]);
        self.assertIn('"dayOfWeekStart": 0', lines[1])
        self.assertIn('"format": "Y-m-d"', lines[1])
        self.assertIn('</script>', lines[1])

    @freeze_timetz("2019-04-06 9:00")
    def testValidDates(self):
        widget = ExceptionDateInput()
        widget.overrides_repeat = Recurrence(dtstart=dt.date(2009, 1, 1),
                                             freq=MONTHLY, byweekday=MO(1))
        self.assertEqual(widget.valid_dates(),
                         ["20180903", "20181001", "20181105", "20181203", "20190107", "20190204",
                          "20190304", "20190401", "20190506", "20190603", "20190701", "20190805",
                          "20190902", "20191007", "20191104", "20191202", "20200106", "20200203",
                          "20200302", "20200406", "20200504", "20200601", "20200706", "20200803",
                          "20200907", "20201005" ])

    def testMedia(self):
        widget = ExceptionDateInput()
        self.assertEqual(widget.media._css, {'all': ["/static/joyous/css/recurrence_admin.css"]})
        self.assertEqual(widget.media._js, ["/static/joyous/js/recurrence_admin.js"])

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
