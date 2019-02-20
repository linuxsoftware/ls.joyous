ls.joyous
===============

.. image:: https://secure.travis-ci.org/linuxsoftware/ls.joyous.svg?branch=master
   :target: https://travis-ci.org/linuxsoftware/ls.joyous
.. image:: https://coveralls.io/repos/github/linuxsoftware/ls.joyous/badge.svg?branch=master
   :target: https://coveralls.io/github/linuxsoftware/ls.joyous?branch=master

About
------
Joyous is a reusable calendar application for Wagtail. Features include rrule
based recurring events with cancellations and postponements; iCal import and export; Gcal export; event permissioning; timezone handling; and multi-site aware calendars.

Demo
-----
Yet another demonstration Wagtail website `code <http://github.com/linuxsoftware/orange-wagtail-site>`_ | `live <http://demo.linuxsoftware.nz>`_

Installation
-------------

Install the package.

.. code-block:: bash

    $ pip install ls.joyous

Add ``ls.joyous`` and ``wagtail.contrib.modeladmin`` to your ``INSTALLED_APPS``

.. code-block:: python

    INSTALLED_APPS = [
        'ls.joyous',
        'wagtail.contrib.modeladmin',
        # ... etc ...
        ]

Settings
--------
* ``JOYOUS_HOLIDAYS``: Observed holidays - e.g. ``NZ[WGN]``
* ``JOYOUS_GROUP_SELECTABLE``: Enable group selection? ``False`` or ``True``
* ``JOYOUS_GROUP_MODEL``: To swap out the group model
* ``JOYOUS_TIME_INPUT``: Prompt for ``12`` or ``24`` hour times

Compatibility
--------------
I am aiming to support the latest releases of Wagtail and Django.  Older versions may be dropped without much notice.  Let me know if that is a problem for you.  Other versions may work - YMMV.

FYI: Django 2.1 is a definite minimum requirement.

Getting Help
-------------
Please report bugs or ask questions using the `Issue Tracker <http://github.com/linuxsoftware/ls.joyous/issues>`_.

Thanks To
-------------

`Sauce Labs <https://saucelabs.com>`_ for their cross-browser testing platform.

.. image:: /docs/powered-by-sauce-labs.png

