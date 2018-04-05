# ----------------------
#  ls.joyous
# ----------------------

import sys
import subprocess
import codecs
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand

class RunTests(TestCommand):
    def run(self):
        errno = subprocess.call([sys.executable, 'runtests.py'])
        raise SystemExit(errno)

setup(name="ls.joyous",
      use_scm_version={
          'write_to':  "ls/joyous/_version.py",
      },
      description="A calendar application for Wagtail.",
      long_description=codecs.open("README.rst", encoding="utf-8").read(),
      keywords=["calendar", "events", "wagtail", "groupware"],
      classifiers=["Development Status :: 4 - Beta",
                   "Framework :: Django",
                   "Framework :: Django :: 1.11",
                   "Framework :: Django :: 2.0",
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
                                  "static/joyous/css/*.css",
                                  "static/joyous/css/vendor/*.css",
                                  "static/joyous/img/*.png",
                                  "static/joyous/img/*.jpg",
                                  "static/joyous/js/*.js",
                                  "static/joyous/js/vendor/*.js"
                                 ],
                   },
      setup_requires=["setuptools_scm"],
      install_requires=["django-timezone-field",
                        "holidays",
                        "icalendar",
                        "inflect",
                        "python-dateutil",
                       ],
      tests_require=["coverage",
                     "django-beautifulsoup-test",
                     "freezegun"],
      test_suite="ls.joyous.tests",
      cmdclass={'test': RunTests},
      zip_safe=False,
     )
