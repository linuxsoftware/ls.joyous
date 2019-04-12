#!/usr/bin/env python
import os
import sys


if __name__ == '__main__':
    from django.core.management import execute_from_command_line
    os.environ['DJANGO_SETTINGS_MODULE'] = 'ls.joyous.tests.settings'
    os.environ['PYTHONSTARTUP'] = __file__
    argv = sys.argv[:1] + ['shell'] + sys.argv[1:]
    execute_from_command_line(argv)

elif __name__ == "builtins":
    # useful once we are in the shell
    import datetime as dt
    from django.utils import timezone
    from django.conf import settings
    import pytz
    import pprint
    import ls.joyous
    from ls.joyous.models import *
    from ls.joyous.utils.recurrence import *
    from ls.joyous.utils import manythings, telltime
    from ls.joyous.formats import ical
    L = list
    sys.displayhook = pprint.pprint
    sys.__interactivehook__()
    timezone.activate("Pacific/Auckland")

