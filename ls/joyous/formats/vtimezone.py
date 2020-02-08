# ------------------------------------------------------------------------------
# vtimezone functions copied from https://github.com/pimutils/khal
# ------------------------------------------------------------------------------
# Copyright (c) 2013-2017 Christian Geier et al.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import datetime as dt
import icalendar
import pytz

def to_naive_utc(dtime):
    """convert a datetime object to UTC and than remove the tzinfo, if
    datetime is naive already, return it
    """
    if not hasattr(dtime, 'tzinfo') or dtime.tzinfo is None:
        return dtime

    dtime_utc = dtime.astimezone(pytz.UTC)
    dtime_naive = dtime_utc.replace(tzinfo=None)
    return dtime_naive

def create_timezone(tz, first_date=None, last_date=None):
    """
    create an icalendar vtimezone from a pytz.tzinfo object

    :param tz: the timezone
    :type tz: pytz.tzinfo
    :param first_date: the very first datetime that needs to be included in the
    transition times, typically the DTSTART value of the (first recurring)
    event
    :type first_date: datetime.datetime
    :param last_date: the last datetime that needs to included, typically the
    end of the (very last) event (of a recursion set)
    :returns: timezone information
    :rtype: icalendar.Timezone()

    we currently have a problem here:

       pytz.timezones only carry the absolute dates of time zone transitions,
       not their RRULEs. This will a) make for rather bloated VTIMEZONE
       components, especially for long recurring events, b) we'll need to
       specify for which time range this VTIMEZONE should be generated and c)
       will not be valid for recurring events that go into eternity.

    Possible Solutions:

    As this information is not provided by pytz at all, there is no
    easy solution, we'd really need to ship another version of the OLSON DB.

    """
    if isinstance(tz, pytz.tzinfo.StaticTzInfo):
        return _create_timezone_static(tz)

    first_date = dt.datetime.today() if not first_date else to_naive_utc(first_date)
    last_date = dt.datetime.today() if not last_date else to_naive_utc(last_date)
    timezone = icalendar.Timezone()
    timezone.add('TZID', tz)

    # This is not a reliable way of determining if a transition is for
    # daylight savings.
    # From 1927 to 1941 New Zealand had GMT+11:30 (NZ Mean Time) as standard
    # and GMT+12:00 (NZ Summer Time) as daylight savings time.
    # From 1941 GMT+12:00 (NZ Standard Time) became standard time.
    # So NZST (NZ Summer/Standard Time) can refer to standard or daylight
    # savings time.  And this code depends on the random order the _tzinfos
    # are returned.
    # dst = {
    #     one[2]: 'DST' in two.__repr__()
    #     for one, two in iter(tz._tzinfos.items())
    # }
    # bst = {
    #     one[2]: 'BST' in two.__repr__()
    #     for one, two in iter(tz._tzinfos.items())
    # }
    # ...
    #   if dst[name] or bst[name]:

    # looking for the first and last transition time we need to include
    first_num, last_num = 0, len(tz._utc_transition_times) - 1
    first_tt = tz._utc_transition_times[0]
    last_tt = tz._utc_transition_times[-1]
    for num, transtime in enumerate(tz._utc_transition_times):
        if transtime > first_tt and transtime < first_date:
            first_num = num
            first_tt = transtime
        if transtime < last_tt and transtime > last_date:
            last_num = num
            last_tt = transtime

    timezones = dict()
    for num in range(first_num, last_num + 1):
        name = tz._transition_info[num][2]
        if name in timezones:
            ttime = tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None)
            if 'RDATE' in timezones[name]:
                timezones[name]['RDATE'].dts.append(
                    icalendar.prop.vDDDTypes(ttime))
            else:
                timezones[name].add('RDATE', ttime)
            continue

        if tz._transition_info[num][1]:
            subcomp = icalendar.TimezoneDaylight()
        else:
            subcomp = icalendar.TimezoneStandard()

        subcomp.add('TZNAME', tz._transition_info[num][2])
        subcomp.add(
            'DTSTART',
            tz.fromutc(tz._utc_transition_times[num]).replace(tzinfo=None))
        subcomp.add('TZOFFSETTO', tz._transition_info[num][0])
        subcomp.add('TZOFFSETFROM', tz._transition_info[num - 1][0])
        timezones[name] = subcomp

    for subcomp in timezones.values():
        timezone.add_component(subcomp)

    return timezone


def _create_timezone_static(tz):
    """create an icalendar vtimezone from a pytz.tzinfo.StaticTzInfo

    :param tz: the timezone
    :type tz: pytz.tzinfo.StaticTzInfo
    :returns: timezone information
    :rtype: icalendar.Timezone()
    """
    timezone = icalendar.Timezone()
    timezone.add('TZID', tz)
    subcomp = icalendar.TimezoneStandard()
    subcomp.add('TZNAME', tz)
    subcomp.add('DTSTART', dt.datetime(1601, 1, 1))
    subcomp.add('RDATE', dt.datetime(1601, 1, 1))
    subcomp.add('TZOFFSETTO', tz._utcoffset)
    subcomp.add('TZOFFSETFROM', tz._utcoffset)
    timezone.add_component(subcomp)
    return timezone
