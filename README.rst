ls.joyous
===============

Events
-------
Simple, multiday, and recurring events can be added to the calendar.

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
* ``JOYOUS_DEFAULT_EVENTS_VIEW``: ``Monthly``, ``List`` or ``Weekly`` view
* ``JOYOUS_HOLIDAYS``: Observed holidays - e.g. ``NZ[WGN]``
* ``JOYOUS_GROUP_SELECTABLE``: Enable group selection? ``False`` or ``True``
* ``JOYOUS_GROUP_MODEL``: To swap out the group model
* ``JOYOUS_TIME_INPUT``: Prompt for ``12`` or ``24`` hour times

Compatibility
--------------
ls.joyous is known to work with the following versions of Python/Django/Wagtail.

======   ======   =======
Python   Django   Wagtail
======   ======   =======
3.5.4    2.0.3    2.0
3.5.4    1.11.9   1.13.1
======   ======   =======

I am aiming to support the latest version of each.  Older versions may be dropped without much notice.  Let me know if that is a problem for you.  Other versions may work - YMMV.

Getting Help
-------------
Please report bugs or ask questions using the `Issue Tracker <http://github.com/linuxsoftware/ls.joyous/issues>`_.
