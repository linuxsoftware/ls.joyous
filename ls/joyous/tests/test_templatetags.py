# ------------------------------------------------------------------------------
# Test Joyous Template Tags
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.contrib.auth.models import User
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase, RequestFactory
from wagtail.core.models import Site, Page
from bs4 import BeautifulSoup
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import DAILY, WEEKLY, YEARLY, MO, TU, WE, TH, FR, SA
from ls.joyous.models.calendar import CalendarPage
from ls.joyous.models import (SimpleEventPage, MultidayEventPage,
        RecurringEventPage, CancellationPage)
from .testutils import datetimetz, freeze_timetz

class TestTemplateTags(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        #Site.objects.update(hostname="joy.test")
        self.events = {}
        self.requestFactory = RequestFactory()
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        Page.objects.get(slug='home').add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        event = RecurringEventPage(owner = self.user,
                                   slug  = "chess-club",
                                   title = "Chess Club",
                                   repeat = Recurrence(dtstart=dt.date(1972,8,5),
                                                       freq=WEEKLY,
                                                       byweekday=[MO,WE,FR]),
                                   time_from = dt.time(12),
                                   time_to   = dt.time(13))
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        self.events['chess'] = event
        event = RecurringEventPage(owner = self.user,
                                   slug  = "flea-market",
                                   title = "Flea Market",
                                   repeat = Recurrence(dtstart=dt.date(1972,7,1),
                                                       freq=YEARLY,
                                                       byweekday=[SA(1), SA(3)],
                                                       bymonth=range(2,12)),
                                   time_from = dt.time(8),
                                   time_to   = dt.time(13))
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        self.events['market'] = event
        event = RecurringEventPage(owner = self.user,
                                   slug  = "drama-group",
                                   title = "Drama Group",
                                   repeat = Recurrence(dtstart=dt.date(1972,8,14),
                                                       freq=WEEKLY,
                                                       byweekday=[TH],
                                                       interval=2),
                                   time_from = dt.time(17))
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        self.events['drama'] = event
        event = SimpleEventPage(owner = self.user,
                                slug  = "public-lecture3",
                                title = "The Human Environment",
                                date  = dt.date(1972,9,15),
                                time_from = dt.time(19))
        self.calendar.add_child(instance=event)
        event.save_revision().publish()
        self.events['lecture'] = event

    def _getContext(self):
        context = Context({'request': self._getRequest()})
        return context

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        return request

    @freeze_timetz("1972-09-11 10:00")
    def testEventsThisWeek(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% events_this_week %}"
        ).render(self._getContext())
        self.assertHTMLEqual(out, """
<div class="events-this-week">
  <h3>This Week</h3>
  <div class="events">
      <div class="day  today">
        <div class="event-day" title="Today">
            <h4>Monday</h4> 11th Sep
        </div>
        <div class="days-events">
            <a href="/events/chess-club/" class="event">
              12pm Chess Club
            </a>
        </div>
      </div>
      <div class="day ">
        <div class="event-day" >
            <h4>Tuesday</h4> 12th Sep
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day ">
        <div class="event-day" >
            <h4>Wednesday</h4> 13th Sep
        </div>
        <div class="days-events">
            <a href="/events/chess-club/" class="event">
              12pm Chess Club
            </a>
        </div>
      </div>
      <div class="day ">
        <div class="event-day" >
            <h4>Thursday</h4> 14th Sep
        </div>
        <div class="days-events">
            <a href="/events/drama-group/" class="event">
              5pm Drama Group
            </a>
        </div>
      </div>
      <div class="day ">
        <div class="event-day" >
            <h4>Friday</h4> 15th Sep
        </div>
        <div class="days-events">
            <a href="/events/chess-club/" class="event">
              12pm Chess Club
            </a>
            <a href="/events/public-lecture3/" class="event">
              7pm The Human Environment
            </a>
        </div>
      </div>
      <div class="day ">
        <div class="event-day" >
            <h4>Saturday</h4> 16th Sep
        </div>
        <div class="days-events">
            <a href="/events/flea-market/" class="event">
              8am Flea Market
            </a>
        </div>
      </div>
      <div class="day ">
        <div class="event-day" >
            <h4>Sunday</h4> 17th Sep
        </div>
        <div class="days-events">
        </div>
      </div>
  </div>
  <div class="calendar-link">
    <a href="/events/">Events</a>
  </div>
</div>
""")

    @freeze_timetz("1972-10-24 10:00")
    def testMinicalendar(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% minicalendar %}"
        ).render(self._getContext())
        soup = BeautifulSoup(out, "html5lib")
        select = soup.select
        self.assertEqual(len(select('thead a')), 2)
        self.assertEqual(len(select("table.minicalendar thead tr th.sun")), 1)

        month = select("tr.heading th.month .month-name")[0]
        self.assertEqual(month.string.strip(), "October")
        year = select("tr.heading th.month .year-number")[0]
        self.assertEqual(year.string.strip(), "1972")

        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.day")), 31)
        self.assertEqual(len(select("tbody td.noday")), 4)
        self.assertEqual(len(select('tbody td.day a[title="Chess Club"]')), 13)

