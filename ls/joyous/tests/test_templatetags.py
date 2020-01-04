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
from ls.joyous.utils.recurrence import (DAILY, WEEKLY, MONTHLY, YEARLY,
                                        MO, TU, WE, TH, FR, SA)
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
        self._setUpVeterisSubsite()

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
                                   time_from = dt.time(17),
                                   location = "Community Centre, Backstage")
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

    def _setUpVeterisSubsite(self):
        main = getPage("/home/")
        home = Page(slug="veteris", title="Veteris Council")
        main.add_child(instance=home)
        home.save_revision().publish()
        activities = Page(slug="activities", title="Veteris Calendar")
        home.add_child(instance=activities)
        activities.save_revision().publish()
        Site.objects.create(hostname='veteris.joy.test',
                            root_page_id=home.id,
                            is_default_site=False)
        events = CalendarPage(owner = self.user,
                              slug  = "veteris-events",
                              title = "Veteris Events")
        home.add_child(instance=events)
        events.save_revision().publish()
        committee = RecurringEventPage(owner = self.user,
                                       slug  = "veteris-committee",
                                       title = "Committee Meeting",
                                       repeat = Recurrence(dtstart=dt.date(1970,1,5),
                                                           freq=MONTHLY,
                                                           byweekday=[MO],
                                                           until=dt.date(1978,8,7)),
                                       time_from = dt.time(14),
                                       time_to   = dt.time(15))
        events.add_child(instance=committee)
        committee.save_revision().publish()

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
  <div class="joy-this-week">
    <h2 class="joy-this-week__title">This Week</h2>
    <div class="joy-this-week__events">
      <div class="joy-this-week__day joy-this-week__day--in-past">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Monday</h4>
            <div class="joy-this-week__date">10th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/chess-club/lunchtime-matches/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">12pm</span><span class="joy-days-events__event-text">Lunchtime Chess Matches</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day joy-this-week__day--today">
        <div class="joy-this-week__day-title" title=Today>
            <h4  class="joy-this-week__weekday">Tuesday</h4>
            <div class="joy-this-week__date">11th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Wednesday</h4>
            <div class="joy-this-week__date">12th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/chess-club/lunchtime-matches/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">12pm</span><span class="joy-days-events__event-text">Lunchtime Chess Matches</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Thursday</h4>
            <div class="joy-this-week__date">13th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/nova/nova-events/rubbish-blitz/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">12:30pm</span><span class="joy-days-events__event-text">Rubbish Blitz</span>
          </a>
          <a href="/nova/nova-events/executive-meeting/1984-09-13-cancellation/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">1pm</span><span class="joy-days-events__event-text">Meeting Cancelled</span>
          </a>
          <a href="/events/drama-practice/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">5pm</span><span class="joy-days-events__event-text">Drama Group</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Friday</h4>
            <div class="joy-this-week__date">14th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/chess-club/lunchtime-matches/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">12pm</span><span class="joy-days-events__event-text">Lunchtime Chess Matches</span>
          </a>
          <a href="/events/public-lecture3/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">7pm</span><span class="joy-days-events__event-text">The Human Environment</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Saturday</h4>
            <div class="joy-this-week__date">15th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/events/flea-market/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">8am</span><span class="joy-days-events__event-text">Flea Market</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Sunday</h4>
            <div class="joy-this-week__date">16th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
        </div>
      </div>
    </div>
    <div class="joy-this-week__cal">
      <a class="joy-this-week__cal-link" href="/events/">Events</a>
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
  <div class="joy-this-week">
    <h2 class="joy-this-week__title">This Week</h2>
    <div class="joy-this-week__events">
      <div class="joy-this-week__day joy-this-week__day--in-past">
        <div class="joy-this-week__day-title" >
          <h4  class="joy-this-week__weekday">Monday</h4>
          <div class="joy-this-week__date">17th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
      <div class="joy-this-week__day joy-this-week__day--in-past">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Tuesday</h4>
            <div class="joy-this-week__date">18th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
      <div class="joy-this-week__day joy-this-week__day--in-past">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Wednesday</h4>
            <div class="joy-this-week__date">19th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
      <div class="joy-this-week__day joy-this-week__day--today">
        <div class="joy-this-week__day-title" title=Today>
            <h4  class="joy-this-week__weekday">Thursday</h4>
            <div class="joy-this-week__date">20th Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/nova-events/executive-meeting/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">1pm</span><span class="joy-days-events__event-text">Executive Committee Meeting</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Friday</h4>
            <div class="joy-this-week__date">21st Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Saturday</h4>
            <div class="joy-this-week__date">22nd Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Sunday</h4>
            <div class="joy-this-week__date">23rd Sep</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
    </div>
    <div class="joy-this-week__cal">
      <a class="joy-this-week__cal-link" href="/nova-events/">Nova Events</a>
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
        self.assertEqual(len(select(".joy-minical__weekday--sun")), 1)
        month = select(".joy-minical__month-name")[0]
        self.assertEqual(month.string.strip(), "October")
        year = select(".joy-minical__year-number")[0]
        self.assertEqual(year.string.strip(), "1984")
        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.joy-minical__day")), 31)
        self.assertEqual(len(select("tbody td.joy-minical__no-day")), 4)
        self.assertEqual(len(select('tbody td.joy-minical__day a[title="Lunchtime Chess Matches"]')), 12)
        links = select('tbody td.joy-minical__day a')
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
        items = soup(class_="joy-ev-item")
        self.assertEqual(len(items), 9)
        chess, novaexec, blitz, cancel, drama, lecture, market, nochess, chess2 = items
        self.assertEqual(chess.a['href'], "/chess-club/lunchtime-matches/")
        self.assertEqual(novaexec.find(class_="joy-ev-next-on").get_text(strip=True),
                         "Next on Thursday 6th of September at 1pm")
        self.assertEqual(blitz.a['href'], "/nova/nova-events/rubbish-blitz/")
        self.assertEqual(blitz.a.get_text(strip=True), "Rubbish Blitz")
        self.assertEqual(blitz.find(class_="joy-ev-when").get_text(strip=True),
                         "Thursday 13th of September at 12:30pm to 5pm")
        self.assertEqual(drama.find(class_="joy-ev-when").get_text(strip=True),
                         "Fortnightly on Thursdays at 5pm")
        self.assertEqual(drama.find(class_="joy-ev-next-on").get_text(strip=True),
                         "Next on Thursday 13th of September at 5pm")
        self.assertEqual(lecture.find(class_="joy-ev-when").get_text(strip=True),
                         "Friday 14th of September at 7pm")
        self.assertEqual(lecture.find(class_="joy-ev-where").get_text(strip=True),
                         "Lecture Hall C[map]")
        self.assertEqual(market.a['href'], "/events/flea-market/")
        self.assertEqual(market.a.get_text(strip=True), "Flea Market")
        self.assertEqual(chess2.a['href'], "/chess-club/lunchtime-matches/1984-10-03-postponement/")
        self.assertEqual(chess2.find(class_="joy-ev-from-when").get_text(strip=True),
                         "Postponed from Wednesday 3rd of October at 12pm to 1pm")
        self.assertEqual(cancel.a.get_text(strip=True), "Meeting Cancelled")
        self.assertEqual(nochess.a.get_text(strip=True), "No Chess Club Today")

    @freeze_timetz("1984-09-01 15:00")
    def testSubsiteUpcomingEvents(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% subsite_upcoming_events %}"
        ).render(self._getContext(hostname="nova.joy.test",
                                  page=getPage("/home/nova/activities/")))
        soup = BeautifulSoup(out, "html5lib")
        items = soup(class_="joy-ev-item")
        self.assertEqual(len(items), 3)
        novaexec, blitz, cancel = items
        self.assertEqual(novaexec.a.get_text(strip=True),
                         "Executive Committee Meeting")
        self.assertEqual(blitz.a.get_text(strip=True), "Rubbish Blitz")
        self.assertEqual(cancel.a.get_text(strip=True), "Meeting Cancelled")

    @freeze_timetz("1984-09-15 10:00")
    def testGroupUpcomingEvents(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% group_upcoming_events %}"
        ).render(self._getContext(page=getPage("/home/chess-club/")))
        self.assertHTMLEqual(out, """
    <div class="joy-title joy-title--list">
      <h2>Events</h2>
    </div>
    <div class="joy-grp-list">
      <div class="joy-ev-item">
        <div class="joy-title joy-title--item">
          <h3><a class="joy-title__link" href="/chess-club/lunchtime-matches/">Lunchtime Chess Matches</a></h3>
        </div>
        <div class="joy-ev-when joy-field">
          Mondays, Wednesdays and Fridays at 12pm to 1pm
        </div>
        <div class="joy-ev-next-on joy-field">
          Next on Monday 17th of September at 12pm
        </div>
      </div>
      <div class="joy-ev-item">
        <div class="joy-title joy-title--item">
          <h3><a class="joy-title__link" href="/chess-club/lunchtime-matches/1984-10-01-cancellation/">No Chess Club Today</a></h3>
        </div>
        <div class="joy-ev-when joy-field">
          Monday 1st of October at 12pm to 1pm
        </div>
      </div>
      <div class="joy-ev-item">
        <div class="joy-title joy-title--item">
          <h3><a class="joy-title__link" href="/chess-club/lunchtime-matches/1984-10-03-postponement/">Early Morning Matches</a></h3>
        </div>
        <div class="joy-ev-when joy-field">
          Thursday 4th of October at 7:30am to 8:30am
        </div>
        <div class="joy-ev-from-when joy-field">
          Postponed from Wednesday 3rd of October at 12pm to 1pm
        </div>
      </div>
    </div>
""")

    def testGroupUpcomingEventsNotGroup(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% group_upcoming_events %}"
        ).render(self._getContext(page=getPage("/home/")))
        self.assertHTMLEqual(out, "")

    def testGroupUpcomingEventsNoPage(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% group_upcoming_events %}"
        ).render(self._getContext(page=None))
        self.assertHTMLEqual(out, "")

    @freeze_timetz("1984-08-04 10:00")
    def testFutureExceptionsImplicitPage(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% future_exceptions %}"
        ).render(self._getContext(hostname="nova.joy.test",
                                  page=getPage("/home/nova/nova-events/executive-meeting/")))
        soup = BeautifulSoup(out, "html5lib")
        items = soup(class_="joy-ev-related__item")
        self.assertEqual(len(items), 1)
        cancellation = items[0]
        self.assertEqual(cancellation.a['href'],
                         "/nova-events/executive-meeting/1984-09-13-cancellation/")
        self.assertEqual(cancellation.find(class_="joy-field").get_text(strip=True),
                         "Meeting Cancelled")

    @freeze_timetz("1984-09-15 13:00")
    def testFutureExceptionsExplicitPage(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% future_exceptions kasparov %}"
        ).render(self._getContext(kasparov=getPage("/home/chess-club/lunchtime-matches/")))
        soup = BeautifulSoup(out, "html5lib")
        items = soup(class_="joy-ev-related__item")
        self.assertEqual(len(items), 2)
        cancellation, postponement = items
        self.assertEqual(cancellation.a['href'],
                         "/chess-club/lunchtime-matches/1984-10-01-cancellation/")
        self.assertEqual(cancellation.find(class_="joy-field").get_text(strip=True),
                         "No Chess Club Today")
        self.assertEqual(postponement.a['href'],
                         "/chess-club/lunchtime-matches/1984-10-03-postponement/")
        self.assertEqual(postponement.find(class_="joy-field").get_text(strip=True),
                         "Early Morning Matches on Thursday 4th of October")

    def testFutureExceptionsNotRrevent(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% future_exceptions %}"
        ).render(self._getContext(page=getPage("/home/chess-club/")))
        self.assertHTMLEqual(out, "")

    def testFutureExceptionsNoPage(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% future_exceptions %}"
        ).render(self._getContext(page=None))
        self.assertHTMLEqual(out, "")

    @freeze_timetz("1984-10-10 10:00")
    def testNextOn(self):
        out = Template(
            "{% load joyous_tags %}"
            "{% next_on %}"
        ).render(self._getContext(hostname="nova.joy.test",
                                  page=getPage("/home/nova/nova-events/executive-meeting/")))
        self.assertEqual(out, "Thursday 11th of October at 1pm")

    def testLocationGMap(self):
        page = getPage("/home/events/drama-practice/")
        out = Template(
            "{% load joyous_tags %}"
            "{% location_gmap location %}"
        ).render(self._getContext(page=page,
                                  location=page.location))
        self.assertHTMLEqual(out, """
<a class="joy-ev-where__map-link" target="_blank"
   href="http://maps.google.com/?q=Community Centre, Backstage">[map]</a>
""")
    def testTimeDisplay(self):
        out = Template(
            "{% load joyous_tags %}"
            "{{ alarm | time_display }}"
        ).render(self._getContext(alarm=dt.time(6,55)))
        self.assertEqual(out, "6:55am")

    def testAtTimeDisplay(self):
        out = Template(
            "{% load joyous_tags %}"
            "{{ meeting | at_time_display }}"
        ).render(self._getContext(meeting=dt.time(8,30)))
        self.assertEqual(out, "at 8:30am")

    def testDateDisplay(self):
        out = Template(
            "{% load joyous_tags %}"
            "{{ day | date_display }}"
        ).render(self._getContext(day=dt.date(2008,3,10)))
        self.assertEqual(out, "Monday 10th of March 2008")

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
  <div class="joy-this-week">
    <h2 class="joy-this-week__title">This Week</h2>
    <div class="joy-this-week__events">
      <div class="joy-this-week__day joy-this-week__day--today">
        <div class="joy-this-week__day-title" title=Today>
          <h4  class="joy-this-week__weekday">Sunday</h4>
          <div class="joy-this-week__date">16th Aug</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
          <h4  class="joy-this-week__weekday">Monday</h4>
          <div class="joy-this-week__date">17th Aug</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/chess-club/lunchtime-matches/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">12pm</span><span class="joy-days-events__event-text">Lunchtime Chess Matches</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
          <h4  class="joy-this-week__weekday">Tuesday</h4>
          <div class="joy-this-week__date">18th Aug</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Wednesday</h4>
            <div class="joy-this-week__date">19th Aug</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/chess-club/lunchtime-matches/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">12pm</span><span class="joy-days-events__event-text">Lunchtime Chess Matches</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Thursday</h4>
            <div class="joy-this-week__date">20th Aug</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Friday</h4>
            <div class="joy-this-week__date">21st Aug</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events">
          <a href="/chess-club/lunchtime-matches/" class="joy-days-events__event">
            <span class="joy-days-events__event-time">12pm</span><span class="joy-days-events__event-text">Lunchtime Chess Matches</span>
          </a>
        </div>
      </div>
      <div class="joy-this-week__day">
        <div class="joy-this-week__day-title" >
            <h4  class="joy-this-week__weekday">Saturday</h4>
            <div class="joy-this-week__date">22nd Aug</div>
        </div>
        <div class="joy-this-week__days-events joy-days-events"></div>
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
        self.assertEqual(len(select(".joy-minical__weekday--sun")), 1)
        month = select(".joy-minical__month-name")[0]
        self.assertEqual(month.string.strip(), "October")
        year = select(".joy-minical__year-number")[0]
        self.assertEqual(year.string.strip(), "1984")
        self.assertEqual(len(select("tbody tr")), 5)
        self.assertEqual(len(select("tbody td")), 35)
        self.assertEqual(len(select("tbody td.joy-minical__day")), 31)
        self.assertEqual(len(select(".joy-minical__no-day")), 4)
        self.assertEqual(len(select('.joy-minical__date--event')), 14)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
