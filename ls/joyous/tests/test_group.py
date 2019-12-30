# ------------------------------------------------------------------------------
# Test Group Page
# ------------------------------------------------------------------------------
import sys
import datetime as dt
from django.test import RequestFactory, override_settings
from django_bs_test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from wagtail.core.models import Page
from ls.joyous.models.groups import GroupPage
from ls.joyous.models.groups import get_group_model

# ------------------------------------------------------------------------------
class Test(TestCase):
    def setUp(self):
        self.home = Page.objects.get(slug='home')
        self.user = User.objects.create_user('i', 'i@joy.test', 's3cr3t')
        self.group = GroupPage(owner = self.user,
                               slug  = "moreporks",
                               title = "Moreporks Club")
        self.home.add_child(instance=self.group)
        self.group.save_revision().publish()

    @override_settings(JOYOUS_THEME_CSS = "/static/joyous/joyous_stellar_theme.html")
    def testIncludeThemeCss(self):
        response = self.client.get("/moreporks/")
        self.assertEqual(response.status_code, 200)
        soup = response.soup
        links = soup.head('link')
        self.assertEqual(len(links), 2)
        link = links[1]
        self.assertEqual(link['href'], "/static/joyous/joyous_stellar_theme.html")
        self.assertEqual(link['type'], "text/css")
        self.assertEqual(link['rel'], ["stylesheet"])

    @override_settings(JOYOUS_GROUP_MODEL = "foo")
    def testInvalidGroupModel(self):
        with self.assertRaises(ImproperlyConfigured):
            get_group_model()

    @override_settings(JOYOUS_GROUP_MODEL = "foo.bar")
    def testUninstalledGroupModel(self):
        with self.assertRaises(ImproperlyConfigured):
            get_group_model()

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
