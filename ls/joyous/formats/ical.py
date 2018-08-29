# ------------------------------------------------------------------------------
# ical import/export format
# ------------------------------------------------------------------------------
import datetime as dt
from collections import namedtuple
from itertools import chain
import pytz
import base64
import quopri
from icalendar import Calendar, Event
from icalendar import vDatetime, vRecur, vDDDTypes, vText
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.utils import timezone
from ls.joyous import __version__
from ..models import (SimpleEventPage, MultidayEventPage, RecurringEventPage,
        EventExceptionBase, ExtraInfoPage, CancellationPage, PostponementPage,
        EventBase, CalendarPage)
from ..utils.recurrence import Recurrence
from ..utils.telltime import getAwareDatetime
from .vtimezone import create_timezone

# ------------------------------------------------------------------------------
class VComponentMixin:
    """Utilities for working with icalendar components"""
    def set(self, name, value, parameters=None, encode=1):
        if name in self:
            del self[name]
        self.add(name, value, parameters, encode)

class CalendarTypeError(TypeError):
    pass

class CalendarNotInitializedError(RuntimeError):
    pass

# ------------------------------------------------------------------------------
class ICalHandler:
    def serve(self, page, request, *args, **kwargs):
        try:
            vcal = VCalendar.fromPage(page, request)
        except CalendarTypeError:
            return None
        response = HttpResponse(vcal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = \
            'attachment; filename={}.ics'.format(page.slug)
        return response

    def load(self, page, request, upload):
        vcal = VCalendar(page)
        vcal.load(request, upload.read(), getattr(upload, 'name', ""))

# ------------------------------------------------------------------------------
class VCalendar(Calendar, VComponentMixin):
    prodVersion = ".".join(__version__.split(".", 2)[:2])
    prodId = "-//linuxsoftware.nz//NONSGML Joyous v{}//EN".format(prodVersion)

    def __init__(self, page=None):
        super().__init__(self)
        self.page = page
        self.set('PRODID',  self.prodId)
        self.set('VERSION', "2.0")

    @classmethod
    def fromPage(cls, page, request):
        if isinstance(page, CalendarPage):
            return cls._fromCalendarPage(page, request)
        elif isinstance(page, EventBase):
            return cls._fromEventPage(page)
        else:
            raise CalendarTypeError("Unsupported input page")

    @classmethod
    def _fromCalendarPage(cls, page, request):
        vcal = cls(page)
        tzs = {}
        for event in page._getAllEvents(request):
            vevent = cls.factory.makeFromPage(event)
            vcal.add_component(vevent)
            for vchild in vevent.vchildren:
                vcal.add_component(vchild)
            if event.tz and event.tz is not pytz.utc:
                tzs.setdefault(event.tz, TimeZoneSpan()).add(vevent)
        for tz, vspan in tzs.items():
            vtz = vspan.createVTimeZone(tz)
            vcal.add_component(vtz)
        return vcal

    @classmethod
    def _fromEventPage(cls, event):
        vcal = cls(cls._findCalendarFor(event))
        vevent = cls.factory.makeFromPage(event)
        vcal.add_component(vevent)
        for vchild in vevent.vchildren:
            vcal.add_component(vchild)
        if event.tz and event.tz is not pytz.utc:
            vtz = TimeZoneSpan(vevent).createVTimeZone(event.tz)
            vcal.add_component(vtz)
        return vcal

    @classmethod
    def _findCalendarFor(cls, event):
        calendar = CalendarPage.objects.ancestor_of(event).first()
        if not calendar:
            site = event.get_site()
            if site:
                home = site.root_page
                calendar = CalendarPage.objects.descendant_of(home).first()
        if not calendar:
            calendar = CalendarPage.objects.first()
        return calendar

    def clear(self):
        super().clear()
        self.subcomponents.clear()

    def load(self, request, data, name=""):
        if self.page is None:
            raise CalendarNotInitializedError("No page set")

        # Typically, this information will consist of an iCalendar stream
        # with a single iCalendar object.  However, multiple iCalendar
        # objects can be sequentially grouped together in an iCalendar
        # stream.
        try:
            calStream = Calendar.from_ical(data, multiple=True)
        except ValueError as e:
            messages.error(request, "Could not parse iCalendar file "+name)
            #messages.debug(request, str(e))
            return

        self.clear()
        numSuccess = numFail = 0
        for cal in calStream:
            vmap = {}
            for props in cal.walk(name="VEVENT"):
                try:
                    vevent = self.factory.makeFromProps(props)
                except CalendarTypeError as e:
                    numFail += 1
                    #messages.debug(request, str(e))
                else:
                    self.add_component(vevent)
                    vmap.setdefault(str(vevent['UID']), VMatch()).add(vevent)

            for vmatch in vmap.values():
                vevent = vmatch.parent
                if vevent is not None:
                    try:
                        event = self.page._getEventFromUid(request, vevent['UID'])
                    except ObjectDoesNotExist:
                        numSuccess += self._createEventPage(request, vevent)
                    else:
                        if event:
                            numSuccess += self._updateEventPage(request, vevent, event)
        if numSuccess:
            messages.success(request, "{} iCal events loaded".format(numSuccess))
        if numFail:
            messages.error(request, "Could not load {} iCal events".format(numFail))

    def _updateEventPage(self, request, vevent, event):
        numUpdated = 0
        if vevent.modifiedDt > event.latest_revision_created_at:
            vevent.toPage(event)
            _saveRevision(request, event)
            numUpdated += 1

        vchildren  = vevent.vchildren[:]
        vchildren += [CancellationVEvent.fromExDate(vevent, exDate)
                      for exDate in vevent.exDates]
        for vchild in vchildren:
            try:
                exception = vchild.Page.objects.child_of(event)            \
                                  .get(except_date=vchild['RECURRENCE-ID'].date())
            except ObjectDoesNotExist:
                self._createExceptionPage(request, event, vchild)
            else:
                if exception.isAuthorized(request):
                    self._updateExceptionPage(request, vchild, exception)
        return numUpdated

    def _updateExceptionPage(self, request, vchild, exception):
        if vchild.modifiedDt > exception.latest_revision_created_at:
            vchild.toPage(exception)
            _saveRevision(request, exception)

    def _createEventPage(self, request, vevent):
        event = vevent.makePage(uid=vevent['UID'])
        _addPage(request, self.page, event)
        _saveRevision(request, event)
        numCreated = 1

        vchildren  = vevent.vchildren[:]
        vchildren += [CancellationVEvent.fromExDate(vevent, exDate)
                      for exDate in vevent.exDates]
        for vchild in vchildren:
            self._createExceptionPage(request, event, vchild)
        return numCreated

    def _createExceptionPage(self, request, event, vchild):
        exception = vchild.makePage(overrides=event)
        _addPage(request, event, exception)
        _saveRevision(request, exception)

# ------------------------------------------------------------------------------
def _addPage(request, parent, page):
    page.owner = request.user
    page.live  = bool(request.POST.get('action-publish'))
    parent.add_child(instance=page)

def _saveRevision(request, page):
    revision = page.save_revision(request.user,
                                  bool(request.POST.get('action-submit')))
    if bool(request.POST.get('action-publish')):
        revision.publish()

# ------------------------------------------------------------------------------
class vDt(vDDDTypes):
    """Smooths over some date-vs-datetime and aware-vs-naive differences"""
    def __init__(self, value=None, *, inclusive=False):
        self.dt = None
        if value is not None:
            if hasattr(value, 'dt'):
                value = value.dt
            if isinstance(value, dt.date) and inclusive:
                value += value.timedelta(days=1)
            super().__init__(value)

    def __bool__(self):
        return bool(self.dt)

    def __eq__(self, value):
        if hasattr(value, 'dt'):
            value = value.dt
        return self.dt == value

    def date(self, inclusive=False):
        if isinstance(self.dt, dt.datetime):
            return self.dt.date()
        elif isinstance(self.dt, dt.date):
            if inclusive:
                return self.dt - dt.timedelta(days=1)
            else:
                return self.dt

    def time(self):
        if isinstance(self.dt, dt.datetime):
            return self.dt.time()

    def datetime(self, timeDefault=dt.time.min):
        tz = timezone.get_default_timezone()
        if isinstance(self.dt, dt.datetime):
            if timezone.is_aware(self.dt):
                return self.dt
            else:
                return timezone.make_aware(self.dt, tz)
        elif isinstance(self.dt, dt.date):
            return getAwareDatetime(self.dt, None, tz, timeDefault)

    def tzinfo(self):
        return getattr(self.dt, 'tzinfo', None)

    def zone(self):
        tzinfo = self.tzinfo()
        if hasattr(tzinfo, 'zone'):
            return tzinfo.zone
        elif hasattr(tzinfo, 'tzname'):
            return tzinfo.tzname(None)

    def timezone(self):
        zone = self.zone()
        if zone:
            try:
                return pytz.timezone(zone)
            except pytz.exceptions.UnknownTimeZoneError as e:
                raise CalendarTypeError(str(e)) from e
        return timezone.get_default_timezone()

class vSmart(vText):
    """Text property that automatically decodes encoded strings"""
    def __str__(self):
        retval = super().__str__()
        param = self.params.get('ENCODING', "").upper()
        if param == 'QUOTED-PRINTABLE':
            retval = quopri.decodestring(retval).decode(self.encoding, 'ignore')
        elif param == 'BASE64':
            retval = base64.b64decode(retval).decode(self.encoding, 'ignore')
        return retval

from icalendar.cal import types_factory
types_factory['date']      = vDt
types_factory['date-time'] = vDt
types_factory['text']      = vSmart

# ------------------------------------------------------------------------------
class TimeZoneSpan:
    """Combines common time zones"""
    class NotInitializedError(RuntimeError): pass

    def __init__(self, vevent=None):
        self.firstDt = None
        self.lastDt  = None
        if vevent is not None:
            self.add(vevent)

    def add(self, vevent):
        firstDt = vDt(vevent['DTSTART']).datetime()
        lastDt  = vDt(vevent.get('DTEND')).datetime(dt.time.max)
        if not lastDt:
            lastDt = firstDt + dt.timedelta(days=2) # it's a guess

        # use until if it is available
        rrule = vevent.get('RRULE', {})
        untilDt = vDt(rrule.get('UNTIL', [None])[0]).datetime(dt.time.max)
        if untilDt and untilDt > lastDt:
            lastDt = untilDt

        if self.firstDt is None or firstDt < self.firstDt:
            self.firstDt = firstDt
        if self.lastDt is None or lastDt > self.lastDt:
            self.lastDt = lastDt

    def createVTimeZone(self, tz):
        if self.firstDt is None or self.lastDt is None:
            raise self.NotInitializedError()
        return create_timezone(tz, self.firstDt, self.lastDt)

# ------------------------------------------------------------------------------
class VMatch:
    """Matches recurring events with their exceptions"""
    class DuplicateError(RuntimeError): pass

    def __init__(self):
        self.parent  = None
        self.orphans = []

    def add(self, component):
        if isinstance(component, ExceptionVEvent):
            self._addChild(component)
        else:
            self._addParent(component)

    def _addChild(self, component):
        if self.parent:
            self.parent.vchildren.append(component)
        else:
            self.orphans.append(component)

    def _addParent(self, component):
        if self.parent:
            raise self.DuplicateError("UID {}".format(component['UID']))
        self.parent = component
        self.parent.vchildren += self.orphans
        self.orphans.clear()

# ------------------------------------------------------------------------------
class VEventFactory:
    """Creates VEvent objects"""
    def makeFromProps(self, props):
        if 'UID' not in props:
            raise CalendarTypeError("Missing UID")
        if 'DTSTAMP' not in props:
            raise CalendarTypeError("Missing DTSTAMP")
        dtstart = props.get('DTSTART')
        if not dtstart:
            raise CalendarTypeError("Missing DTSTART")

        dtend    = props.get('DTEND')
        duration = props.get('DURATION')
        if duration:
            if dtend:
                # dtend and duration must not occur in the same event properties
                raise CalendarTypeError("Both DURATION and DTEND set")
            else:
                dtend = props['DTEND'] = vDt(dtstart.dt + duration.dt)
        else:
            if not dtend:
                if isinstance(dtstart.dt, dt.date):
                    dtend = vDt(dtstart + dt.timedelta(days=1))
                else:
                    dtend = dtstart
        if type(dtstart.dt) != type(dtend.dt):
            raise CalendarTypeError("DTSTART and DTEND types do not match")
        if dtstart.timezone() != dtend.timezone():
            # Yes it is valid, but Joyous does not support it
            raise CalendarTypeError("DTSTART.timezone != DTEND.timezone")

        rrule = props.get('RRULE')
        if rrule is not None:
            if type(rrule) == list:
                # TODO support multiple RRULEs?
                raise CalendarTypeError("Multiple RRULEs")
            return RecurringVEvent.fromProps(props)

        recurrenceId = props.get('RECURRENCE-ID')
        if recurrenceId:
            if dtstart.timezone() != recurrenceId.timezone():
                # Also valid, but still Joyous does not support it
                raise CalendarTypeError("DTSTART.timezone != RECURRENCE-ID.timezone")

            if recurrenceId == dtstart:
                return ExtraInfoVEvent.fromProps(props)
            else:
                return PostponementVEvent.fromProps(props)

        if (dtstart.date() != dtend.date(inclusive=True)):
            return MultidayVEvent.fromProps(props)
        else:
            return SimpleVEvent.fromProps(props)

    def makeFromPage(self, page):
        if isinstance(page, SimpleEventPage):
            return SimpleVEvent.fromPage(page)

        elif isinstance(page, MultidayEventPage):
            return MultidayVEvent.fromPage(page)

        elif isinstance(page, RecurringEventPage):
            return RecurringVEvent.fromPage(page)

        elif isinstance(page, EventExceptionBase):
            return RecurringVEvent.fromPage(page.overrides)

        else:
            raise CalendarTypeError("Unsupported page type")

VCalendar.factory = VEventFactory()

# ------------------------------------------------------------------------------
class VEvent(Event, VComponentMixin):
    def __init__(self):
        super().__init__()
        self.vchildren = []

    @classmethod
    def fromPage(cls, page):
        vevent = cls()
        firstRevision = page.revisions.order_by("created_at").first()
        vevent.set('URL',           page.full_url)
        vevent.set('SUMMARY',       page.title)
        vevent.set('SEQUENCE',      page.revisions.count())
        vevent.set('DTSTAMP',       vDatetime(timezone.now()))
        vevent.set('CREATED',       vDatetime(firstRevision.created_at))
        vevent.set('LAST-MODIFIED', vDatetime(page.latest_revision_created_at))
        return vevent

    @classmethod
    def fromProps(cls, props):
        vevent = cls()
        vevent.update(props)
        return vevent

    def toPage(self, page):
        page.title      = str(self.get('SUMMARY', ""))

    def makePage(self, **kwargs):
        if not hasattr(self, 'Page'):
            raise NotImplementedError()
        page = self.Page(**kwargs)
        self.toPage(page)
        return page

    @property
    def modifiedDt(self):
        prop = self.get('LAST-MODIFIED') or self.get('DTSTAMP')
        return prop.datetime()

    @property
    def exDates(self):
        exDates = self.get('EXDATE', [])
        if type(exDates) != list:
            exDates = [exDates]
        dtType = type(self['DTSTART'].dt)
        retval = {exDate for vddd in exDates for exDate in vddd.dts
                  if type(exDate.dt) == dtType}
        return list(retval)

# ------------------------------------------------------------------------------
class SimpleVEvent(VEvent):
    Page = SimpleEventPage

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        # FIXME support Anniversary date type events?
        dtstart = getAwareDatetime(page.date, page.time_from, page.tz, dt.time.min)
        dtend   = getAwareDatetime(page.date, page.time_to, page.tz, dt.time.max)
        vevent.set('UID',         page.uid)
        vevent.set('DTSTART',     vDatetime(dtstart))
        vevent.set('DTEND',       vDatetime(dtend))
        vevent.set('DESCRIPTION', page.details)
        vevent.set('LOCATION',    page.location)
        # TODO CATEGORY
        return vevent

    def toPage(self, page):
        super().toPage(page)
        assert page.uid == self.get('UID')
        dtstart  = self['DTSTART']
        # TODO consider an option to convert UTC timezone events into local time
        dtend    = vDt(self.get('DTEND'))
        page.details    = str(self.get('DESCRIPTION', ""))
        page.location   = str(self.get('LOCATION', ""))
        page.date       = dtstart.date()
        page.time_from  = dtstart.time()
        page.time_to    = dtend.time()
        page.tz         = dtstart.timezone()

# ------------------------------------------------------------------------------
class MultidayVEvent(VEvent):
    Page = MultidayEventPage

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        # FIXME support Anniversary date type events?
        dtstart = getAwareDatetime(page.date_from, page.time_from, page.tz, dt.time.min)
        dtend   = getAwareDatetime(page.date_to, page.time_to, page.tz, dt.time.max)
        vevent.set('UID',         page.uid)
        vevent.set('DTSTART',     vDatetime(dtstart))
        vevent.set('DTEND',       vDatetime(dtend))
        vevent.set('DESCRIPTION', page.details)
        vevent.set('LOCATION',    page.location)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        assert page.uid == self.get('UID')
        dtstart  = self['DTSTART']
        # TODO consider an option to convert UTC timezone events into local time
        dtend    = vDt(self.get('DTEND'))
        page.details    = str(self.get('DESCRIPTION', ""))
        page.location   = str(self.get('LOCATION', ""))
        page.date_from  = dtstart.date()
        page.time_from  = dtstart.time()
        page.date_to    = dtend.date(inclusive=True)
        page.time_to    = dtend.time()
        page.tz         = dtstart.timezone()

# ------------------------------------------------------------------------------
class RecurringVEvent(VEvent):
    Page = RecurringEventPage

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        minDt   = pytz.utc.localize(dt.datetime.min)
        # FIXME support Anniversary date type events?
        dtstart = page._getMyFirstDatetimeFrom() or minDt
        dtend   = page._getMyFirstDatetimeTo()   or minDt
        vevent.set('UID',         page.uid)
        vevent.set('DTSTART',     vDatetime(dtstart))
        vevent.set('DTEND',       vDatetime(dtend))
        vevent.set('DESCRIPTION', page.details)
        vevent.set('LOCATION',    page.location)
        vevent.vchildren, exDates = cls.__getExceptions(page)
        if exDates:
            vevent.set('EXDATE', exDates)
        vevent.set('RRULE', vRecur.from_ical(page.repeat._getRrule()))
        return vevent

    @classmethod
    def __getExceptions(cls, page):
        vchildren = []
        exDates   = []
        for cancellation in CancellationPage.objects.live().child_of(page) \
                                            .select_related("postponementpage"):
            postponement = getattr(cancellation, "postponementpage", None)
            if postponement:
                vchildren.append(PostponementVEvent.fromPage(postponement))
            else:
                excludeDt = getAwareDatetime(cancellation.except_date,
                                             cancellation.time_from,
                                             cancellation.tz, dt.time.min)
                exDates.append(excludeDt)
                # NB any cancellation title or details are going to be lost
                # vchildren.append(CancellationVEvent.fromPage(cancellation))

            # if not postponement and cancellation.cancellation_title == "":
            #     excludeDt = getAwareDatetime(cancellation.except_date,
            #                                  cancellation.time_from,
            #                                  cancellation.tz, dt.time.min)
            #     exDates.append(excludeDt)
            # else:
            #     if cancellation.title != "":
            #         vchildren.append(CancellationVEvent.fromPage(cancellation))
            #     if postponement:
            #         vchildren.append(PostponementVEvent.fromPage(postponement))

        for info in ExtraInfoPage.objects.live().child_of(page):
            vchildren.append(ExtraInfoVEvent.fromPage(info))
        return vchildren, exDates

    def toPage(self, page):
        super().toPage(page)
        assert page.uid == self.get('UID')
        dtstart  = self['DTSTART']
        dtend    = vDt(self.get('DTEND'))
        rrule = self['RRULE']
        until = vDt(rrule.get('UNTIL', [None])[0])
        if until:
            rrule['UNTIL'] = [until.date()]
        page.details    = str(self.get('DESCRIPTION', ""))
        page.location   = str(self.get('LOCATION', ""))
        page.repeat     = Recurrence(rrule.to_ical().decode(),
                                     dtstart=dtstart.date())
        page.time_from  = dtstart.time()
        page.time_to    = dtend.time()
        page.tz         = dtstart.timezone()

# ------------------------------------------------------------------------------
class ExceptionVEvent(VEvent):
    def __init__(self):
        super().__init__()

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        exceptDt = getAwareDatetime(page.except_date, page.overrides.time_from,
                                    page.tz, dt.time.min)
        dtstart  = getAwareDatetime(page.except_date, page.time_from, page.tz,
                                    dt.time.min)
        dtend    = getAwareDatetime(page.except_date, page.time_to, page.tz,
                                    dt.time.max)
        vevent.set('UID',           page.overrides.uid)
        vevent.set('RECURRENCE-ID', vDatetime(exceptDt))
        vevent.set('DTSTART',       vDatetime(dtstart))
        vevent.set('DTEND',         vDatetime(dtend))
        vevent.set('LOCATION',      page.overrides.location)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        assert page.overrides.uid == self.get('UID')
        page.except_date = self['RECURRENCE-ID'].date()

# ------------------------------------------------------------------------------
class ExtraInfoVEvent(ExceptionVEvent):
    Page = ExtraInfoPage

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        vevent.set('SUMMARY',       page.extra_title or page.overrides.title)
        vevent.set('DESCRIPTION',   page.extra_information)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        page.extra_title       = str(self.get('SUMMARY', ""))
        page.extra_information = str(self.get('DESCRIPTION', ""))

# ------------------------------------------------------------------------------
class CancellationVEvent(ExceptionVEvent):
    Page = CancellationPage

    def property_items(self, recursive=True, sorted=True):
        # Cancellations are represented by EXDATE in VEVENT not as their own
        # VEVENT instance.  Yes, this means the cancellation_title and
        # cancellation_details are lost.
        return []

    @classmethod
    def fromExDate(cls, vparent, exDate):
        vevent = cls()
        vevent.set('DTSTAMP',       vparent['DTSTAMP'])
        vevent.set('UID',           vparent['UID'])
        vevent.set('RECURRENCE-ID', vDt(exDate))
        vparent.vchildren.append(vevent)
        return vevent

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        vevent.set('SUMMARY',       page.cancellation_title)
        vevent.set('DESCRIPTION',   page.cancellation_details)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        page.cancellation_title   = str(self.get('SUMMARY', ""))
        page.cancellation_details = str(self.get('DESCRIPTION', ""))

# ------------------------------------------------------------------------------
class PostponementVEvent(ExceptionVEvent):
    Page = PostponementPage

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        dtstart = getAwareDatetime(page.date, page.time_from, page.tz, dt.time.min)
        dtend   = getAwareDatetime(page.date, page.time_to, page.tz, dt.time.max)
        vevent.set('UID',         page.uid)
        vevent.set('SUMMARY',     page.postponement_title)
        vevent.set('DTSTART',     vDatetime(dtstart))
        vevent.set('DTEND',       vDatetime(dtend))
        vevent.set('DESCRIPTION', page.details)
        vevent.set('LOCATION',    page.location)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        assert page.uid == self.get('UID')
        dtstart  = self['DTSTART']
        dtend    = vDt(self.get('DTEND'))
        page.postponement_title = str(self.get('SUMMARY', ""))
        page.details            = str(self.get('DESCRIPTION', ""))
        page.location           = str(self.get('LOCATION', ""))
        page.date               = dtstart.date()
        page.time_from          = dtstart.time()
        page.time_to            = dtend.time()

    def makePage(self, **kwargs):
        if 'uid' not in kwargs:
            kwargs['uid'] = self.get('UID')
        return super().makePage(**kwargs)

# ------------------------------------------------------------------------------
class RawVEvent(VEvent):
    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        # FIXME
        return vevent

    def toPage(self, page):
        super().toPage(page)
        # FIXME

    def makePage(self):
        #page = IcalEventPage(uid = self['UID'])
        # FIXME
        #return page
        pass

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
