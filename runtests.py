#!/usr/bin/env python
import os
import os.path
import sys
import django
from glob import glob
from django.conf import settings
from django.test.utils import get_runner

def cleanMedia():
    mediaDir = settings.MEDIA_ROOT
    imgDir = os.path.join(mediaDir, "images")
    origImgDir = os.path.join(mediaDir, "original_images")
    for path in glob(os.path.join(imgDir, "*")) + glob(os.path.join(origImgDir, "*")):
        try:
            os.remove(path)
        except:
            print("Error deleting", path)

def runPytest():
    import pytest
    opts = []
    parallelOpt = ""
    labels = []
    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            opts.append(arg)
            if arg.startswith("-n"):
                parallelOpt = arg
        else:
            # convert unittest "test_ical.TestImport.testMeetup" format to
            # "ls/joyous/test_ical.py::TestImport::testMeetup"
            path = arg.split(".")
            if len(path) >= 2 and path[1] == "py":
                del path[1]
            path[0] += ".py"
            labels.append("ls/joyous/tests/"+"::".join(path))
    if not parallelOpt:
        # default to running in parallel
        opts.append("-n2")
    errCode = pytest.main(opts + labels)
    return errCode

def runDjangoTest():
    cleanMedia()
    verbosity = 1
    if "-v" in sys.argv or "--verbose" in sys.argv:
        verbosity = 2
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
    from coverage import Coverage
    cover = Coverage()
    cover.start()
    failures = runDjangoTest()
    cover.stop()
    cover.save()
    cover.html_report()
    return failures

def main():
    doRunCoverage = "--coverage" in sys.argv
    os.environ['DJANGO_SETTINGS_MODULE'] = 'ls.joyous.tests.settings'
    if "--pytest" in sys.argv:
        sys.argv.remove("--pytest")
        if doRunCoverage:
            sys.argv.remove("--coverage")
            sys.argv.append("--cov=ls/joyous")
            sys.argv.append("--cov-report=html")
        failures = runPytest()
    else:
        if doRunCoverage:
            failures = coverage()
        else:
            failures = runDjangoTest()
    return failures

if __name__ == "__main__":
    failures = main()
    sys.exit(failures)
