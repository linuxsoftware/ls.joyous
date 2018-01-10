#!/usr/bin/env python

import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner

if __name__ == "__main__":
    os.environ['DJANGO_SETTINGS_MODULE'] = 'ls.joyous.tests.settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(top_level="ls/joyous")
    failures = test_runner.run_tests(["ls.joyous.tests"])
    sys.exit(bool(failures))
