# ------------------------------------------------------------------------------
# Recurrence
# ------------------------------------------------------------------------------
# Somewhat based upon RFC5545 RRules, implemented using dateutil.rrule
# Does not support timezones ... and probably never will
# Does not support a frequency of by hour, by minute or by second
#
# See also:
#   https://github.com/django-recurrence/django-recurrence
#   https://github.com/dakrauth/django-swingtime

import sys
from operator import attrgetter
import calendar
import json
import datetime as dt
from django.db.models import Field
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.fields import CharField
from django.forms.widgets import MultiWidget, NumberInput, Select, \
        CheckboxSelectMultiple
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.forms import Media
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from wagtail.utils.widgets import WidgetWithScript
from wagtail.wagtailadmin.widgets import AdminDateInput
from wagtail.wagtailadmin.edit_handlers import BaseFieldPanel
from dateutil.rrule import rrule, rrulestr, rrulebase
from dateutil.rrule import DAILY, WEEKLY, MONTHLY, YEARLY
from dateutil.rrule import weekday as rrweekday
from dateutil.parser import parse as dt_parse
from .utils.telltime import dateFormatDMY
from .utils.manythings import toOrdinal, hrJoin

# ------------------------------------------------------------------------------
class Weekday(rrweekday):
    def __repr__(self):
        s = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")[self.weekday]
        if not self.n:
            return s
        else:
            return "{:+d}{}".format(self.n, s)

    def __str__(self):
        s = calendar.day_name[self.weekday]
        if not self.n:
            return s
        else:
            return "{} {}".format(toOrdinal(self.n), s)

# ------------------------------------------------------------------------------
class Recurrence(rrulebase):
    def __init__(self, *args, **kwargs):
        super().__init__()
        arg0 = args[0] if len(args) else None
        if isinstance(arg0, str):
            self.rule = rrulestr(arg0)
            if not isinstance(self.rule, rrule):
                raise ValueError("Only support simple RRules for now")
        elif isinstance(arg0, Recurrence):
            self.rule = arg0.rule
        elif isinstance(arg0, rrule):
            self.rule = arg0
        else:
            self.rule = rrule(*args, **kwargs)

    # expose all
    dtstart     = property(attrgetter("rule._dtstart"))
    freq        = property(attrgetter("rule._freq"))
    interval    = property(attrgetter("rule._interval"))
    wkst        = property(attrgetter("rule._wkst"))
    until       = property(attrgetter("rule._until"))
    count       = property(attrgetter("rule._count"))
    bymonth     = property(attrgetter("rule._bymonth"))
    byweekno    = property(attrgetter("rule._byweekno"))
    byyearday   = property(attrgetter("rule._byyearday"))
    byeaster    = property(attrgetter("rule._byeaster"))
    bysetpos    = property(attrgetter("rule._bysetpos"))

    @property
    def byweekday(self):
        retval = []
        if self.rule._byweekday:
            retval += [Weekday(day) for day in self.rule._byweekday]
        if self.rule._bynweekday:
            retval += [Weekday(day, n) for day, n in self.rule._bynweekday]
        return retval

    @property
    def bymonthday(self):
        retval = []
        if self.rule._bymonthday:
            retval += self.rule._bymonthday
        if self.rule._bynmonthday:
            retval += self.rule._bynmonthday
        return retval

    def _iter(self):
        return self.rule._iter()

    def getCount(self):
        return self.rule.count()

    def __repr__(self):
        freqOptions = ("YEARLY", "MONTHLY", "WEEKLY", "DAILY")
        if self.freq >= len(freqOptions): return ""
        parts = ["FREQ={}".format(freqOptions[self.freq])]
        if self.interval and self.interval != 1:
            parts.append("INTERVAL={}".format(self.interval))
        if self.wkst:
            parts.append("WKST={!r}".format(Weekday(self.wkst)))
        if self.count:
            parts.append("COUNT={}".format(self.count))
        if self.until:
            parts.append("UNTIL={:%Y%m%d}".format(self.until))
        for name, value in [('BYSETPOS',   self.bysetpos),
                            ('BYDAY',      self.byweekday),
                            ('BYMONTH',    self.bymonth),
                            ('BYMONTHDAY', self.bymonthday),
                            ('BYYEARDAY',  self.byyearday),
                            ('BYWEEKNO',   self.byweekno)]:
            if value:
                parts.append("{}={}".format(name,
                                            ",".join(repr(v) for v in value)))
        rrule = "RRULE:{}".format(";".join(parts))
        dtstart = ""
        if self.dtstart:
            dtstart = "DTSTART:{:%Y%m%d}\n".format(self.dtstart)
        retval = dtstart + rrule
        return retval

    def __str__(self):
        retval = ""
        if self.freq == DAILY:
            if self.interval > 1:
                retval = "Every {} days".format(self.interval)
            else:
                retval = "Daily"
        elif self.freq == WEEKLY:
            days = ["{}s".format(d) for d in self.byweekday]
            retval = hrJoin(days)
            if self.interval == 2:
                retval = "Fortnightly on {}".format(retval)
            elif self.interval > 2:
                retval = "Every {} weeks on {}".format(self.interval, retval)
        elif self.freq in (MONTHLY, YEARLY):
            if self.freq == MONTHLY:
                of = " of the month"
            else:
                months = [calendar.month_name[m] for m in self.bymonth]
                of = " of {}".format(hrJoin(months))
            days = []
            if self.byweekday:
                if len(self.byweekday) == 7 and all(not day.n for day in self.byweekday):
                    retval = "Everyday"
                    of = ""
                else:
                    days = ["{}".format(d) for d in self.byweekday]
                    retval = hrJoin(days)
                    if not self.byweekday[0].n:
                        retval = "Every "+retval
                        of = ""
                    else:
                        retval = "The {}".format(retval)
            elif self.bymonthday:
                days = [toOrdinal(d) for d in self.bymonthday]
                retval = "The {} day".format(hrJoin(days))
            retval += of
            if self.interval >= 2:
                if self.freq == MONTHLY:
                    retval = "{}, every {} months".format(retval, self.interval)
                else:
                    retval = "{}, every {} years".format(retval, self.interval)
        if self.until:
            # TODO make format configurable
            retval += " (until {})".format(dateFormatDMY(self.until))
        return retval

# ------------------------------------------------------------------------------
class RecurrenceField(Field):
    description = "The rule for recurring events"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 255
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection, context):
        return self.to_python(value)

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, Recurrence):
            return value
        try:
            return Recurrence(value)
        except (TypeError, ValueError, UnboundLocalError) as err:
            raise ValidationError("Invalid input for recurrence {}".format(err))

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def get_prep_value(self, rule):
        return repr(rule)

    def get_prep_lookup(self, lookup_type, value):
        raise TypeError('Lookup type %r not supported.' % lookup_type)

    def formfield(self, **kwargs):
        defaults = {'form_class': RecurrenceFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def get_internal_type(self):
        return "CharField"

# ------------------------------------------------------------------------------
(_EveryDay, _SameDay, _DayOfMonth) = (100, 101, 200)

class RecurrenceWidget(WidgetWithScript, MultiWidget):
    def __init__(self, attrs=None):
        freqOptions = [(3, "Daily"),
                       (2, "Weekly"),
                       (1, "Monthly"),
                       (0, "Yearly")]
        ordOptions1 = [(1, "The First"),
                       (2, "The Second"),
                       (3, "The Third"),
                       (4, "The Fourth"),
                       (5, "The Fifth"),
                       (-1, "The Last"),
                       (_EveryDay, "Every"),
                       (_SameDay, "The Same")]
        ordOptions2 = [(None, ""),
                       (1, "The First"),
                       (2, "The Second"),
                       (3, "The Third"),
                       (4, "The Fourth"),
                       (5, "The Fifth"),
                       (-1, "The Last")]
        dayOptions1  = enumerate(calendar.day_abbr)
        dayOptions2  = [(None, "")] + list(enumerate(calendar.day_name))
        dayOptions3  = list(enumerate(calendar.day_name)) +\
                       [(_DayOfMonth, "Day of the month")]
        monthOptions = enumerate(calendar.month_name[1:], 1)

        numAttrs = {'min': 1, 'max': 366}
        disableAttrs = {'disabled': True}
        if attrs:
            numAttrs.update(attrs)
            disableAttrs.update(attrs)
        widgets = [AdminDateInput(attrs=attrs),
                   Select(attrs=attrs, choices=freqOptions),         #1
                   NumberInput(attrs=numAttrs),
                   CheckboxSelectMultiple(attrs=attrs, choices=dayOptions1),
                   NumberInput(attrs=numAttrs),
                   AdminDateInput(attrs=attrs),                      #5
                   Select(attrs=attrs, choices=ordOptions1),
                   Select(attrs=attrs, choices=dayOptions3),
                   Select(attrs=disableAttrs, choices=ordOptions2),
                   Select(attrs=disableAttrs, choices=dayOptions2),
                   Select(attrs=disableAttrs, choices=ordOptions2),  #10
                   Select(attrs=disableAttrs, choices=dayOptions2),
                   Select(attrs=attrs, choices=monthOptions) ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        wdayChoices = []
        ordChoices  = [_SameDay,    None, None]
        dayChoices  = [_DayOfMonth, None, None]
        monChoice   = None
        if isinstance(value, Recurrence):
            if value.freq == WEEKLY:
                if value.byweekday:
                    wdayChoices = [day.weekday for day in value.byweekday]
            elif value.freq in (MONTHLY, YEARLY):
                if value.byweekday:
                    if len(value.byweekday) == 7 and all(not day.n for day in value.byweekday):
                        ordChoices[0] = _EveryDay
                        dayChoices[0] = _DayOfMonth
                    else:
                        # if len(value.byweekday) >= 1:
                        for (i, day) in enumerate(value.byweekday[:3]):
                            dayChoices[i] = day.weekday
                            ordChoices[i] = day.n or _EveryDay
                elif value.bymonthday:
                    ordChoices[0] = value.bymonthday[0]
                    if value.dtstart.day == ordChoices[0]:
                        ordChoices[0] = _SameDay
                    dayChoices[0] = _DayOfMonth
                if value.bymonth:
                    monChoice = value.bymonth[0]
                else:
                    value.dtstart.month
            return [value.dtstart,
                    value.freq,      #1
                    value.interval,
                    wdayChoices,
                    value.count,
                    value.until,     #5
                    ordChoices[0],
                    dayChoices[0],
                    ordChoices[1],
                    dayChoices[1],
                    ordChoices[2],   #10
                    dayChoices[2],
                    monChoice]
        else:
            return [None,
                    None,            #1
                    1,
                    wdayChoices,
                    None,
                    None,            #5
                    ordChoices[0],
                    dayChoices[0],
                    ordChoices[1],
                    dayChoices[1],
                    ordChoices[2],   #10
                    dayChoices[2],
                    monChoice]

    def render_html(self, name, value, attrs=None):
        if isinstance(value, list):
            values = value
        else:
            values = self.decompress(value)

        rendered_widgets = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = values[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            rendered_widgets.append(widget.render(name + '_%s' % i, widget_value, final_attrs))

        return render_to_string("joyous/widgets/recurrence_widget.html", {
            'widget':           self,
            'attrs':            attrs,
            'value_r':          repr(value),
            'value_s':          str(value),
            'widgets':          self.widgets,
            'rendered_widgets': rendered_widgets,
        })

    def render_js_init(self, id_, name, value):
        return 'initRecurrenceWidget({0});'.format(json.dumps(id_))

    def value_from_datadict(self, data, files, name):
        values = [widget.value_from_datadict(data, files, "{}_{}".format(name, i))
                  for i, widget in enumerate(self.widgets)]
        try:
            def toIntOrNone(value):
                return int(value) if value else None
            dtstart     = dt_parse(values[0]) if values[0] else None
            frequency   = toIntOrNone(values[1])
            interval    = toIntOrNone(values[2]) or None
            #count     = toIntOrNone(values[4]) or None
            dtuntil     = dt_parse(values[5]) if values[5] else None
            ordChoices  = [toIntOrNone(values[6]),
                           toIntOrNone(values[8]),
                           toIntOrNone(values[10])]
            dayChoices  = [toIntOrNone(values[7]),
                           toIntOrNone(values[9]),
                           toIntOrNone(values[11])]
            wdayChoices = []
            mdayChoices = None
            monChoices  = None
            if frequency == WEEKLY:
                if values[3]:
                    wdayChoices = [int(day) for day in values[3]]
            elif frequency in (MONTHLY, YEARLY):
                if dayChoices[0] == _DayOfMonth:    # day of the month
                    if ordChoices[0] == _EveryDay:      # every day, == daily
                        wdayChoices = range(7)
                    elif ordChoices[0] == _SameDay:     # the same day of the month
                        mdayChoices = None
                    else:
                        mdayChoices = [ordChoices[0]]
                else:                         # a day of the week
                    if ordChoices[0] == _EveryDay:      # every of this weekday
                        wdayChoices = [Weekday(dayChoices[0])]
                    elif ordChoices[0] == _SameDay:     # the same weekday of the month
                        wdayNum = (dtstart.day - 1) // 7 + 1
                        wdayChoices = [Weekday(dayChoices[0], wdayNum)]
                    else:
                        wdayChoices = [Weekday(dayChoices[0], ordChoices[0])]
                if dayChoices[1] != None and ordChoices[1] != None:
                    wdayChoices.append(Weekday(dayChoices[1], ordChoices[1]))
                if dayChoices[2] != None and ordChoices[2] != None:
                    wdayChoices.append(Weekday(dayChoices[2], ordChoices[2]))
                if frequency == YEARLY:
                    monChoices = [int(values[12])]

            retval = Recurrence(dtstart    = dtstart,
                                freq       = frequency,
                                interval   = interval,
                                byweekday  = wdayChoices,
                                #count      = count,
                                until      = dtuntil,
                                bymonthday = mdayChoices,
                                bymonth    = monChoices)
        except (TypeError, ValueError):
            retval = None
        return retval

    @property
    def media(self):
        return Media(css={'all': [static("joyous/css/recurrence_admin.css")]},
                     js=[static("joyous/js/recurrence_admin.js")])

# ------------------------------------------------------------------------------
class RecurrenceFormField(CharField):
    widget = RecurrenceWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        return value

    def validate(self, value):
        return super().validate(value)

# ------------------------------------------------------------------------------
class BaseRecurrencePanel(BaseFieldPanel):
    object_template = "joyous/edit_handlers/recurrence_object.html"

# ------------------------------------------------------------------------------
class RecurrencePanel(object):
    def __init__(self, field_name, classname=""):
        self.field_name = field_name
        self.classname = classname

    def bind_to_model(self, model):
        members = {
            'model':      model,
            'field_name': self.field_name,
            'classname':  self.classname,
            'widget':     RecurrenceWidget,
        }
        return type(str('_RecurrencePanel'), (BaseRecurrencePanel,), members)

# ------------------------------------------------------------------------------
class ExceptionDateInput(AdminDateInput):
    def __init__(self, attrs=None, format='%Y-%m-%d'):
        super().__init__(attrs=attrs, format=format)
        self.overrides_repeat = None

    def render_js_init(self, id_, name, value):
        if settings.JOYOUS_DAY_OF_WEEK_START == "Monday":
            dowStart = 1
        else:
            dowStart = 0
        return "initExceptionDateChooser({0}, {1}, {2});"\
               .format(json.dumps(id_), json.dumps(self.valid_dates()), json.dumps(dowStart))

    def valid_dates(self):
        valid_dates = -1
        if self.overrides_repeat:
            todayStart = dt.datetime.combine(dt.date.today(), dt.time.min)
            past = (todayStart - dt.timedelta(days=90)).replace(day=1)
            future = (todayStart + dt.timedelta(days=217)).replace(day=1)
            valid_dates = ["{:%Y%m%d}".format(occurence) for occurence in
                           self.overrides_repeat.between(past, future, inc=True)]
        return valid_dates

    @property
    def media(self):
        return Media(css={'all': [static("joyous/css/recurrence_admin.css")]},
                     js=[static("joyous/js/recurrence_admin.js")])

# TODO Should probably also do validation on the returned date?
# that would require ExceptionDateField and ExceptionDateFormField :(
# or else wait for custom form for page validation?
# https://github.com/torchbox/wagtail/pull/1867

# ------------------------------------------------------------------------------
class BaseExceptionDatePanel(BaseFieldPanel):
    def __init__(self, instance=None, form=None):
        super().__init__(instance=instance, form=form)
        widget = self.bound_field.field.widget
        widget.overrides_repeat = self.instance.overrides_repeat

# ------------------------------------------------------------------------------
class ExceptionDatePanel(object):
    def __init__(self, field_name, classname=""):
        self.field_name = field_name
        self.classname = classname

    def bind_to_model(self, model):
        members = {
            'model':      model,
            'field_name': self.field_name,
            'classname':  self.classname,
            'widget':     ExceptionDateInput,
        }
        return type(str('_ExceptionDatePanel'), (BaseExceptionDatePanel,), members)

# ------------------------------------------------------------------------------
