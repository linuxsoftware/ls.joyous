# ------------------------------------------------------------------------------
# Joyous Widgets
# ------------------------------------------------------------------------------
import sys
import json
import datetime as dt
from django.templatetags.static import static
from django.forms import Media
from django.utils.formats import get_format
from django.utils import timezone
from django.utils.translation import gettext as _
from django.forms.widgets import MultiWidget, NumberInput, Select, \
        CheckboxSelectMultiple, FileInput
from django.template.loader import render_to_string
from wagtail.admin.widgets import AdminDateInput, AdminTimeInput
from dateutil.parser import parse as dt_parse
from .utils.recurrence import Weekday, Recurrence, DAILY, WEEKLY, MONTHLY, YEARLY
from .utils.manythings import toTheOrdinal
from .utils.names import WEEKDAY_NAMES, WEEKDAY_ABBRS, MONTH_ABBRS

# ------------------------------------------------------------------------------
class Time12hrInput(AdminTimeInput):
    """
    Display and Edit time fields in a 12hr format
    """
    template_name = 'joyous/widgets/time12hr_input.html'

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format=None)

    def format_value(self, value):
        if isinstance(value, (dt.datetime, dt.time)):
            return value.strftime("%I:%M%P") # %P for lower case am/pm
        else:
            return value

    @property
    def media(self):
        return Media(js=[static('joyous/js/vendor/moment-2.22.0.min.js'),
                         static("joyous/js/time12hr_admin.js")])

# ------------------------------------------------------------------------------
(EVERY_DAY, SAME_DAY, DAY_OF_MONTH) = (100, 101, 200)

class RecurrenceWidget(MultiWidget):
    """
    Widget for entering the rule of a recurrence
    """
    template_name = 'joyous/widgets/recurrence_widget.html'

    def __init__(self, attrs=None):
        freqOptions = [(DAILY,   _("Daily")),
                       (WEEKLY,  _("Weekly")),
                       (MONTHLY, _("Monthly")),
                       (YEARLY,  _("Yearly"))]
        ordOptions1 = [(1,  toTheOrdinal(1)),
                       (2,  toTheOrdinal(2)),
                       (3,  toTheOrdinal(3)),
                       (4,  toTheOrdinal(4)),
                       (5,  toTheOrdinal(5)),
                       (-1, toTheOrdinal(-1)),
                       (EVERY_DAY, _("Every")),
                       (SAME_DAY, _("The Same"))]
        ordOptions2 = [(None, ""),
                       (1,    toTheOrdinal(1)),
                       (2,    toTheOrdinal(2)),
                       (3,    toTheOrdinal(3)),
                       (4,    toTheOrdinal(4)),
                       (5,    toTheOrdinal(5)),
                       (-1,   toTheOrdinal(-1))]
        dayOptions1  = enumerate(WEEKDAY_ABBRS)
        dayOptions2  = [(None, "")] + list(enumerate(WEEKDAY_NAMES))
        dayOptions3  = list(enumerate(WEEKDAY_NAMES)) +\
                       [(DAY_OF_MONTH, _("Day of the month"))]
        monthOptions = enumerate(MONTH_ABBRS[1:], 1)

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
        ordChoices  = [SAME_DAY,    None, None]
        dayChoices  = [DAY_OF_MONTH, None, None]
        monChoices  = []
        if isinstance(value, Recurrence):
            if value.freq == WEEKLY:
                if value.byweekday:
                    wdayChoices = [day.weekday for day in value.byweekday]
            elif value.freq in (MONTHLY, YEARLY):
                if value.byweekday:
                    if len(value.byweekday) == 7 and all(not day.n for day in value.byweekday):
                        ordChoices[0] = EVERY_DAY
                        dayChoices[0] = DAY_OF_MONTH
                    else:
                        for (i, day) in enumerate(value.byweekday[:3]):
                            dayChoices[i] = day.weekday
                            ordChoices[i] = day.n or EVERY_DAY
                elif value.bymonthday:
                    ordChoices[0] = value.bymonthday[0]
                    if value.dtstart.day == ordChoices[0]:
                        ordChoices[0] = SAME_DAY
                    dayChoices[0] = DAY_OF_MONTH
                if value.bymonth:
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

    def get_context(self, name, value, attrs):
        """
        Return the context to use with the widget's template, e.g.
        {'widget': {
            'attrs': {'id': "id_repeat", 'required': True},
            'is_hidden': False,
            'name': "repeat",
            'required': True,
            'subwidgets': [... the context of all the component subwigets...],
            'template_name': "joyous/widgets/recurrence_widget.html",
            'value': "Tuesdays",
            'value_s': "Tuesdays",
            'value_r': "DTSTART:20181201\nRRULE:FREQ=WEEKLY;WKST=SU;BYDAY=TU",
            }}}
        """
        context = super().get_context(name, value, attrs)
        context['widget']['value_s'] = str(value)
        context['widget']['value_r'] = repr(value)
        return context

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
            wdayChoices = None
            mdayChoices = None
            monChoices  = None
            if freq == WEEKLY:
                if values[3]:
                    wdayChoices = [int(day) for day in values[3]]
            elif freq in (MONTHLY, YEARLY):
                if dayChoices[0] == DAY_OF_MONTH:    # day of the month
                    if ordChoices[0] == EVERY_DAY:      # every day, == daily
                        wdayChoices = range(7)
                    elif ordChoices[0] == SAME_DAY:     # the same day of the month
                        mdayChoices = None
                    else:
                        mdayChoices = [ordChoices[0]]
                else:                         # a day of the week
                    if ordChoices[0] == EVERY_DAY:      # every of this weekday
                        wdayChoices = [Weekday(dayChoices[0])]
                    elif ordChoices[0] == SAME_DAY:     # the same weekday of the month
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
        media = super()._get_media()
        media += Media(css={'all': [static("joyous/css/recurrence_admin.css")]},
                       js=[static("joyous/js/recurrence_admin.js")])
        return media

# ------------------------------------------------------------------------------
class ExceptionDateInput(AdminDateInput):
    """
    Display and Edit the dates which are the exceptions to a recurrence rule
    """
    template_name = 'joyous/widgets/exception_date_input.html'

    def __init__(self, attrs=None, format=None):
        super().__init__(attrs=attrs, format=format)
        self.overrides_repeat = None

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        config = {
            'dayOfWeekStart': get_format('FIRST_DAY_OF_WEEK'),
            'format':         self.js_format,
        }
        context['widget']['valid_dates'] = json.dumps(self.valid_dates())
        context['widget']['config_json'] = json.dumps(config)
        return context

    def valid_dates(self):
        valid_dates = None # null in JS
        if self.overrides_repeat:
            today = timezone.localdate()
            past = (today - dt.timedelta(days=200)).replace(day=1)
            future = (today + dt.timedelta(days=600)).replace(day=1)
            valid_dates = ["{:%Y%m%d}".format(occurence) for occurence in
                           self.overrides_repeat.between(past, future, inc=True)]
        return valid_dates

    @property
    def media(self):
        return Media(css={'all': [static("joyous/css/recurrence_admin.css")]},
                     js=[static("joyous/js/recurrence_admin.js")])

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
