# ------------------------------------------------------------------------------
# Test Edit Handlers
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import RequestFactory, TestCase, override_settings
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.formats import get_format_modules
from wagtail.admin.edit_handlers import get_form_for_model
from wagtail.admin.widgets import AdminTimeInput, AdminDateInput
from wagtail.core.models import Site, Page
from ls.joyous.models.events import CancellationPageForm
from ls.joyous.models import CalendarPage, CancellationPage, RecurringEventPage
from ls.joyous.utils.recurrence import Recurrence, MONTHLY, TU
from ls.joyous.edit_handlers import ExceptionDatePanel, ConcealedPanel
from ls.joyous.widgets import Time12hrInput, ExceptionDateInput
from .testutils import datetimetz, freeze_timetz, getPage
import ls.joyous.edit_handlers
import importlib

# ------------------------------------------------------------------------------
class TestExceptionDatePanel(TestCase):
    def setUp(self):
        self.home = getPage("/home/")
        self.user = User.objects.create_superuser('i', 'i@joy.test', 's3(r3t')
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(slug      = "leaders-meeting",
                                        title     = "Leaders' Meeting",
                                        repeat    = Recurrence(dtstart=dt.date(2016,2,16),
                                                               freq=MONTHLY,
                                                               byweekday=[TU(3)]),
                                        time_from = dt.time(19),
                                        tz        = "Asia/Tokyo")
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()

    def _getRequest(self):
        request = RequestFactory().get("/test")
        request.user = self.user
        request.session = {}
        request.site = Site.objects.get(is_default_site=True)
        return request

    def testWidget(self):
        self.assertIs(ExceptionDatePanel.widget, ExceptionDateInput)

    def testBindWithoutForm(self):
        cancellation = CancellationPage(owner = self.user,
                                        except_date = dt.date(2019,1,21))
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = panel.bind_to(instance=cancellation)
        self.assertIsNone(panel.form)

    def testBindWithoutOverrides(self):
        cancellation = CancellationPage(owner = self.user,
                                        except_date = dt.date(2019,1,21))
        Form = get_form_for_model(CancellationPage, form_class=CancellationPageForm)
        form = Form(instance=cancellation, parent_page=self.event)
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = panel.bind_to(instance=cancellation)
        panel = panel.bind_to(request=self._getRequest())
        panel = panel.bind_to(form=form)
        self.assertIsNotNone(panel.form)
        self.assertIsNone(panel.instance.overrides)

    def testBindOverridesRepeat(self):
        cancellation = CancellationPage(owner = self.user,
                                        overrides = self.event,
                                        except_date = dt.date(2019,1,21))
        Form = get_form_for_model(CancellationPage, form_class=CancellationPageForm)
        form = Form(instance=cancellation, parent_page=self.event)
        widget = form['except_date'].field.widget
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = panel.bind_to(instance=cancellation)
        panel = panel.bind_to(request=self._getRequest())
        panel = panel.bind_to(form=form)
        self.assertIs(widget.overrides_repeat, self.event.repeat)
        self.assertIsNone(panel.exceptionTZ)

    @timezone.override("America/Los_Angeles")
    def testBindExceptionTZ(self):
        cancellation = CancellationPage(owner = self.user,
                                        overrides = self.event,
                                        except_date = dt.date(2019,1,21))
        Form = get_form_for_model(CancellationPage, form_class=CancellationPageForm)
        form = Form(instance=cancellation, parent_page=self.event)
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = panel.bind_to(instance=cancellation)
        panel = panel.bind_to(request=self._getRequest())
        panel = panel.bind_to(form=form)
        self.assertEquals(panel.exceptionTZ, "Asia/Tokyo")

# ------------------------------------------------------------------------------
@override_settings(JOYOUS_TIME_INPUT=12)
class TestTime12hrPanel(TestCase):
    def setUp(self):
        importlib.reload(ls.joyous.edit_handlers)

    def testWidget(self):
        from ls.joyous.edit_handlers import TimePanel
        self.assertIs(TimePanel.widget, Time12hrInput)
        
    def testDefaultTimeInput(self):
        self.assertIn('%I:%M%p', settings.TIME_INPUT_FORMATS)
        self.assertIn('%I%p', settings.TIME_INPUT_FORMATS)

    def testNZLocaleTimeInput(self):
        format = get_format_modules("en-nz")
        self.assertIn('%I:%M%p', format[0].TIME_INPUT_FORMATS)
        self.assertIn('%I%p', format[0].TIME_INPUT_FORMATS)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
