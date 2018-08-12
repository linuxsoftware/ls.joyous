# ------------------------------------------------------------------------------
# Joyous Fields
# ------------------------------------------------------------------------------

import sys
from django.db.models import Field
from django.core.exceptions import ValidationError
from django.forms.fields import Field as FormField
from .utils.recurrence import Recurrence
from .widgets import RecurrenceWidget

# ------------------------------------------------------------------------------
class RecurrenceField(Field):
    description = "The rule for recurring events"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 255
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def from_db_value(self, value, *args):
        return self.to_python(value)

    def to_python(self, value):
        if not value:
            return None
        if isinstance(value, Recurrence):
            return value
        try:
            return Recurrence(value)
        except (TypeError, ValueError, UnboundLocalError) as err:
            raise ValidationError("Invalid input for recurrence {}".format(err))

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def get_prep_value(self, rule):
        return repr(rule)

    def get_prep_lookup(self, lookup_type, value):
        raise TypeError('Lookup type %r not supported.' % lookup_type)

    def formfield(self, **kwargs):
        defaults = {'form_class': RecurrenceFormField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def get_internal_type(self):
        return "CharField"

# ------------------------------------------------------------------------------
class RecurrenceFormField(FormField):
    widget = RecurrenceWidget

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
