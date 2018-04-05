# ------------------------------------------------------------------------------
# Joyous Widgets
# ------------------------------------------------------------------------------
import sys
import json
import datetime as dt
import calendar
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.forms import Media
from django.conf import settings
from django.utils.formats import get_format
from django.utils import timezone
from django.forms.widgets import MultiWidget, NumberInput, Select, \
        CheckboxSelectMultiple
from django.template.loader import render_to_string
from wagtail.utils.widgets import WidgetWithScript
from wagtail.admin.widgets import AdminDateInput, AdminTimeInput
from dateutil.parser import parse as dt_parse
from .recurrence import WEEKLY, MONTHLY, YEARLY
from .recurrence import Weekday, Recurrence

# ------------------------------------------------------------------------------
class Time12hrInput(AdminTimeInput):
    """
    Display and Edit time fields in a 12hr format
    """
    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format=None)

    def format_value(self, value):
        if isinstance(value, (dt.datetime, dt.time)):
            return value.strftime("%I:%M%P") # %P for lower case am/pm
        else:
            return value

    def render_js_init(self, id_, name, value):
        return "$(function() {{"                               \
               "  initTime12hrChooser({})"                     \
               "  }});".format(json.dumps(id_))

    @property
    def media(self):
        return Media(js=[static("joyous/js/time12hr_admin.js")])

# ------------------------------------------------------------------------------
if getattr(settings, "JOYOUS_TIME_INPUT", "12") in (12, "12"):
    TimeInput = Time12hrInput

    # Time12hrInput will not work unless django.forms.fields.TimeField
    # can process 12hr times, so sneak them into TIME_INPUT_FORMATS if
    # it isn't already there.  sneaky!
    # Note: strptime does not accept %P %p is for both cases here
    _12hrFormats = ['%I:%M%p', # 2:30pm
                    '%I%p']    # 7am
    _inputFormats = get_format("TIME_INPUT_FORMATS")
    if _12hrFormats[0] not in _inputFormats:
        _inputFormats += _12hrFormats
else:
    TimeInput = AdminTimeInput

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
        monthOptions = enumerate(calendar.month_abbr[1:], 1)

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
                   CheckboxSelectMultiple(attrs=attrs, choices=monthOptions) ]
        super().__init__(widgets, attrs)

    def decompress(self, value):
        wdayChoices = []
        ordChoices  = [_SameDay,    None, None]
        dayChoices  = [_DayOfMonth, None, None]
        monChoices  = []
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
                        for (i, day) in enumerate(value.byweekday[:3]):
                            dayChoices[i] = day.weekday
                            ordChoices[i] = day.n or _EveryDay
                elif value.bymonthday:
                    ordChoices[0] = value.bymonthday[0]
                    if value.dtstart.day == ordChoices[0]:
                        ordChoices[0] = _SameDay
                    dayChoices[0] = _DayOfMonth
                if value.bymonth:
                    #monChoice = value.bymonth[0]
                    monChoices = value.bymonth
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
                    monChoices]
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
                    monChoices]

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
            freq        = toIntOrNone(values[1])
            interval    = toIntOrNone(values[2]) or None
            #count      = toIntOrNone(values[4]) or None
            dtuntil     = dt_parse(values[5]) if values[5] else None
            ordChoices  = [toIntOrNone(values[6]),
                           toIntOrNone(values[8]),
                           toIntOrNone(values[10])]
            dayChoices  = [toIntOrNone(values[7]),
                           toIntOrNone(values[9]),
                           toIntOrNone(values[11])]
            wdayChoices = []
            mdayChoices = None
            monChoices  = []
            if freq == WEEKLY:
                if values[3]:
                    wdayChoices = [int(day) for day in values[3]]
            elif freq in (MONTHLY, YEARLY):
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
                if freq == YEARLY:
                    if values[12]:
                        monChoices = [int(month) for month in values[12]]

            retval = Recurrence(dtstart    = dtstart,
                                freq       = freq,
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
class ExceptionDateInput(AdminDateInput):
    def __init__(self, attrs=None, format='%Y-%m-%d'):
        super().__init__(attrs=attrs, format=format)
        self.overrides_repeat = None
        self.tz = None

    def render_js_init(self, id_, name, value):
        dowStart = get_format("FIRST_DAY_OF_WEEK")
        return "initExceptionDateChooser({0}, {1}, {2});"\
               .format(json.dumps(id_), json.dumps(self.valid_dates()), json.dumps(dowStart))

    def valid_dates(self):
        valid_dates = -1
        if self.overrides_repeat:
            today = timezone.localdate()
            past = (today - dt.timedelta(days=90)).replace(day=1)
            future = (today + dt.timedelta(days=217)).replace(day=1)
            valid_dates = ["{:%Y%m%d}".format(occurence) for occurence in
                           self.overrides_repeat.between(past, future, inc=True)]
        return valid_dates

    @property
    def media(self):
        return Media(css={'all': [static("joyous/css/recurrence_admin.css")]},
                     js=[static("joyous/js/recurrence_admin.js")])

# TODO Should probably also do validation on the returned date?
# that would require ExceptionDateField and ExceptionDateFormField :(
# or else use custom form for page validation?
# https://github.com/torchbox/wagtail/pull/1867

# ------------------------------------------------------------------------------
