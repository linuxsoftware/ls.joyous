#  ls.joyous
#  -----------

import codecs
from setuptools import setup, find_packages


setup(name="ls.joyous",
      version="0.1.2",
      description="A calendar application for Wagtail.",
      long_description=codecs.open("README.rst", encoding="utf-8").read(),
      keywords=["calendar", "events"],
      classifiers=["Development Status :: 4 - Beta",
                   "Framework :: Django",
                   "Framework :: Django :: 1.11",
                   "Framework :: Django :: 2.0",
                   "License :: OSI Approved :: BSD License",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Programming Language :: Python :: 2",
                   "Programming Language :: Python :: 3",
                   "Topic :: Office/Business :: Groupware",
                   "Topic :: Office/Business :: Scheduling",
                   "Topic :: Software Development :: Libraries :: Python Modules"
                  ],
      platforms="any",
      author="David Moore",
      author_email="david@linuxsoftware.nz",
      url="https://github.com/linuxsoftware/ls.joyous",
      license="BSD",
      install_requires=["python-dateutil", "inflect", "holidays"],
      test_requires=["coverage", "django-beautifulsoup-test"],
      packages=find_packages(),
      include_package_data=True,
      test_suite="ls.joyous.tests",
      zip_save=False,
     )
