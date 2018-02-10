===============
ls.joyous
===============

A calendar application for Wagtail.

Events
-------
Simple, multiday, and recurring events can be added to the calendar.

Installation
-------------

Install the package. Currently it is only available from GitHub, coming to PyPI soon!

.. code-block:: bash

    $ pip install -e git://github.com/linuxsoftware/ls.joyous.git#egg=ls.joyous

Add ``ls.joyous`` and ``wagtail.contrib.modeladmin`` to your ``INSTALLED_APPS``

.. code-block:: python

    INSTALLED_APPS = [
        'ls.joyous',
        'wagtail.contrib.modeladmin',

        'wagtail.wagtailforms',
        'wagtail.wagtailredirects',
        'wagtail.wagtailembeds',
        'wagtail.wagtailsites',
        'wagtail.wagtailusers',
        'wagtail.wagtailsnippets',
        'wagtail.wagtaildocs',
        'wagtail.wagtailimages',
        'wagtail.wagtailsearch',
        'wagtail.wagtailadmin',
        'wagtail.wagtailcore',
        # ... etc ...
        ]


Settings
--------
* ``JOYOUS_DAY_OF_WEEK_START``: ``Sunday`` or ``Monday``
* ``JOYOUS_DEFAULT_EVENTS_VIEW``: ``Monthly``, ``List`` or ``Weekly`` view
* ``JOYOUS_HOLIDAYS``: Observed holidays - e.g. ``NZ[WGN]``
* ``JOYOUS_GROUP_SELECTABLE``: Enable group selection? ``False`` or ``True``
* ``JOYOUS_GROUP_MODEL``: To swap out the group model
* ``JOYOUS_TIME_INPUT``: Prompt for ``12`` or ``24`` hour times
