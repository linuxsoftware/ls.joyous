import os

DEBUG = True
JOYOUS_DEBUG = True
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = os.path.dirname(os.path.dirname(PROJECT_DIR))
STATIC_ROOT = os.path.join(PROJECT_DIR, 'tests', 'test-static')
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'tests', 'test-media')
TEMPLATES_DIR = os.path.join(PROJECT_DIR, 'tests', 'templates')
STATIC_URL = '/static/'
MEDIA_URL = '/media/'


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

SECRET_KEY = 'not needed'

ROOT_URLCONF = 'ls.joyous.tests.urls'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ TEMPLATES_DIR ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'wagtail.tests.context_processors.do_not_use_static_url',
            ],
            'debug': True,  # required in order to catch template errors
        },
    },
]


MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'wagtail.core.middleware.SiteMiddleware',
    'wagtail.contrib.redirects.middleware.RedirectMiddleware',
]

INSTALLED_APPS = [
    'ls.joyous',

    'wagtail.contrib.forms',
    'wagtail.contrib.redirects',
    'wagtail.embeds',
    'wagtail.sites',
    'wagtail.users',
    'wagtail.snippets',
    'wagtail.documents',
    'wagtail.images',
    'wagtail.search',
    'wagtail.admin',
    'wagtail.core',

    'modelcluster',
    'taggit',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

WSGI_APPLICATION = 'demo.wsgi.application'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Tokyo'
USE_I18N = True
USE_L10N = True
USE_TZ = True

WAGTAIL_SITE_NAME = "Testing"
BASE_URL = 'http://joy.test'
ALLOWED_HOSTS = ['joy.test', '.joy.test', '.localhost', '127.0.0.1', '[::1]']

JOYOUS_HOLIDAYS = "NZ[*]"
JOYOUS_GROUP_SELECTABLE = True
