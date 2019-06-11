# ------------------------------------------------------------------------------
# Test Edit Handlers
# ------------------------------------------------------------------------------
import sys
import datetime as dt

from django.test import RequestFactory, TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from wagtail.admin.edit_handlers import get_form_for_model
from wagtail.core.models import Site, Page
from ls.joyous.models.events import CancellationPageForm
from ls.joyous.models import CalendarPage, CancellationPage, RecurringEventPage
from ls.joyous.utils.recurrence import Recurrence, MONTHLY, TU
from ls.joyous.edit_handlers import ExceptionDatePanel, TimePanel, ConcealedPanel
from .testutils import datetimetz, freeze_timetz, getPage

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
class TestTime12hrPanel(TestCase):
    def setUp(self):
        self.newTime = AdminTimeInput().attrs.get('autocomplete', "new-time")

#     def testNullValue(self):
#         widget = Time12hrInput()
#         self.assertEqual(widget.value_from_datadict({}, {}, 'time'), None)
#
#     def testRenderNone(self):
#         widget = Time12hrInput()
#         out = widget.render('time', None, {'id': "time_id"})
#         self.assertHTMLEqual(out, """
# <input type="text" name="time" id="time_id" autocomplete="{0.newTime}">
# <script>
# $(function() {{
#     initTime12hrChooser("time_id");
# }});
# </script>""".format(self))


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
