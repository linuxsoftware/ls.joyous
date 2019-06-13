# ------------------------------------------------------------------------------
# Test Edit Handlers
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from unittest import skipIf, skipUnless
from django.test import RequestFactory, TestCase, override_settings
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.formats import get_format
from wagtail.admin.edit_handlers import get_form_for_model
from wagtail.admin.widgets import AdminTimeInput, AdminDateInput
from wagtail.core.models import Site, Page
from ls.joyous.models.events import CancellationPageForm, RecurringEventPageForm
from ls.joyous.models import CalendarPage, CancellationPage, RecurringEventPage
from ls.joyous.utils.recurrence import Recurrence, MONTHLY, TU
from ls.joyous.edit_handlers import ExceptionDatePanel, ConcealedPanel
from ls.joyous.widgets import Time12hrInput, ExceptionDateInput
from .testutils import datetimetz, freeze_timetz, getPage
import ls.joyous.edit_handlers
import importlib
from wagtail import VERSION as _wt_version
WagtailVersion = _wt_version[:3]

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

    @skipUnless(WagtailVersion < (2, 5, 0), "Wagtail >=2.5")
    def testBindWithoutOverrides23(self):
        cancellation = CancellationPage(owner = self.user,
                                        except_date = dt.date(2019,1,21))
        Form = get_form_for_model(CancellationPage, form_class=CancellationPageForm)
        form = Form(instance=cancellation, parent_page=self.event)
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = panel.bind_to_model(CancellationPage)
        panel = panel.bind_to_instance(instance=cancellation,
                                       form=form,
                                       request=self._getRequest())
        self.assertIsNotNone(panel.form)
        self.assertIsNone(panel.instance.overrides)

    @skipUnless(WagtailVersion < (2, 5, 0), "Wagtail >=2.5")
    def testBindOverridesRepeat23(self):
        cancellation = CancellationPage(owner = self.user,
                                        overrides = self.event,
                                        except_date = dt.date(2019,1,21))
        Form = get_form_for_model(CancellationPage, form_class=CancellationPageForm)
        form = Form(instance=cancellation, parent_page=self.event)
        widget = form['except_date'].field.widget
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = panel.bind_to_model(CancellationPage)
        panel = panel.bind_to_instance(instance=cancellation,
                                       form=form,
                                       request=self._getRequest())
        self.assertIs(widget.overrides_repeat, self.event.repeat)
        self.assertIsNone(panel.exceptionTZ)

    @skipUnless(WagtailVersion < (2, 5, 0), "Wagtail >=2.5")
    @timezone.override("America/Los_Angeles")
    def testBindExceptionTZ23(self):
        cancellation = CancellationPage(owner = self.user,
                                        overrides = self.event,
                                        except_date = dt.date(2019,1,21))
        Form = get_form_for_model(CancellationPage, form_class=CancellationPageForm)
        form = Form(instance=cancellation, parent_page=self.event)
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = panel.bind_to_model(CancellationPage)
        panel = panel.bind_to_instance(instance=cancellation,
                                       form=form,
                                       request=self._getRequest())
        self.assertEquals(panel.exceptionTZ, "Asia/Tokyo")

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testBindWithoutForm25(self):
        cancellation = CancellationPage(owner = self.user,
                                        except_date = dt.date(2019,1,21))
        panel = ExceptionDatePanel('except_date', classname='full-width')
        panel = panel.bind_to(instance=cancellation)
        self.assertIsNone(panel.form)

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testBindWithoutOverrides25(self):
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

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testBindOverridesRepeat25(self):
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

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    @timezone.override("America/Los_Angeles")
    def testBindExceptionTZ25(self):
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
    def testWidget(self):
        importlib.reload(ls.joyous.edit_handlers)
        from ls.joyous.edit_handlers import TimePanel
        self.assertIs(TimePanel.widget, Time12hrInput)

    def testDefaultTimeInput(self):
        importlib.reload(ls.joyous.edit_handlers)
        self.assertIn('%I:%M%p', settings.TIME_INPUT_FORMATS)
        self.assertIn('%I%p', settings.TIME_INPUT_FORMATS)

    @override_settings(LANGUAGE_CODE="en-nz")
    def testNZLocaleTimeInput(self):
        importlib.reload(ls.joyous.edit_handlers)
        format = get_format('TIME_INPUT_FORMATS')
        self.assertIn('%I:%M%p', format)
        self.assertIn('%I%p', format)


# ------------------------------------------------------------------------------
class TestConcealedPanel(TestCase):
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

    def testInit(self):
        panel = ConcealedPanel([], "Test", help_text="Nothing")
        self.assertEqual(panel._heading, "Test")
        self.assertEqual(panel._help_text, "Nothing")
        self.assertEqual(panel.heading, "")
        self.assertEqual(panel.help_text, "")

    @skipUnless(WagtailVersion < (2, 5, 0), "Wagtail >=2.5")
    def testConcealed23(self):
        Form = get_form_for_model(RecurringEventPage,
                                  form_class=RecurringEventPageForm)
        form = Form(instance=self.event, parent_page=self.calendar)
        panel = ConcealedPanel([], "Test")
        panel = panel.bind_to_model(RecurringEventPage)
        panel = panel.bind_to_instance(instance=self.event,
                                       form=form,
                                       request=self._getRequest())
        content = panel.render()
        self.assertEqual(content, "")
        self.assertEqual(panel.heading, "")
        self.assertEqual(panel.help_text, "")

    @skipUnless(WagtailVersion < (2, 5, 0), "Wagtail >=2.5")
    def testShown23(self):
        class ShownPanel(ConcealedPanel):
            def _show(self):
                return True

        Form = get_form_for_model(RecurringEventPage,
                                  form_class=RecurringEventPageForm)
        form = Form(instance=self.event, parent_page=self.calendar)
        panel = ShownPanel([], "Test", help_text="Nothing")
        panel = panel.bind_to_model(RecurringEventPage)
        panel = panel.bind_to_instance(instance=self.event,
                                       form=form,
                                       request=self._getRequest())
        content = panel.render()
        self.assertHTMLEqual(content, """
<fieldset>
    <legend>Test</legend>
    <ul class="fields">
    </ul>
</fieldset>
""")
        self.assertEqual(panel.heading, "Test")
        self.assertEqual(panel.help_text, "Nothing")

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testConcealed25(self):
        panel = ConcealedPanel([], "Test")
        panel = panel.bind_to(instance=self.event)
        panel = panel.bind_to(request=self._getRequest())
        content = panel.render()
        self.assertEqual(content, "")
        self.assertEqual(panel.heading, "")
        self.assertEqual(panel.help_text, "")

    @skipUnless(WagtailVersion >= (2, 5, 0), "Wagtail <2.5")
    def testShown25(self):
        class ShownPanel(ConcealedPanel):
            def _show(self):
                return True

        panel = ShownPanel([], "Test", help_text="Nothing")
        panel = panel.bind_to(instance=self.event)
        self.assertEqual(panel.heading, "")
        self.assertEqual(panel.help_text, "")
        panel = panel.bind_to(request=self._getRequest())
        content = panel.render()
        self.assertHTMLEqual(content, """
<fieldset>
    <legend>Test</legend>
    <ul class="fields">
    </ul>
</fieldset>
""")
        self.assertEqual(panel.heading, "Test")
        self.assertEqual(panel.help_text, "Nothing")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
