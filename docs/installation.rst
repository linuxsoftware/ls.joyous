.. _installation:

Installing
==========

The easiest way to install Joyous is from the 
`Python Package Index <https://pypi.org/project/ls.joyous/>`_. 

Install the package.

.. code-block:: console

    $ pip install ls.joyous

Add ls.joyous and wagtail.contrib.modeladmin to your INSTALLED_APPS.

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'ls.joyous',
        'wagtail.contrib.modeladmin',
        ...
    ]

Make sure USE_TZ is set to True

.. code-block:: python

    USE_TZ = True

The blocks ``content``, ``extra_css`` and ``extra_js`` are required in the base.html template for the Joyous templates to work.  A Wagtail project based upon the `default template <https://github.com/wagtail/wagtail/blob/master/wagtail/project_template/project_name/templates/base.html>`_ will have these.

Run migrations and collectstatic.

.. code-block:: console

    $ ./manage.py migrate
    $ ./manage.py collectstatic --no-input

.. _compatibility:

Compatibility
-------------

Joyous version 1.4.0 is known to work with the following versions of Wagtail, Django and Python.

=======   ======   =======
Wagtail   Django   Python
=======   ======   =======
2.10.2    3.1.6    3.7.1
2.10.2    3.1.6    3.8.7
2.10.2    3.1.6    3.9.1
2.11.3    3.1.6    3.7.1
2.11.3    3.1.6    3.8.7
2.11.3    3.1.6    3.9.1
2.12      3.1.6    3.7.1
2.12      3.1.6    3.8.7
2.12      3.1.6    3.9.1
=======   ======   =======

Other versions may work - YMMV.
