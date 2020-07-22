# ------------------------------------------------------------------------------
# ical import/export format
# ------------------------------------------------------------------------------
import datetime as dt
import pytz
import base64
import quopri
from contextlib import suppress
from zipfile import is_zipfile, ZipFile
from icalendar import Calendar, Event
from icalendar import vDatetime, vRecur, vDDDTypes, vText
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import HttpResponse
from django.utils import html
from django.utils import timezone
from ls.joyous import __version__
from ..models import (SimpleEventPage, MultidayEventPage, RecurringEventPage,
        MultidayRecurringEventPage, EventExceptionBase, ExtraInfoPage,
        CancellationPage, PostponementPage, RescheduleMultidayEventPage,
        ClosedForHolidaysPage, ExtCancellationPage, EventBase, CalendarPage)
from ..utils.recurrence import Recurrence
from ..utils.telltime import getAwareDatetime
from .vtimezone import create_timezone
from .errors import CalendarTypeError, CalendarNotInitializedError

# ------------------------------------------------------------------------------
MAX_YEAR = 2038

# ------------------------------------------------------------------------------
class VComponentMixin:
    """Utilities for working with icalendar components"""
    def set(self, name, value, parameters=None, encode=1):
        if name in self:
            del self[name]
        self.add(name, value, parameters, encode)

# ------------------------------------------------------------------------------
class VResults:
    """The number of successes, failures and errors"""
    def __init__(self, success=0, fail=0, error=0):
        if type(success) is bool:
            success = int(success)
            fail    = int(not success)
        self.success = success
        self.fail    = fail
        self.error   = error

    def __add__(self, other):
        return VResults(self.success + other.success,
                        self.fail    + other.fail,
                        self.error   + other.error)

    def __eq__(self, other):
        return (self.success == other.success and
                self.fail    == other.fail    and
                self.error   == other.error)

    def __repr__(self):
        return "Success={}, Fail={}, Error={}".format(self.success, self.fail,
                                                      self.error)

# ------------------------------------------------------------------------------
class ICalHandler:
    """Serve and load iCalendar files"""
    def serve(self, page, request, *args, **kwargs):
        try:
            vcal = VCalendar.fromPage(page, request)
        except CalendarTypeError:
            return None
        response = HttpResponse(vcal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = \
            'attachment; filename={}.ics'.format(page.slug)
        return response

    def load(self, page, request, upload, **kwargs):
        isZip = is_zipfile(upload)
        upload.seek(0)
        if isZip:
            results = self._loadZip(page, request, upload, **kwargs)
        else:
            results = self._loadICal(page, request, upload, **kwargs)
        if results.success:
            messages.success(request, "{} iCal events loaded".format(results.success))
        if results.fail:
            messages.error(request, "Could not load {} iCal events".format(results.fail))

    def _loadZip(self, page, request, upload, **kwargs):
        results = VResults()
        with ZipFile(upload) as package:
            for info in package.infolist():
                if info.filename.endswith(".ics"):
                    with package.open(info) as calFile:
                        results += self._loadICal(page, request, calFile, **kwargs)
        return results

    def _loadICal(self, page, request, upload, **kwargs):
        vcal = VCalendar(page, **kwargs)
        results = vcal.load(request, upload.read())
        if results.error:
            name = getattr(upload, 'name', "")
            messages.error(request, "Could not parse iCalendar file "+name)
        return results

# ------------------------------------------------------------------------------
class VCalendar(Calendar, VComponentMixin):
    prodVersion = ".".join(__version__.split(".", 2)[:2])
    prodId = "-//linuxsoftware.nz//NONSGML Joyous v{}//EN".format(prodVersion)

    def __init__(self, page=None, utc2local=False):
        super().__init__(self)
        self.page = page
        self.utc2local = utc2local
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
        vevents = []
        tzs = {}
        for event in page._getAllEvents(request):
            vevent = cls.factory.makeFromPage(event, vcal.page)
            vevents.append(vevent)
            for vchild in vevent.vchildren:
                vevents.append(vchild)
            if event.tz and event.tz is not pytz.utc:
                tzs.setdefault(event.tz, TimeZoneSpan()).add(vevent)
        for tz, vspan in tzs.items():
            vtz = vspan.createVTimeZone(tz)
            # Put timezones up top. The RFC doesn't require this, but everyone
            # else does it.
            vcal.add_component(vtz)
        vcal.subcomponents.extend(vevents)
        return vcal

    @classmethod
    def _fromEventPage(cls, event):
        vcal = cls(cls._findCalendarFor(event))
        vevent = cls.factory.makeFromPage(event, vcal.page)
        if event.tz and event.tz is not pytz.utc:
            vtz = TimeZoneSpan(vevent).createVTimeZone(event.tz)
            vcal.add_component(vtz)
        vcal.add_component(vevent)
        for vchild in vevent.vchildren:
            vcal.add_component(vchild)
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

    def load(self, request, data):
        if self.page is None:
            raise CalendarNotInitializedError("No page set")

        # Typically, this information will consist of an iCalendar stream
        # with a single iCalendar object.  However, multiple iCalendar
        # objects can be sequentially grouped together in an iCalendar
        # stream.
        try:
            calStream = Calendar.from_ical(data, multiple=True)
        except Exception as e:
            #messages.debug(request, str(e))
            return VResults(error=1)

        self.clear()
        results = VResults()
        for cal in calStream:
            tz = timezone.get_current_timezone()
            zone = cal.get('X-WR-TIMEZONE', None)
            if zone:
                try:
                    tz = pytz.timezone(zone)
                except pytz.exceptions.UnknownTimeZoneError:
                    messages.warning(request, "Unknown time zone {}".format(zone))
            with timezone.override(tz):
                results += self._loadEvents(request, cal.walk(name="VEVENT"))
        return results

    def _loadEvents(self, request, vevents):
        results = VResults()
        vmap = {}
        for props in vevents:
            try:
                match = vmap.setdefault(str(props.get('UID')), VMatch())
                vevent = self.factory.makeFromProps(props, match.parent)
                if self.utc2local:
                    vevent._convertTZ()
            except CalendarTypeError as e:
                results.fail += 1
                #messages.debug(request, str(e))
            else:
                self.add_component(vevent)
                match.add(vevent)

        for vmatch in vmap.values():
            vevent = vmatch.parent
            if vevent is not None:
                try:
                    event = self.page._getEventFromUid(request, vevent['UID'])
                except PermissionDenied:
                    # No authority
                    results.fail += 1
                except ObjectDoesNotExist:
                    results += self._createEventPage(request, vevent)
                else:
                    results += self._updateEventPage(request, vevent, event)
        return results

    def _updateEventPage(self, request, vevent, event):
        allOk = True
        if vevent.modifiedDt > event.latest_revision_created_at:
            vevent.toPage(event)
            _saveRevision(request, event)

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
                else:
                    allOk = False
        return VResults(allOk)

    def _updateExceptionPage(self, request, vchild, exception):
        if vchild.modifiedDt > exception.latest_revision_created_at:
            vchild.toPage(exception)
            _saveRevision(request, exception)

    def _createEventPage(self, request, vevent):
        event = vevent.makePage(uid=vevent['UID'])
        _addPage(request, self.page, event)
        _saveRevision(request, event)

        vchildren  = vevent.vchildren[:]
        vchildren += [CancellationVEvent.fromExDate(vevent, exDate)
                      for exDate in vevent.exDates]
        for vchild in vchildren:
            self._createExceptionPage(request, event, vchild)
        return VResults(success=1)

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
            if type(value) == dt.date and inclusive:
                value += dt.timedelta(days=1)
            super().__init__(value)

    def __bool__(self):
        return bool(self.dt)

    def __eq__(self, value):
        if hasattr(value, 'dt'):
            value = value.dt
        return self.dt == value

    def date(self, inclusive=False):
        if type(self.dt) == dt.datetime:
            return self.dt.date()
        elif type(self.dt) == dt.date:
            if inclusive:
                return self.dt - dt.timedelta(days=1)
            else:
                return self.dt

    def time(self):
        if type(self.dt) == dt.datetime:
            return self.dt.time()

    def datetime(self, timeDefault=dt.time.min):
        tz = timezone.get_current_timezone()
        if type(self.dt) == dt.datetime:
            if timezone.is_aware(self.dt):
                return self.dt
            else:
                return timezone.make_aware(self.dt, tz)
        elif type(self.dt) == dt.date:
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
        tzinfo = self.tzinfo()
        if getattr(tzinfo, 'zone', None):
            try:
                # Return the timezone unbound from the datetime
                return pytz.timezone(tzinfo.zone)
            except pytz.exceptions.UnknownTimeZoneError as e:
                raise CalendarTypeError(str(e)) from e
        elif tzinfo is not None:
            return tzinfo
        else:
            return timezone.get_current_timezone()

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
        lastDt  = vDt(vevent['DTEND']).datetime(dt.time.max)

        rrule = vevent.get('RRULE', {})
        if rrule:
            # use until if it is available
            untilDt = vDt(rrule.get('UNTIL', [None])[0]).datetime(dt.time.max)
            if untilDt:
                lastDt = untilDt
            else:
                # pytz.timezones doesn't know any transition dates after 2038
                # either -- icalendar/src/icalendar/cal.py:526
                # using replace to keep the tzinfo
                lastDt = lastDt.replace(year=MAX_YEAR, month=12, day=31)

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
            # I don't know of any iCalendar producer that lists exceptions
            # before the recurring event, but the RFC doesn't seem to say that
            # it can't happen either.
            self.orphans.append(component)

    def _addParent(self, component):
        if self.parent:
            # duplicates should be caught before they get this far
            raise self.DuplicateError("UID {}".format(component['UID']))
        self.parent = component
        for orphan in self.orphans:
            # reprocess orphans now their parent has been found
            vevent = VCalendar.factory.makeFromProps(orphan, self.parent)
            self.parent.vchildren.append(vevent)
        self.orphans.clear()

# ------------------------------------------------------------------------------
class VEventFactory:
    """Creates VEvent objects"""
    def makeFromProps(self, props, parent):
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
                dtend = props['DTEND'] = vDt(dtstart, inclusive=True)
        if type(dtstart.dt) != type(dtend.dt):
            raise CalendarTypeError("DTSTART and DTEND types do not match")
        if dtstart.timezone() != dtend.timezone():
            # Yes it is valid, but Joyous does not support it
            raise CalendarTypeError("DTSTART.timezone != DTEND.timezone")

        numDays = (dtend.date(inclusive=True) - dtstart.date()).days + 1

        recurrenceId = props.get('RECURRENCE-ID')
        if recurrenceId is not None:
            if dtstart.timezone() != recurrenceId.timezone():
                # Also valid, but still Joyous does not support it
                raise CalendarTypeError("DTSTART.timezone != RECURRENCE-ID.timezone")

            # Don't worry if parent is not set first time through, orphans
            # will be collected when the parent turns up later.
            if (parent and recurrenceId == dtstart and
                parent.numDays == numDays and
                parent['DTEND'].time() == dtend.time() and
                (parent['SUMMARY'] != props['SUMMARY'] or
                 parent['DESCRIPTION'] != props['DESCRIPTION'] != "")):
                return ExtraInfoVEvent.fromProps(props)
            else:
                if numDays > 1:
                    return RescheduleMultidayVEvent.fromProps(props)
                elif parent and parent.numDays > 1:
                    return RescheduleMultidayVEvent.fromProps(props)
                else:
                    return PostponementVEvent.fromProps(props)

        elif parent:
            raise CalendarTypeError("Duplicate UID {}".format(props['UID']))

        rrule = props.get('RRULE')
        if rrule is not None:
            if type(rrule) == list:
                raise CalendarTypeError("Multiple RRULEs")
            if numDays > 1:
                return MultidayRecurringVEvent.fromProps(props)
            else:
                return RecurringVEvent.fromProps(props)

        if (dtstart.date() != dtend.date(inclusive=True)):
            return MultidayVEvent.fromProps(props)
        else:
            return SimpleVEvent.fromProps(props)

    def makeFromPage(self, page, calendar):
        if isinstance(page, SimpleEventPage):
            return SimpleVEvent.fromPage(page)

        elif isinstance(page, MultidayEventPage):
            return MultidayVEvent.fromPage(page)

        elif isinstance(page, MultidayRecurringEventPage):
            return MultidayRecurringVEvent.fromPage(page, calendar)

        elif isinstance(page, RecurringEventPage):
            return RecurringVEvent.fromPage(page, calendar)

        elif isinstance(page, EventExceptionBase):
            return RecurringVEvent.fromPage(page.overrides, calendar)

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
        pass

    def makePage(self, **kwargs):
        if not hasattr(self, 'Page'):
            raise NotImplementedError()
        page = self.Page(**kwargs)
        self.toPage(page)
        return page

    def _convertTZ(self):
        """Will convert UTC datetimes to the current local timezone"""
        tz = timezone.get_current_timezone()
        dtstart = self['DTSTART']
        dtend   = self['DTEND']
        if dtstart.zone() == "UTC":
            dtstart.dt = dtstart.dt.astimezone(tz)
        if dtend.zone() == "UTC":
            dtend.dt = dtend.dt.astimezone(tz)

    def _getDesc(self):
        altDesc = self.get('X-ALT-DESC')
        if altDesc and altDesc.params.get('FMTTYPE', "").lower() == "text/html":
            retval = str(altDesc)
        else:
            retval = str(self.get('DESCRIPTION', ""))
        return retval

    def _setDesc(self, desc):
        plainDesc = html.strip_tags(desc)
        if desc != plainDesc:
            self.set('X-ALT-DESC', desc, parameters={'FMTTYPE': "text/html"})
        self.set('DESCRIPTION', plainDesc)

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

    @property
    def numDays(self):
        dtstart = self['DTSTART']
        dtend   = self['DTEND']
        return (dtend.date(inclusive=True) - dtstart.date()).days + 1

# ------------------------------------------------------------------------------
class SimpleVEvent(VEvent):
    Page = SimpleEventPage

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        dtstart = getAwareDatetime(page.date, page.time_from, page.tz, dt.time.min)
        dtend   = getAwareDatetime(page.date, page.time_to, page.tz, dt.time.max)
        vevent.set('UID',         page.uid)
        vevent.set('DTSTART',     vDatetime(dtstart))
        vevent.set('DTEND',       vDatetime(dtend))
        vevent._setDesc(page.details)
        vevent.set('LOCATION',    page.location)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        assert page.uid == self.get('UID')
        page.title = str(self.get('SUMMARY', "")) or page.uid[:16]
        dtstart  = self['DTSTART']
        dtend    = self['DTEND']
        page.details    = self._getDesc()
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
        dtstart = getAwareDatetime(page.date_from, page.time_from, page.tz, dt.time.min)
        dtend   = getAwareDatetime(page.date_to, page.time_to, page.tz, dt.time.max)
        vevent.set('UID',         page.uid)
        vevent.set('DTSTART',     vDatetime(dtstart))
        vevent.set('DTEND',       vDatetime(dtend))
        vevent._setDesc(page.details)
        vevent.set('LOCATION',    page.location)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        assert page.uid == self.get('UID')
        page.title = str(self.get('SUMMARY', "")) or page.uid[:16]
        dtstart  = self['DTSTART']
        dtend    = self['DTEND']
        page.details    = self._getDesc()
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
    def fromPage(cls, page, calendar):
        if page.holidays is None and calendar is not None:
            # make sure we all have the same holidays
            page.holidays = calendar.holidays
        vevent = super().fromPage(page)
        minDt   = pytz.utc.localize(dt.datetime.min)
        dtstart = page._getMyFirstDatetimeFrom() or minDt
        dtend   = page._getMyFirstDatetimeTo(dtstart) or minDt
        vevent.set('UID',         page.uid)
        vevent.set('DTSTART',     vDatetime(dtstart))
        vevent.set('DTEND',       vDatetime(dtend))
        vevent._setDesc(page.details)
        vevent.set('LOCATION',    page.location)
        vevent.vchildren, exDates = cls.__getExceptions(page)
        if exDates:
            vevent.set('EXDATE', exDates)
        until = page.repeat.until
        if until:
            until = getAwareDatetime(until, dt.time.max, dtend.tzinfo)
            until = until.astimezone(pytz.utc)
        vevent.set('RRULE', vRecur.from_ical(page.repeat._getRrule(until)))
        return vevent

    @classmethod
    def __getExceptions(cls, page):
        vchildren = []
        excludes = set()
        for cancellation in CancellationPage.events.child_of(page):
            excludeDt = getAwareDatetime(cancellation.except_date,
                                         cancellation.time_from,
                                         cancellation.tz, dt.time.min)
            excludes.add(excludeDt)
            # NB any cancellation title or details are going to be lost

        for shutdown in ExtCancellationPage.events.child_of(page):
            # TODO Consider using RANGE:THISANDFUTURE
            for shutDate in shutdown._getMyDates(toDate=dt.date(MAX_YEAR,1,1)):
                excludeDt = getAwareDatetime(shutDate,
                                             shutdown.time_from,
                                             shutdown.tz, dt.time.min)
                excludes.add(excludeDt)
                # NB any cancellation title or details are going to be lost
                # ExtCancellationPage does not round-trip.  All imported
                # EXDATEs become plain cancellations

        closedHols = ClosedForHolidaysPage.events.hols(page.holidays)        \
                                          .child_of(page).first()
        if closedHols is not None:
            for closedDate in closedHols._getMyDates():
                if closedDate.year > MAX_YEAR:
                    break
                excludeDt = getAwareDatetime(closedDate,
                                             closedHols.time_from,
                                             closedHols.tz, dt.time.min)
                excludes.add(excludeDt)
                # NB any cancellation title or details are going to be lost
                # ClosedForHolidaysPage does not round-trip.  All imported
                # EXDATEs become plain cancellations

        for info in ExtraInfoPage.events.child_of(page):
            excludeDt = getAwareDatetime(info.except_date,
                                         info.time_from,
                                         info.tz, dt.time.min)
            if excludeDt not in excludes:
                vchildren.append(ExtraInfoVEvent.fromPage(info))

        for postponement in PostponementPage.events.child_of(page):
            excludeDt = getAwareDatetime(postponement.except_date,
                                         postponement.overrides.time_from,
                                         postponement.tz, dt.time.min)
            # Important that this remove is done after the ExtraInfo check
            excludes.remove(excludeDt)
            vchildren.append(PostponementVEvent.fromPage(postponement))

        exDates = list(excludes)
        exDates.sort()
        return vchildren, exDates

    def toPage(self, page):
        super().toPage(page)
        assert page.uid == self.get('UID')
        page.title = str(self.get('SUMMARY', "")) or page.uid[:16]
        dtstart  = self['DTSTART']
        dtend    = self['DTEND']
        rrule = self['RRULE']
        until = vDt(rrule.get('UNTIL', [None])[0])
        if until:
            untilDt = until.datetime().astimezone(dtstart.timezone())
            rrule['UNTIL'] = [untilDt.date()]
        page.details    = self._getDesc()
        page.location   = str(self.get('LOCATION', ""))
        page.repeat     = Recurrence(rrule.to_ical().decode(),
                                     dtstart=dtstart.date())
        page.num_days   = self.numDays
        page.time_from  = dtstart.time()
        page.time_to    = dtend.time()
        page.tz         = dtstart.timezone()

# ------------------------------------------------------------------------------
class MultidayRecurringVEvent(RecurringVEvent):
    Page = MultidayRecurringEventPage

# ------------------------------------------------------------------------------
class ExceptionVEvent(VEvent):
    def __init__(self):
        super().__init__()

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        daysDelta = dt.timedelta(days=page.num_days - 1)
        exceptDt = getAwareDatetime(page.except_date, page.overrides.time_from,
                                    page.tz, dt.time.min)
        dtstart  = getAwareDatetime(page.except_date, page.time_from,
                                    page.tz, dt.time.min)
        dtend    = getAwareDatetime(page.except_date + daysDelta, page.time_to,
                                    page.tz, dt.time.max)
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
        vevent._setDesc(page.extra_information)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        page.extra_title       = str(self.get('SUMMARY', ""))
        page.extra_information = self._getDesc()

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

    # this method is not currently used
    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        vevent.set('URL',           page.cancellation_url)
        vevent.set('SUMMARY',       page.cancellation_title)
        vevent._setDesc(page.cancellation_details)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        page.cancellation_title   = str(self.get('SUMMARY', ""))
        page.cancellation_details = self._getDesc()

# ------------------------------------------------------------------------------
class PostponementVEvent(ExceptionVEvent):
    Page = PostponementPage

    @classmethod
    def fromPage(cls, page):
        vevent = super().fromPage(page)
        daysDelta = dt.timedelta(days=page.num_days - 1)
        dtstart = getAwareDatetime(page.date, page.time_from,
                                   page.tz, dt.time.min)
        dtend   = getAwareDatetime(page.date + daysDelta, page.time_to,
                                   page.tz, dt.time.max)
        vevent.set('SUMMARY',     page.postponement_title)
        vevent.set('DTSTART',     vDatetime(dtstart))
        vevent.set('DTEND',       vDatetime(dtend))
        vevent._setDesc(page.details)
        vevent.set('LOCATION',    page.location)
        return vevent

    def toPage(self, page):
        super().toPage(page)
        dtstart  = self['DTSTART']
        dtend    = self['DTEND']
        page.postponement_title = str(self.get('SUMMARY', ""))
        page.details            = self._getDesc()
        page.location           = str(self.get('LOCATION', ""))
        page.date               = dtstart.date()
        page.num_days           = self.numDays
        page.time_from          = dtstart.time()
        page.time_to            = dtend.time()

    def makePage(self, **kwargs):
        return super().makePage(**kwargs)

# ------------------------------------------------------------------------------
class RescheduleMultidayVEvent(PostponementVEvent):
    Page = RescheduleMultidayEventPage

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
