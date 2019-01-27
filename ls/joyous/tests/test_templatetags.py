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
from ls.joyous.models import (CalendarPage, SimpleEventPage, RecurringEventPage,
                              CancellationPage, PostponementPage, GroupPage)
from .testutils import datetimetz, freeze_timetz
from .testutils import getPage

# ------------------------------------------------------------------------------
class TestMultiSite(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.requestFactory = RequestFactory()
        self._setUpMainSite()
        self._setUpNovaSubsite()

    def _setUpMainSite(self):
        Site.objects.filter(is_default_site=True).update(hostname="joy.test")
        home = getPage("/home/")
        events = CalendarPage(owner = self.user,
                              slug  = "events",
                              title = "Events")
        home.add_child(instance=events)
        events.save_revision().publish()
        chess = GroupPage(slug="chess-club", title="Chess Club")
        home.add_child(instance=chess)
        chess.save_revision().publish()
        event = RecurringEventPage(owner = self.user,
                                   slug  = "lunchtime-matches",
                                   title = "Lunchtime Chess Matches",
                                   repeat = Recurrence(dtstart=dt.date(1984,8,5),
                                                       freq=WEEKLY,
                                                       byweekday=[MO,WE,FR]),
                                   time_from = dt.time(12),
                                   time_to   = dt.time(13))
        chess.add_child(instance=event)
        event.save_revision().publish()
        cancellation = CancellationPage(owner = self.user,
                                        slug  = "1984-10-01-cancellation",
                                        title = "Cancellation for Monday 1st of October",
                                        overrides = event,
                                        except_date = dt.date(1984, 10, 1),
                                        cancellation_title   = "No Chess Club Today")
        event.add_child(instance=cancellation)
        cancellation.save_revision().publish()
        postponement = PostponementPage(owner = self.user,
                                        slug  = "1984-10-03-postponement",
                                        title = "Postponement for Wednesday 3rd of October",
                                        overrides = event,
                                        except_date = dt.date(1984, 10, 3),
                                        cancellation_title   = "",
                                        postponement_title   = "Early Morning Matches",
                                        date      = dt.date(1984,10,4),
                                        time_from = dt.time(7,30),
                                        time_to   = dt.time(8,30))
        event.add_child(instance=postponement)
        postponement.save_revision().publish()
        event = RecurringEventPage(owner = self.user,
                                   slug  = "flea-market",
                                   title = "Flea Market",
                                   repeat = Recurrence(dtstart=dt.date(1984,7,1),
                                                       freq=YEARLY,
                                                       byweekday=[SA(1), SA(3)],
                                                       bymonth=range(2,12)),
                                   time_from = dt.time(8),
                                   time_to   = dt.time(13))
        events.add_child(instance=event)
        event.save_revision().publish()
        event = RecurringEventPage(owner = self.user,
                                   slug  = "drama-practice",
                                   title = "Drama Group",
                                   repeat = Recurrence(dtstart=dt.date(1984,8,14),
                                                       freq=WEEKLY,
                                                       byweekday=[TH],
                                                       interval=2),
                                   time_from = dt.time(17))
        events.add_child(instance=event)
        event.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "public-lecture3",
                                title = "The Human Environment",
                                date  = dt.date(1984,9,14),
                                time_from = dt.time(19),
                                location = "Lecture Hall C")
        events.add_child(instance=event)
        event.save_revision().publish()

    def _setUpNovaSubsite(self):
        main = getPage("/home/")
        home = Page(slug="nova", title="Nova Homepage")
        main.add_child(instance=home)
        home.save_revision().publish()
        activities = Page(slug="activities", title="Nova Activities")
        home.add_child(instance=activities)
        activities.save_revision().publish()
        Site.objects.create(hostname='nova.joy.test',
                            root_page_id=home.id,
                            is_default_site=False)
        events = CalendarPage(owner = self.user,
                              slug  = "nova-events",
                              title = "Nova Events")
        home.add_child(instance=events)
        events.save_revision().publish()
        committee = RecurringEventPage(owner = self.user,
                                       slug  = "executive-meeting",
                                       title = "Executive Committee Meeting",
                                       repeat = Recurrence(dtstart=dt.date(1984,8,5),
                                                           freq=WEEKLY,
                                                           byweekday=[TH]),
                                       time_from = dt.time(13),
                                       time_to   = dt.time(15))
        events.add_child(instance=committee)
        committee.save_revision().publish()
        event = SimpleEventPage(owner = self.user,
                                slug  = "rubbish-blitz",
                                title = "Rubbish Blitz",
                                date  = dt.date(1984, 9, 13),
                                time_from = dt.time(12,30),
                                time_to   = dt.time(17))
        events.add_child(instance=event)
        event.save_revision().publish()
        cancellation = CancellationPage(owner = self.user,
                                        slug  = "1984-09-13-cancellation",
                                        title = "Cancellation for Thursday 13th of September",
                                        overrides = committee,
                                        except_date = dt.date(1984, 9, 13),
                                        cancellation_title   = "Meeting Cancelled",
                                        cancellation_details = "The committee will be at "
                                                               "the working bee")
        committee.add_child(instance=cancellation)
        cancellation.save_revision().publish()

    def _getContext(self, hostname=None, slug="", **kwargs):
        if hostname is None:
            hostname = "joy.test"
        site = Site.objects.get(hostname=hostname)
        vars = {'request': self._getRequest(site, slug),
                'page':    getPage("/home/")}
        vars.update(kwargs)
        context = Context(vars)
        return context

    def _getRequest(self, site, slug=""):
        path = "test/{}/{}".format(site.root_page.slug, slug)
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = site
        request.session = {}
        return request

    @freeze_timetz("1984-09-11 10:00")
    def testEventsThisWeek(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% events_this_week %}"
        ).render(self._getContext())
        self.assertHTMLEqual(out, """
<div class="events-this-week">
  <h3>This Week</h3>
  <div class="events">
      <div class="day in-past">
        <div class="event-day">
            <h4>Monday</h4> 10th Sep
        </div>
        <div class="days-events">
            <a href="/chess-club/lunchtime-matches/" class="event">
              12pm Lunchtime Chess Matches
            </a>
        </div>
      </div>
      <div class="day today">
        <div class="event-day" title="Today">
            <h4>Tuesday</h4> 11th Sep
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day">
        <div class="event-day">
            <h4>Wednesday</h4> 12th Sep
        </div>
        <div class="days-events">
            <a href="/chess-club/lunchtime-matches/" class="event">
              12pm Lunchtime Chess Matches
            </a>
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Thursday</h4> 13th Sep
        </div>
        <div class="days-events">
            <a href="/nova/nova-events/rubbish-blitz/" class="event">
              12:30pm Rubbish Blitz
            </a>
            <a href="/nova/nova-events/executive-meeting/1984-09-13-cancellation/" class="event">
              1pm Meeting Cancelled
            </a>
            <a href="/events/drama-practice/" class="event">
              5pm Drama Group
            </a>
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Friday</h4> 14th Sep
        </div>
        <div class="days-events">
            <a href="/chess-club/lunchtime-matches/" class="event">
              12pm Lunchtime Chess Matches
            </a>
            <a href="/events/public-lecture3/" class="event">
              7pm The Human Environment
            </a>
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Saturday</h4> 15th Sep
        </div>
        <div class="days-events">
            <a href="/events/flea-market/" class="event">
              8am Flea Market
            </a>
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Sunday</h4> 16th Sep
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

    @freeze_timetz("1984-09-20 09:00")
    def testSubsiteEventsThisWeek(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% events_this_week %}"
        ).render(self._getContext(hostname="nova.joy.test",
                                  page=getPage("/home/nova/activities/")))
        self.assertHTMLEqual(out, """
<div class="events-this-week">
  <h3>This Week</h3>
  <div class="events">
      <div class="day in-past">
        <div class="event-day">
            <h4>Monday</h4> 17th Sep
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day in-past">
        <div class="event-day">
            <h4>Tuesday</h4> 18th Sep
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day in-past">
        <div class="event-day">
            <h4>Wednesday</h4> 19th Sep
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day today">
        <div class="event-day" title="Today">
            <h4>Thursday</h4> 20th Sep
        </div>
        <div class="days-events">
            <a href="/nova-events/executive-meeting/" class="event">
              1pm Executive Committee Meeting
            </a>
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Friday</h4> 21st Sep
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Saturday</h4> 22nd Sep
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Sunday</h4> 23rd Sep
        </div>
        <div class="days-events">
        </div>
      </div>
  </div>
  <div class="calendar-link">
    <a href="/nova-events/">Nova Events</a>
  </div>
</div>
""")

    @freeze_timetz("1984-10-24 10:00")
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
        self.assertEqual(year.string.strip(), "1984")
        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.day")), 31)
        self.assertEqual(len(select("tbody td.noday")), 4)
        self.assertEqual(len(select('tbody td.day a[title="Lunchtime Chess Matches"]')), 12)
        links = select('tbody td.day a')
        self.assertEqual(len(links), 19)
        self.assertEqual(links[0].get_text(), "1")
        self.assertEqual(links[0]['href'], "/events/1984/10/01/")
        self.assertEqual(links[0]['title'], "No Chess Club Today")
        self.assertEqual(links[1].get_text(), "4")
        self.assertEqual(links[1]['href'], "/events/1984/10/04/")
        self.assertEqual(links[1]['title'], "Early Morning Matches, Executive Committee Meeting")
        self.assertEqual(links[3].get_text(), "6")
        self.assertEqual(links[3]['href'], "/events/1984/10/06/")
        self.assertEqual(links[3]['title'], "Flea Market")
        self.assertEqual(links[15].get_text(), "25")
        self.assertEqual(links[15]['href'], "/events/1984/10/25/")
        self.assertEqual(links[15]['title'], "Executive Committee Meeting, Drama Group")

    @freeze_timetz("1984-09-05 10:00")
    def testAllUpcomingEvents(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% all_upcoming_events %}"
        ).render(self._getContext())
        soup = BeautifulSoup(out, "html5lib")
        items = soup(class_="event-item")
        self.assertEqual(len(items), 7)
        chess, novaexec, blitz, drama, lecture, market, chess2 = items
        self.assertEqual(chess.a['href'], "/chess-club/lunchtime-matches/")
        self.assertEqual(novaexec.find(class_="event-next-on").get_text(strip=True),
                         "Next on Thursday 6th of September at 1pm")
        self.assertEqual(blitz.a['href'], "/nova/nova-events/rubbish-blitz/")
        self.assertEqual(blitz.a.get_text(strip=True), "Rubbish Blitz")
        self.assertEqual(blitz.find(class_="event-when").get_text(strip=True),
                         "Thursday 13th of September at 12:30pm to 5pm")
        self.assertEqual(drama.find(class_="event-when").get_text(strip=True),
                         "Fortnightly on Thursdays at 5pm")
        self.assertEqual(drama.find(class_="event-next-on").get_text(strip=True),
                         "Next on Thursday 13th of September at 5pm")
        self.assertEqual(lecture.find(class_="event-when").get_text(strip=True),
                         "Friday 14th of September at 7pm")
        self.assertEqual(lecture.find(class_="event-location").get_text(strip=True),
                         "Lecture Hall C")
        self.assertEqual(market.a['href'], "/events/flea-market/")
        self.assertEqual(market.a.get_text(strip=True), "Flea Market")
        self.assertEqual(chess2.a['href'], "/chess-club/lunchtime-matches/1984-10-03-postponement/")
        self.assertEqual(chess2.find(class_="event-postponed-from").get_text(strip=True),
                         "Postponed from Wednesday 3rd of October at 12pm to 1pm")

    @freeze_timetz("1984-09-01 15:00")
    def testSubsiteUpcomingEvents(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% subsite_upcoming_events %}"
        ).render(self._getContext(hostname="nova.joy.test",
                                  page=getPage("/home/nova/activities/")))
        soup = BeautifulSoup(out, "html5lib")
        items = soup(class_="event-item")
        self.assertEqual(len(items), 2)
        novaexec, blitz = items
        self.assertEqual(novaexec.a.get_text(strip=True),
                         "Executive Committee Meeting")
        self.assertEqual(blitz.a.get_text(strip=True), "Rubbish Blitz")

    @freeze_timetz("1984-09-15 10:00")
    def testGroupUpcomingEvents(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% group_upcoming_events %}"
        ).render(self._getContext(page=getPage("/home/chess-club/")))
        self.assertHTMLEqual(out, """
<h3>Events</h3>
<div class="upcoming-events">
  <div class="event-item clearfix">
    <div class="event-item-title">
      <a href="/chess-club/lunchtime-matches/">Lunchtime Chess Matches</a>
    </div>
    <div class="event-when">
      Mondays, Wednesdays and Fridays at 12pm to 1pm
    </div>
    <div class="event-next-on">
      Next on Monday 17th of September at 12pm
    </div>
  </div>
  <div class="event-item clearfix">
    <div class="event-item-title">
      <a href="/chess-club/lunchtime-matches/1984-10-03-postponement/">Early Morning Matches</a>
    </div>
    <div class="event-when">
      Thursday 4th of October at 7:30am to 8:30am
    </div>
    <div class="event-postponed-from">
      Postponed from Wednesday 3rd of October at 12pm to 1pm
    </div>
  </div>
</div>""")

    @freeze_timetz("1984-08-04 10:00")
    def testFutureExceptionsImplicitPage(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% future_exceptions %}"
        ).render(self._getContext(hostname="nova.joy.test",
                                  page=getPage("/home/nova/nova-events/executive-meeting/")))
        soup = BeautifulSoup(out, "html5lib")
        items = soup(class_="item")
        self.assertEqual(len(items), 1)
        cancellation = items[0]
        self.assertEqual(cancellation['href'],
                         "/nova-events/executive-meeting/1984-09-13-cancellation/")
        self.assertEqual(cancellation.find(class_="item-text").get_text(strip=True),
                         "Meeting Cancelled")

    @freeze_timetz("1984-09-15 13:00")
    def testFutureExceptionsExplicitPage(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% future_exceptions kasparov %}"
        ).render(self._getContext(kasparov=getPage("/home/chess-club/lunchtime-matches/")))
        soup = BeautifulSoup(out, "html5lib")
        items = soup(class_="item")
        self.assertEqual(len(items), 2)
        cancellation, postponement = items
        self.assertEqual(cancellation['href'],
                         "/chess-club/lunchtime-matches/1984-10-01-cancellation/")
        self.assertEqual(cancellation.find(class_="item-text").get_text(strip=True),
                         "No Chess Club Today")
        self.assertEqual(postponement['href'],
                         "/chess-club/lunchtime-matches/1984-10-03-postponement/")
        self.assertEqual(postponement.find(class_="item-text").get_text(strip=True),
                         "Early Morning Matches on Thursday 4th of October")

# ------------------------------------------------------------------------------
class TestNoCalendar(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        home = getPage("/home/")
        chess = GroupPage(slug="chess-club", title="Chess Club")
        home.add_child(instance=chess)
        chess.save_revision().publish()
        event = RecurringEventPage(owner = self.user,
                                   slug  = "lunchtime-matches",
                                   title = "Lunchtime Chess Matches",
                                   repeat = Recurrence(dtstart=dt.date(1984,8,5),
                                                       freq=WEEKLY,
                                                       byweekday=[MO,WE,FR]),
                                   time_from = dt.time(12),
                                   time_to   = dt.time(13))
        chess.add_child(instance=event)
        event.save_revision().publish()
        self.request = RequestFactory().get("/test")
        self.request.user = self.user
        self.request.session = {}
        self.request.site = Site.objects.get(is_default_site=True)

    @freeze_timetz("1987-08-16 12:45")
    def testEventsThisWeek(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% events_this_week %}"
        ).render(Context({'request': self.request}))
        self.assertHTMLEqual(out, """
<div class="events-this-week">
  <h3>This Week</h3>
  <div class="events">
      <div class="day today">
        <div class="event-day" title="Today">
            <h4>Sunday</h4> 16th Aug
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day">
        <div class="event-day">
            <h4>Monday</h4> 17th Aug
        </div>
        <div class="days-events">
            <a href="/chess-club/lunchtime-matches/" class="event">
              12pm Lunchtime Chess Matches
            </a>
        </div>
      </div>
      <div class="day">
        <div class="event-day">
            <h4>Tuesday</h4> 18th Aug
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day">
        <div class="event-day">
            <h4>Wednesday</h4> 19th Aug
        </div>
        <div class="days-events">
            <a href="/chess-club/lunchtime-matches/" class="event">
              12pm Lunchtime Chess Matches
            </a>
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Thursday</h4> 20th Aug
        </div>
        <div class="days-events">
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Friday</h4> 21st Aug
        </div>
        <div class="days-events">
            <a href="/chess-club/lunchtime-matches/" class="event">
              12pm Lunchtime Chess Matches
            </a>
        </div>
      </div>
      <div class="day">
        <div class="event-day" >
            <h4>Saturday</h4> 22nd Aug
        </div>
        <div class="days-events">
        </div>
      </div>
  </div>
</div>
""")

    @freeze_timetz("1984-10-24 10:00")
    def testMinicalendar(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% minicalendar %}"
        ).render(Context({'request': self.request}))
        soup = BeautifulSoup(out, "html5lib")
        select = soup.select
        self.assertEqual(len(select('thead a')), 0)
        self.assertEqual(len(select("table.minicalendar thead tr th.sun")), 1)
        month = select("tr.heading th.month .month-name")[0]
        self.assertEqual(month.string.strip(), "October")
        year = select("tr.heading th.month .year-number")[0]
        self.assertEqual(year.string.strip(), "1984")
        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.day")), 31)
        self.assertEqual(len(select("tbody td.noday")), 4)
        self.assertEqual(len(select('tbody td.day span.event')), 14)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
