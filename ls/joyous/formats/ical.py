# ------------------------------------------------------------------------------
# ical import/export format
# ------------------------------------------------------------------------------
import datetime as dt
import pytz
from socket import gethostname
from icalendar import Calendar, Event
from icalendar import vDatetime
#from html2text import HTML2Text
from django.http import HttpResponse
from django.utils import timezone
from ls.joyous import __version__
from ..models import (SimpleEventPage, MultidayEventPage, RecurringEventPage,
        EventExceptionBase, ExtraInfoPage, CancellationPage, CalendarPage)
from ..utils.telltime import getAwareDatetime
from .vtimezone import create_timezone

# ------------------------------------------------------------------------------
class ICalendarHander:
    def serve(self, page, request, *args, **kwargs):
        vcal = self.makeVCalendar(page)
        if vcal is not None:
            response = HttpResponse(vcal.export(),
                                    content_type='text/calendar')
            response['Content-Disposition'] = \
                'attachment; filename={}.ics'.format(page.slug)
            return response
        return None

    def makeVCalendar(self, page):
        # TODO move the making into VCalendar.__init__
        if not isinstance(page, CalendarPage):
            return self.make1EventVCalendar(page)
        #vcal = VCalendar()
        #for event in vcal._getAllEvents()
        #timezones
        # return vcal
        return None

    def make1EventVCalendar(self, page):
        vcal = None
        vevent = self.makeVEvent(page)
        if vevent is not None:
            vcal = VCalendar()
            if page.tz and page.tz is not pytz.utc:
                vtz = create_timezone(page.tz, vevent.dtstart, vevent.dtend)
                vcal.add_component(vtz)
            vcal.add_component(vevent)
            for vchild in vevent.vchildren:
                vcal.add_component(vchild)
        return vcal

    def makeVEvent(self, page):
        if isinstance(page, SimpleEventPage):
            return SimpleVEvent(page)
        elif isinstance(page, MultidayEventPage):
            return MultidayVEvent(page)
        elif isinstance(page, RecurringEventPage):
            return RecurringVEvent(page)
        elif isinstance(page, EventExceptionBase):
            return RecurringVEvent(page.overrides)
        else:
            return None

# ------------------------------------------------------------------------------
class VCalendar(Calendar):
    prodVersion = ".".join(__version__.split(".", 2)[:2])
    prodId = "-//linuxsoftware.nz//NONSGML Joyous v{}//EN".format(prodVersion)

    def __init__(self):
        super().__init__()
        self.add('prodid',  self.prodId)
        self.add('version', "2.0")

    def export(self):
        return self.to_ical()

# ------------------------------------------------------------------------------
class VEvent(Event):
    def __init__(self, page):
        super().__init__()
        #h2t = HTML2Text()
        self.page = page
        self.vchildren = []
        firstRevision = page.revisions.order_by("created_at").first()
        self.add('UID',           self.uid)
        self.add('URL',           page.full_url)
        self.add('SUMMARY',       self.summary)
        self.add('DESCRIPTION',   self.description)
        self.add('SEQUENCE',      page.revisions.count())
        self.add('DTSTAMP',       vDatetime(timezone.now()))
        self.add('CREATED',       vDatetime(firstRevision.created_at))
        self.add('LAST-MODIFIED', vDatetime(page.latest_revision_created_at))
        self.add('LOCATION',      self.location)
        self.add('DTSTART',       vDatetime(self.dtstart))
        self.add('DTEND',         vDatetime(self.dtend))

    @property
    def uid(self):
        pg = self.page
        site = pg.get_site()
        if site and site.hostname and site.hostname != "localhost":
            hostname = site.hostname
        else:
            hostname = gethostname()
        return "{}-{}@{}".format(pg.id, pg.slug, hostname)

    @property
    def summary(self):
        return self.page.title

    @property
    def description(self):
        #return h2t.handle(self.page.details)
        return self.page.details

    @property
    def location(self):
        return self.page.location


class SimpleVEvent(VEvent):
    @property
    def dtstart(self):
        pg = self.page
        return getAwareDatetime(pg.date, pg.time_from, pg.tz, dt.time.min)

    @property
    def dtend(self):
        pg = self.page
        return getAwareDatetime(pg.date, pg.time_to, pg.tz, dt.time.max)


class MultidayVEvent(VEvent):
    @property
    def dtstart(self):
        pg = self.page
        return getAwareDatetime(pg.date_from, pg.time_from, pg.tz, dt.time.min)

    @property
    def dtend(self):
        pg = self.page
        return getAwareDatetime(pg.date_to, pg.time_to, pg.tz, dt.time.max)


class RecurringVEvent(VEvent):
    def __init__(self, page):
        super().__init__(page)
        self.exDates = []
        self._handleExceptions()
        if self.exDates:
            self.add('EXDATE', self.exDates)
        self.add('RRULE', self._getRrule())

    @property
    def dtstart(self):
        startDt = self.page._getMyFirstDatetimeFrom()
        if startDt is not None:
            return startDt
        else:
            return pytz.utc.localize(dt.datetime.min)

    @property
    def dtend(self):
        endDt = self.page._getMyFirstDatetimeTo()
        if endDt is not None:
            return endDt
        else:
            return pytz.utc.localize(dt.datetime.min)

    def _handleExceptions(self):
        pg = self.page
        for cancellation in CancellationPage.objects.live().child_of(pg) \
                                            .select_related("postponementpage"):
            postponement = getattr(cancellation, "postponementpage", None)
            if not postponement and cancellation.cancellation_title == "":
                excludeDt = getAwareDatetime(cancellation.except_date,
                                             cancellation.time_from,
                                             cancellation.tz, dt.time.min)
                self.exDates.append(excludeDt)
            else:
                if cancellation.title != "":
                    self.vchildren.append(CancelledVEvent(cancellation, self))
                if postponement:
                    self.vchildren.append(PostponedVEvent(postponement, self))

        for info in ExtraInfoPage.objects.live().child_of(pg):
            self.vchildren.append(ExtraInfoVEvent(info, self))

    def _getRrule(self):
        repeat = self.page.repeat
        props = [('FREQ', repeat.frequency)]
        if repeat.interval and repeat.interval != 1:
            props.append(('INTERVAL', repeat.interval))
        if repeat.wkst:
            props.append(('WKST', repr(repeat.wkst)))
        if repeat.count:
            props.append(('COUNT', repeat.count))
        if repeat.until:
            props.append(('UNTIL', repeat.until))
        for name, value in [('BYSETPOS',   repeat.bysetpos),
                            ('BYDAY',      repeat.byweekday),
                            ('BYMONTH',    repeat.bymonth),
                            ('BYMONTHDAY', repeat.bymonthday),
                            ('BYYEARDAY',  repeat.byyearday),
                            ('BYWEEKNO',   repeat.byweekno)]:
            if value:
                props.append((name, [repr(v) for v in value]))
        return dict(props)


class ExceptionVEvent(VEvent):
    def __init__(self, page, vparent):
        self.vparent = vparent
        super().__init__(page)
        self.add('RECURRENCE-ID', vDatetime(self._getStartDt()))

    def _getStartDt(self):
        pg = self.page
        return getAwareDatetime(pg.except_date, pg.time_from, pg.tz, dt.time.min)

    def _getEndDt(self):
        pg = self.page
        return getAwareDatetime(pg.except_date, pg.time_to, pg.tz, dt.time.max)

    @property
    def uid(self):
        return self.vparent.uid

    @property
    def location(self):
        return self.vparent.page.location

    dtstart = property(_getStartDt)
    dtend   = property(_getEndDt)


class ExtraInfoVEvent(ExceptionVEvent):
    @property
    def summary(self):
        return self.page.extra_title or self.vparent.page.title

    @property
    def description(self):
        return self.page.extra_information + "\n" + self.vparent.page.details


class CancelledVEvent(ExceptionVEvent):
    @property
    def summary(self):
        return self.page.cancellation_title

    @property
    def description(self):
        return self.page.cancellation_details


class PostponedVEvent(ExceptionVEvent):
    @property
    def summary(self):
        return self.page.postponement_title

    @property
    def location(self):
        return self.page.location

    @property
    def dtstart(self):
        pg = self.page
        return getAwareDatetime(pg.date, pg.time_from, pg.tz, dt.time.min)

    @property
    def dtend(self):
        pg = self.page
        return getAwareDatetime(pg.date, pg.time_to, pg.tz, dt.time.max)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
