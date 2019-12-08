# ----------------------
#  ls.joyous
# ----------------------

import sys
import os
import io
import subprocess
from pathlib import Path
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

# allow setup.py to be run from any path
here = Path(__file__).resolve().parent
os.chdir(str(here))

with io.open("README.rst", encoding="utf-8") as readme:
    README = readme.read()

class RunTests(TestCommand):
    def run(self):
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)

setup(name="ls.joyous",
      use_scm_version={
          'write_to':  "ls/joyous/_version.py",
      },
      description="A calendar application for Wagtail.",
      long_description=README,
      keywords=["calendar", "events", "wagtail", "groupware"],
      classifiers=["Development Status :: 5 - Production/Stable",
                   "Framework :: Django",
                   "Framework :: Wagtail",
                   "Framework :: Wagtail :: 2",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 3",
                   "Topic :: Office/Business :: Groupware",
                   "Topic :: Office/Business :: Scheduling",
                   "Topic :: Software Development :: Libraries :: Python Modules"
                  ],
      platforms="any",
      author="David Moore",
      author_email="david@linuxsoftware.co.nz",
      url="https://github.com/linuxsoftware/ls.joyous",
      license="BSD",
      packages=find_packages(where=".", exclude=["ls.joyous.tests"]),
      package_data={'ls.joyous': ["templates/joyous/*.html",
                                  "templates/joyous/*/*.html",
                                  "templates/joyous/*/*.xml",
                                  "static/joyous/css/*.css",
                                  "static/joyous/css/vendor/*.css",
                                  "static/joyous/img/*.png",
                                  "static/joyous/img/*.jpg",
                                  "static/joyous/js/*.js",
                                  "static/joyous/js/vendor/*.js",
                                  "locale/*/LC_MESSAGES/django.po",
                                  "locale/*/LC_MESSAGES/django.mo"
                                 ],
                   },
      setup_requires=["setuptools_scm"],
      install_requires=["django-timezone-field",
                        "holidays",
                        "icalendar",
                        "num2words",
                        "python-dateutil",
                        "feedgen",
                       ],
      tests_require=["coverage",
                     "django-beautifulsoup-test",
                     "freezegun",
                     "wagtailgmaps",
                     "pytest",
                     "pytest-pythonpath",
                     "pytest-django",
                     "pytest-cov",
                     "pytest-xdist",
                     "pytest-subtests",
                    ],
      test_suite="ls.joyous.tests",
      cmdclass={'test': RunTests},
      zip_safe=False,
     )
