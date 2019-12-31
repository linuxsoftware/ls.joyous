# ------------------------------------------------------------------------------
# vtimezone functions copied from https://github.com/pimutils/khal
# ------------------------------------------------------------------------------
import datetime as dt
import pytz
from ls.joyous.formats.vtimezone import create_timezone
from django.test import TestCase


# ------------------------------------------------------------------------------
class TestVDt(TestCase):
    def setUp(self):
        self.berlin = pytz.timezone('Europe/Berlin')
        self.bogota = pytz.timezone('America/Bogota')

    def testBerlin(self):
        vberlin_std = b'\r\n'.join(
            [b'BEGIN:STANDARD',
             b'DTSTART;VALUE=DATE-TIME:20141026T020000',
             b'TZNAME:CET',
             b'TZOFFSETFROM:+0200',
             b'TZOFFSETTO:+0100',
             b'END:STANDARD',
             ])
        vberlin_dst = b'\r\n'.join(
            [b'BEGIN:DAYLIGHT',
             b'DTSTART;VALUE=DATE-TIME:20150329T030000',
             b'TZNAME:CEST',
             b'TZOFFSETFROM:+0100',
             b'TZOFFSETTO:+0200',
             b'END:DAYLIGHT',
             ])
        atime = dt.datetime(2014, 10, 28, 10, 10)
        vberlin = create_timezone(self.berlin, atime, atime).to_ical()
        self.assertIn(b'TZID:Europe/Berlin', vberlin)
        self.assertIn(vberlin_std, vberlin)
        self.assertIn(vberlin_dst, vberlin)

    def testBerlinRdate(self):
        vberlin_std = b'\r\n'.join(
            [b'BEGIN:STANDARD',
             b'DTSTART;VALUE=DATE-TIME:20141026T020000',
             b'RDATE:20151025T020000,20161030T020000',
             b'TZNAME:CET',
             b'TZOFFSETFROM:+0200',
             b'TZOFFSETTO:+0100',
             b'END:STANDARD',
             ])
        vberlin_dst = b'\r\n'.join(
            [b'BEGIN:DAYLIGHT',
             b'DTSTART;VALUE=DATE-TIME:20150329T030000',
             b'RDATE:20160327T030000',
             b'TZNAME:CEST',
             b'TZOFFSETFROM:+0100',
             b'TZOFFSETTO:+0200',
             b'END:DAYLIGHT',
             ])
        atime = dt.datetime(2014, 10, 28, 10, 10)
        btime = dt.datetime(2016, 10, 28, 10, 10)
        vberlin = create_timezone(self.berlin, atime, btime).to_ical()
        assert b'TZID:Europe/Berlin' in vberlin
        assert vberlin_std in vberlin
        assert vberlin_dst in vberlin

    def testBogota(self):
        vbogota = [b'BEGIN:VTIMEZONE',
                   b'TZID:America/Bogota',
                   b'BEGIN:STANDARD',
                   b'DTSTART;VALUE=DATE-TIME:19930403T230000',
                   b'TZNAME:COT',
                   b'TZOFFSETFROM:-0400',
                   b'TZOFFSETTO:-0500',
                   b'END:STANDARD',
                   b'END:VTIMEZONE',
                   b'']
        pytz_version = tuple(int(x) for x in pytz.__version__.split("."))
        if pytz_version > (2017, 1):
            vbogota[4] = b'TZNAME:-05'
            vbogota.insert(4, b'RDATE:20380118T221407')
        atime = dt.datetime(2014, 10, 28, 10, 10)
        assert create_timezone(self.bogota, atime, atime).to_ical().split(b'\r\n') == vbogota

    def testPST(self):
        vpacific = [b'BEGIN:VTIMEZONE',
                    b'TZID:Etc/GMT-8',
                    b'BEGIN:STANDARD',
                    b'DTSTART;VALUE=DATE-TIME:16010101T000000',
                    b'RDATE:16010101T000000',
                    b'TZNAME:Etc/GMT-8',
                    b'TZOFFSETFROM:+0800',
                    b'TZOFFSETTO:+0800',
                    b'END:STANDARD',
                    b'END:VTIMEZONE',
                    b'']
        pst = pytz.timezone('Etc/GMT-8')
        atime = dt.datetime(2014, 10, 28, 10, 10)
        btime = dt.datetime(2016, 10, 28, 10, 10)
        vtz = create_timezone(pst, atime, btime)
        assert vtz.to_ical().split(b'\r\n') == vpacific

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
