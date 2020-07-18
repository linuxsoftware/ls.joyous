# ------------------------------------------------------------------------------
# Test RSS Format
# ------------------------------------------------------------------------------
import sys
import os.path
import datetime as dt
import pytz
from io import BytesIO
from icalendar import vDatetime
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import TestCase, RequestFactory
from bs4 import BeautifulSoup
from lxml import etree
from django_bs_test import TestCase
from django.utils import timezone
from wagtail.core.models import Site, Page
from wagtail.images.models import Image
from wagtail.images.tests.utils import get_test_image_file
from ls.joyous.models import CalendarPage
from ls.joyous.models import (EventCategory, SimpleEventPage, MultidayEventPage,
        RecurringEventPage, PostponementPage, ExtraInfoPage, CancellationPage)
from ls.joyous.models import get_group_model
from ls.joyous.models import ThisEvent
from ls.joyous.utils.recurrence import Recurrence
from ls.joyous.utils.recurrence import WEEKLY, MONTHLY, TU, SA
from ls.joyous.formats.rss import RssHandler, EventEntry
from ls.joyous.formats.errors import CalendarTypeError
from freezegun import freeze_time
from .testutils import datetimetz
GroupPage = get_group_model()

# ------------------------------------------------------------------------------
class TestFeed(TestCase):
    @freeze_time("2016-03-24")
    def setUp(self):
        imgFile = get_test_image_file()
        imgFile.name = "logo.png"
        self.img = Image.objects.create(title="Logo", file=imgFile)
        imgName = os.path.splitext(os.path.basename(self.img.file.name))[0]
        self.rendName = "{}.width-350.format-png.png".format(imgName)
        Site.objects.update(hostname="joy.test")
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3(R3t')
        self.requestFactory = RequestFactory()
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()
        self.event = RecurringEventPage(owner = self.user,
                                        slug  = "workshop",
                                        title = "Workshop",
                                        image = self.img,
                                        repeat    = Recurrence(dtstart=dt.date(2017,1,1),
                                                               freq=MONTHLY,
                                                               byweekday=[TU(1)],
                                                               until=dt.date(2017,12,26)))
        self.calendar.add_child(instance=self.event)
        self.event.save_revision().publish()
        self.handler = RssHandler()

    def tearDown(self):
        self.img.file.delete(False)
        for rend in self.img.renditions.all():
            rend.file.delete(False)

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        request._messages = FallbackStorage(request)
        request.POST = request.POST.copy()
        request.POST['action-publish'] = "action-publish"
        return request

    @freeze_time("2016-12-02")
    def testServe(self):
        response = self.handler.serve(self.calendar,
                                      self._getRequest("/events/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), "application/xml; charset=utf-8")
        self.assertIn(b'<?xml version=\'1.0\' encoding=\'UTF-8\'?>', response.content)
        soup = BeautifulSoup(response.content, "xml")
        channel = soup.channel
        self.assertEqual(channel.title.string, "Events")
        self.assertEqual(channel.description.string, "Events")
        self.assertEqual(channel.link.string, "http://joy.test/events/")
        self.assertEqual(channel.generator.string, "ls.joyous")
        self.assertEqual(len(channel("image")), 1)
        image = channel.image
        self.assertEqual(image.url.string, "http://joy.test/static/joyous/img/logo.png")
        self.assertEqual(image.title.string, "Events")
        self.assertEqual(image.link.string, "http://joy.test/events/")
        self.assertEqual(channel.lastBuildDate.string, "Fri, 02 Dec 2016 00:00:00 +0000")
        self.assertEqual(len(channel("item")), 1)
        item = channel.item
        self.assertEqual(item.title.string, "Workshop")
        self.assertEqual(item.link.string, "http://joy.test/events/workshop/")
        self.assertEqual(item.enclosure.decode(),
                         '<enclosure length="773" type="image/png" '
                         'url="http://joy.test/media/images/{}"/>'.format(self.rendName))
        self.assertEqual(item.description.decode(), """<description>\n\n\n
  &lt;div class="joy-ev-when joy-field"&gt;
    The first Tuesday of the month (until 26 December 2017)
  &lt;/div&gt;\n
  &lt;div class="joy-ev-next-on joy-field"&gt;
    Next on Tuesday 3rd of January 2017 
  &lt;/div&gt;\n\n\n\n
&lt;div class="rich-text"&gt;&lt;/div&gt;\n</description>""")
        self.assertEqual(item.guid.get("isPermaLink"), "true")
        self.assertEqual(item.guid.string, "http://joy.test/events/workshop/")
        self.assertEqual(item.pubDate.string, "Thu, 24 Mar 2016 00:00:00 +0000")

    def testServeUnsupported(self):
        response = self.handler.serve(self.event,
                                      self._getRequest("/events/workshop"))
        self.assertIsNone(response)

    @freeze_time("2016-03-25")
    def testServeExtraInfo(self):
        info = ExtraInfoPage(owner = self.user,
                             overrides = self.event,
                             except_date = dt.date(2017,2,7),
                             extra_title = "System Demo",
                             extra_information = "<h3>System Demo</h3>")
        self.event.add_child(instance=info)
        info.save_revision().publish()
        response = self.handler.serve(self.calendar,
                                      self._getRequest("/events/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get('Content-Type'), "application/xml; charset=utf-8")
        soup = BeautifulSoup(response.content, "xml")
        channel = soup.channel
        self.assertEqual(channel.title.string, "Events")
        self.assertEqual(len(channel("item")), 2)
        item = channel("item")[1]
        self.assertEqual(item.title.string, "System Demo")
        self.assertEqual(item.link.string, "http://joy.test/events/workshop/2017-02-07-extra-info/")
        self.assertEqual(item.enclosure.decode(),
                         '<enclosure length="773" type="image/png" '
                         'url="http://joy.test/media/images/{}"/>'.format(self.rendName))
        self.assertEqual(item.description.decode(), """<description>\n\n\n
  &lt;div class="joy-ev-when joy-field"&gt;
    Tuesday 7th of February 2017
  &lt;/div&gt;\n\n\n\n
&lt;div class="rich-text"&gt;&lt;h3&gt;System Demo&lt;/h3&gt;&lt;/div&gt;
&lt;div class="rich-text"&gt;&lt;/div&gt;\n</description>""")
        self.assertEqual(item.guid.get("isPermaLink"), "true")
        self.assertEqual(item.guid.string, "http://joy.test/events/workshop/2017-02-07-extra-info/")
        self.assertEqual(item.pubDate.string, "Fri, 25 Mar 2016 00:00:00 +0000")

    @freeze_time("2016-03-26")
    def testServePostponement(self):
        imgFile = get_test_image_file(filename="logo2.png", colour="red")
        newLogo = Image.objects.create(title="Logo", file=imgFile)
        imgName = os.path.splitext(os.path.basename(newLogo.file.name))[0]
        newLogoRender = "{}.width-350.format-png.png".format(imgName)
        postponement = PostponementPage(owner = self.user,
                                        overrides = self.event,
                                        except_date = dt.date(2017,4,4),
                                        image = newLogo,
                                        cancellation_title   = "Workshop Postponed",
                                        cancellation_details = "Workshop will take place next week",
                                        postponement_title   = "Workshop",
                                        date      = dt.date(2017, 4, 11),
                                        details   = "Interesting stuff")
        self.event.add_child(instance=postponement)
        postponement.save_revision().publish()
        response = self.handler.serve(self.calendar,
                                      self._getRequest("/events/"))
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "xml")
        channel = soup.channel
        self.assertEqual(channel.title.string, "Events")
        self.assertEqual(len(channel("item")), 3)
        item1 = channel("item")[1]
        self.assertEqual(item1.title.string, "Workshop Postponed")
        self.assertEqual(item1.link.string, "http://joy.test/events/workshop/2017-04-04-postponement/from/")
        self.assertEqual(item1.enclosure.decode(),
                         '<enclosure length="773" type="image/png" '
                         'url="http://joy.test/media/images/{}"/>'.format(self.rendName))
        self.assertEqual(item1.description.decode(), """<description>\n\n\n
  &lt;div class="joy-ev-when joy-field"&gt;
    Tuesday 4th of April 2017
  &lt;/div&gt;\n\n\n\n
&lt;div class="rich-text"&gt;Workshop will take place next week&lt;/div&gt;\n</description>""")
        self.assertEqual(item1.guid.get("isPermaLink"), "true")
        self.assertEqual(item1.guid.string, "http://joy.test/events/workshop/2017-04-04-postponement/from/")
        self.assertEqual(item1.pubDate.string, "Sat, 26 Mar 2016 00:00:00 +0000")
        item2 = channel("item")[2]
        self.assertEqual(item2.title.string, "Workshop")
        self.assertEqual(item2.link.string, "http://joy.test/events/workshop/2017-04-04-postponement/")
        self.assertEqual(item2.enclosure.decode(),
                         '<enclosure length="773" type="image/png" '
                         'url="http://joy.test/media/images/{}"/>'.format(newLogoRender))
        self.assertEqual(item2.description.decode(), """<description>\n\n\n
  &lt;div class="joy-ev-when joy-field"&gt;
    Tuesday 11th of April 2017
  &lt;/div&gt;\n
  &lt;div class="joy-ev-from-when joy-field"&gt;
    Postponed from Tuesday 4th of April 2017
  &lt;/div&gt;\n\n\n\n
&lt;div class="rich-text"&gt;Interesting stuff&lt;/div&gt;\n</description>""")
        self.assertEqual(item2.guid.get("isPermaLink"), "true")
        self.assertEqual(item2.guid.string, "http://joy.test/events/workshop/2017-04-04-postponement/")
        self.assertEqual(item2.pubDate.string, "Sat, 26 Mar 2016 00:00:00 +0000")

    @freeze_time("2016-03-27")
    def testServeCancellation(self):
        cancellation = CancellationPage(owner = self.user,
                                        overrides = self.event,
                                        except_date = dt.date(2017,5,2),
                                        cancellation_title   = "Workshop Cancelled",
                                        cancellation_details = "No workshop this month")
        self.event.add_child(instance=cancellation)
        cancellation.save_revision().publish()
        response = self.handler.serve(self.calendar,
                                      self._getRequest("/events/"))
        self.assertEqual(response.status_code, 200)
        soup = BeautifulSoup(response.content, "xml")
        channel = soup.channel
        self.assertEqual(channel.title.string, "Events")
        self.assertEqual(len(channel("item")), 2)
        item = channel("item")[1]
        self.assertEqual(item.title.string, "Workshop Cancelled")
        self.assertEqual(item.link.string, "http://joy.test/events/workshop/2017-05-02-cancellation/")
        self.assertEqual(item.enclosure.decode(),
                         '<enclosure length="773" type="image/png" '
                         'url="http://joy.test/media/images/{}"/>'.format(self.rendName))
        self.assertEqual(item.description.decode(), """<description>\n\n\n
  &lt;div class="joy-ev-when joy-field"&gt;
    Tuesday 2nd of May 2017
  &lt;/div&gt;\n\n\n\n
&lt;div class="rich-text"&gt;No workshop this month&lt;/div&gt;\n</description>""")
        self.assertEqual(item.guid.get("isPermaLink"), "true")
        self.assertEqual(item.guid.string, "http://joy.test/events/workshop/2017-05-02-cancellation/")
        self.assertEqual(item.pubDate.string, "Sun, 27 Mar 2016 00:00:00 +0000")

# ------------------------------------------------------------------------------
class TestEntry(TestCase):
    def setUp(self):
        imgFile = get_test_image_file()
        imgFile.name = "people.png"
        self.img = Image.objects.create(title="People", file=imgFile)
        imgName = os.path.splitext(os.path.basename(self.img.file.name))[0]
        self.rendName = "{}.width-350.format-png.png".format(imgName)
        Site.objects.update(hostname="joy.test")
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3(R3t')
        self.requestFactory = RequestFactory()
        self.calendar = CalendarPage(owner = self.user,
                                     slug  = "events",
                                     title = "Events")
        self.home.add_child(instance=self.calendar)
        self.calendar.save_revision().publish()

    def tearDown(self):
        self.img.file.delete(False)
        for rend in self.img.renditions.all():
            rend.file.delete(False)

    def _getRequest(self, path="/"):
        request = self.requestFactory.get(path)
        request.user = self.user
        request.site = self.home.get_site()
        request.session = {}
        request._messages = FallbackStorage(request)
        request.POST = request.POST.copy()
        request.POST['action-publish'] = "action-publish"
        return request

    def testSetCategory(self):
        cat = EventCategory.objects.create(code="A1", name="AlphaOne")
        page = MultidayEventPage(owner = self.user,
                                 slug  = "road-trip",
                                 title = "Road Trip",
                                 date_from = dt.date(2016,11,1),
                                 date_to   = dt.date(2016,11,10),
                                 time_from = dt.time(10),
                                 category  = cat)
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        request = self._getRequest()
        thisEvent = ThisEvent(page.title, page, page.get_url(request))
        entry = EventEntry.fromEvent(thisEvent, request)
        self.assertEqual(entry.category(), [{'term': 'AlphaOne'}])
        rss = entry.rss_entry()
        self.assertEqual(etree.tostring(rss),
b"""<item><title>Road Trip</title><link>http://joy.test/events/road-trip/</link><description>\n\n\n
  &lt;div class="joy-ev-when joy-field"&gt;
    Tuesday 1st of November 2016 at 10am to Thursday 10th of November 2016\n  &lt;/div&gt;\n\n\n\n
&lt;div class="rich-text"&gt;&lt;/div&gt;
</description><guid isPermaLink="true">http://joy.test/events/road-trip/</guid><category>AlphaOne</category></item>""")

    def testSetImage(self):
        page = SimpleEventPage(owner = self.user,
                               slug  = "meetup",
                               title = "Meet Up",
                               image = self.img,
                               date  = dt.date(2016,10,21),
                               time_from = dt.time(16))
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        request = self._getRequest()
        thisEvent = ThisEvent(page.title, page, page.get_url(request))
        entry = EventEntry.fromEvent(thisEvent, request)
        self.assertEqual(entry.enclosure(), {
            'length': '773',
            'url': 'http://joy.test/media/images/{}'.format(self.rendName),
            'type': 'image/png'})

    def testSetDescription(self):
        group = GroupPage(slug = "sandmen", title = "Sandmen")
        self.home.add_child(instance=group)
        group.save_revision().publish()
        page = MultidayEventPage(owner = self.user,
                                 slug  = "road-trip",
                                 title = "Road Trip",
                                 date_from = dt.date(2016,11,1),
                                 date_to   = dt.date(2016,11,10),
                                 group_page = group)
        self.calendar.add_child(instance=page)
        page.save_revision().publish()
        request = self._getRequest()
        thisEvent = ThisEvent(page.title, page, page.get_url(request))
        entry = EventEntry.fromEvent(thisEvent, request)
        rss = entry.rss_entry()
        self.assertEqual(etree.tostring(rss),
b"""<item><title>Road Trip</title><link>http://joy.test/events/road-trip/</link><description>\n
  &lt;div class="joy-ev-who joy-field"&gt;
    &lt;a class="joy-ev-who__link" href="http://joy.test/sandmen/"&gt;Sandmen&lt;/a&gt;
  &lt;/div&gt;\n\n\n
  &lt;div class="joy-ev-when joy-field"&gt;
    Tuesday 1st of November 2016 to Thursday 10th of November 2016\n  &lt;/div&gt;\n\n\n\n
&lt;div class="rich-text"&gt;&lt;/div&gt;
</description><guid isPermaLink="true">http://joy.test/events/road-trip/</guid></item>""")

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
