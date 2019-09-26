Groups
======

Your organisation might be made up of several groups which can have their own
events.  Or you might want to group events together for another reason.

The template tag 
:py:func:`group_upcoming_events <ls.joyous.templatetags.joyous_tags.group_upcoming_events>`
displays the events that are coming up for a group.

Adding the event as a child of a group automatically assigns the event to that
group, or you can set the :py:attr:`group_page <ls.joyous.models.EventBase.group_page>`
field on the event.  

.. note::
    It is not expected that you will both add an event as the child of a group
    and set the group_page field.  But if you do then: if it is the same group,
    the event will only show up in the group once; if they are different groups,
    the event will show up in both groups, but will only show itself as
    belonging to the group that it is a child of.


Models
~~~~~~

GroupPage
---------
A simple default page model for a group.  It just has a title and a rich-text content area.

The template for GroupPage includes the
:py:func:`group_upcoming_events <ls.joyous.templatetags.joyous_tags.group_upcoming_events>`
template tag.
