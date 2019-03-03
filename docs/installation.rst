.. _installation:

Installing
==========

The easiest way to install Joyous is from the 
`Python Package Index <https://pypi.org/project/ls.joyous/>`_. 

Install the package.

.. code-block:: console

    $ pip install ls.joyous

Add ls.joyous and wagtail.contrib.modeladmin to your INSTALLED_APPS

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'ls.joyous',
        'wagtail.contrib.modeladmin',
        ...
    ]

.. _compatibility:

Compatibility
-------------
I am aiming to support the latest releases of Wagtail and Django. Older versions may be dropped without much notice. Let me know if that is a problem for you.

Joyous |version| is known to work with the following versions of Wagtail, Django and Python.

=======   ======   =======
Wagtail   Django   Python
=======   ======   =======
2.3       2.1.7    3.5.6
2.3       2.1.7    3.6.3
2.3       2.1.7    3.7.1
2.4       2.1.5    3.5.4
2.4       2.1.7    3.5.6
2.4       2.1.7    3.6.3
2.4       2.1.7    3.7.1
=======   ======   =======

Other versions may work - YMMV.  Django 2.1 is a definite minimum requirement.
