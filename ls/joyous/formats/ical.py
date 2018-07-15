# ------------------------------------------------------------------------------
# ical import/export format
# ------------------------------------------------------------------------------
import datetime as dt
import pytz
from socket import gethostname
from contextlib import suppress
from icalendar import Calendar, Event
from icalendar import vDatetime
from django.http import HttpResponse
from django.utils import timezone
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from ls.joyous import __version__
from ..models import (SimpleEventPage, MultidayEventPage, RecurringEventPage,
        EventExceptionBase, ExtraInfoPage, CancellationPage, EventBase,
        CalendarPage)
from ..utils.telltime import getAwareDatetime
from .vtimezone import create_timezone

# ------------------------------------------------------------------------------
class ICalendarHandler:
    def serve(self, page, request, *args, **kwargs):
        try:
            vcal = VCalendar(page)
            response = HttpResponse(vcal.render(), content_type='text/calendar')
            response['Content-Disposition'] = \
                'attachment; filename={}.ics'.format(page.slug)
            return response

        except TypeError:
            return None

    def load(self, page, stream):
        vcal = VCalendar(page)
        vcal.load(stream)


# ------------------------------------------------------------------------------
def _getEventByUid(uid):
    events = []
    with suppress(ObjectDoesNotExist):
        events.append(SimpleEventPage.objects.get(uid=uid))
    with suppress(ObjectDoesNotExist):
        events.append(MultidayEventPage.objects.get(uid=uid))
    with suppress(ObjectDoesNotExist):
        events.append(RecurringEventPage.objects.get(uid=uid))

    if len(events) == 1:
        return events[0]
    elif len(events) == 0:
        return None
    else:
        raise MultipleObjectsReturned("Multiple events with uid={}".format(uid))

# ------------------------------------------------------------------------------
class VEventFactory:
    def makeVEvent(self, data):
        if isinstance(data, EventBase):
            return self._makeVEventFromPage(data)
        elif isinstance(data, Event):
            return self._makeVEventFromProps(data)
        else:
            raise TypeError("Unsupported input data")

    def _makeVEventFromPage(self, page):
        if isinstance(page, SimpleEventPage):
            return SimpleVEvent(page)
        elif isinstance(page, MultidayEventPage):
            return MultidayVEvent(page)
        elif isinstance(page, RecurringEventPage):
            return RecurringVEvent(page)
        elif isinstance(page, EventExceptionBase):
            return RecurringVEvent(page.overrides)
        else:
            raise TypeError("Unsupported page type")

    def _makeVEventFromProps(self, props):
        if 'RRULE' in props:
            return RecurringVEvent(props)
        dtend   = props.get('DTEND')
        dtstart = props.get('DTSTART')
        if dtend is None or dtstart is None:
            raise TypeError("Unsupported properties")
        if (dtend.dt - dt.start.dt) >= dt.timedelta(days=1):
            return MultidayVEvent(props)
        else:
            return SimpleVEvent(props)

class VCalendar:
    prodVersion = ".".join(__version__.split(".", 2)[:2])
    prodId = "-//linuxsoftware.nz//NONSGML Joyous v{}//EN".format(prodVersion)
    factory = VEventFactory()

    def __init__(self, other=None):
        self.page  = None
        self.props = None

        self.add('prodid',  self.prodId)
        self.add('version', "2.0")
        if isinstance(other, Calendar):
            self._initFromProps(other)
        elif isinstance(other, CalendarPage):
            self._initFromCalendarPage(other)
        elif isinstance(other, EventBase):
            self._initFromEventPage(other)

    def _initFromProps(self, props):
        #for event in page._getAllEvents()
        #timezones
        # return vcal
        return None

    def _initFromCalendarPage(self, other):
        pass

    def _initFromEventPage(self, page):
        vevent = self.factory.makeVEvent(page)
        if page.tz and page.tz is not pytz.utc:
            vtz = create_timezone(page.tz, vevent.dtstart, vevent.dtend)
            self.add_component(vtz)
        self.add_component(vevent)
        for exception in vevent.vchildren:
            self.add_component(exception)

    def asProps(self):
        return self.props

    def asPage(self):
        return self.page

    def render(self):
        return self.to_ical()

    def load(self, stream):
        cal = Calendar.from_ical(stream.read())
        for event in cal.walk(name="VEVENT"):
            page = _getEventByUid(event.get('UID'))
        #     if not wehavethis(event):
        #         vevent = self.factory.makeVEvent(event)
        #         check if such a page exists
        #         if not create it


# ------------------------------------------------------------------------------
class VEvent:
    def __init__(self):
        self.page      = None
        self.component = None

    def setPage(self, page):
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
        self._handleExceptions()
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
        self.exDates = []
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
        if self.exDates:
            self.add('EXDATE', self.exDates)

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
