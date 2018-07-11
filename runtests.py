#!/usr/bin/env python
import os
import sys
from coverage import Coverage
import django
from django.conf import settings
from django.test.utils import get_runner

def run():
    verbosity = 1
    if "-v" in sys.argv or "--verbose" in sys.argv:
        verbosity = 2
    os.environ['DJANGO_SETTINGS_MODULE'] = 'ls.joyous.tests.settings'
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner(top_level="ls/joyous",
                             verbosity=verbosity,
                             keepdb=True)
    labels = ["ls.joyous.tests."+arg for arg in sys.argv[1:]
              if not arg.startswith("-")]
    if not labels:
        labels = ["ls.joyous.tests"]
    failures = test_runner.run_tests(labels)
    return failures

def coverage():
    if "--coverage" in sys.argv:
        cover = Coverage(source=["ls.joyous"])
        cover.start()
        failures = run()
        cover.stop()
        cover.save()
        cover.html_report()
    else:
        failures = run()
    return failures

if __name__ == "__main__":
    failures = coverage()
    sys.exit(bool(failures))
