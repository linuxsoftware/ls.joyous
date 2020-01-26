# ------------------------------------------------------------------------------
# Joyous Fields
# ------------------------------------------------------------------------------
import sys
from django.db.models import Field
from django.core.exceptions import ValidationError
from django.forms.fields import Field as FormField
from django.forms import TypedMultipleChoiceField, CheckboxSelectMultiple
from django.utils.encoding import force_str
from .utils.recurrence import Recurrence
from .widgets import RecurrenceWidget

# ------------------------------------------------------------------------------
class RecurrenceField(Field):
    """
    DB Field for recurrences
    """
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
        """Sorry recurrences cannot be used in where clauses"""
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
class MultipleSelectField(Field):
    """
    Field with multiple *static* choices (not via m2m)

    From https://gist.github.com/kottenator/9a50e4207cff15c03f8e
    by Rostyslav Bryzgunov

    Value is stored in DB as comma-separated values
    Default widget is forms.CheckboxSelectMultiple
    Python value: list of values
    """
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
            return []
        if isinstance(value, list):
            return value
        return value.split(",")

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def get_prep_value(self, value):
        if not value:
            return ""
        return ",".join(value)

    def get_prep_lookup(self, lookup_type, value):
        """Sorry multiselects cannot be used in where clauses"""
        raise TypeError('Lookup type %r not supported.' % lookup_type)

    def _coerceChoice(self, choice):
        options = [option[0] for option in self.choices]
        if choice not in options:
            raise ValidationError(self.error_messages['invalid_choice'],
                                  code='invalid_choice',
                                  params={'value': choice})
        return choice

    def formfield(self, **kwargs):
        defaults = {'choices_form_class': MultipleSelectFormField,
                    'choices':            self.choices,
                    'coerce':             self._coerceChoice}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def get_internal_type(self):
        return "CharField"

    def validate(self, value, model_instance):
        if not self.editable:
            return

        if value is None and not self.null:
            raise ValidationError(self.error_messages['null'], code='null')

        if not self.blank and value in self.empty_values:
            raise ValidationError(self.error_messages['blank'], code='blank')

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name)
        if self.choices:
            fieldname = self.name
            choicedict = dict(self.choices)
            def func(self):
                value = getattr(self, fieldname)
                if not isinstance(value, list):
                    value = [value]
                return ", ".join([force_str(choicedict.get(i, i))
                                  for i in value])
            setattr(cls, 'get_%s_display' % fieldname, func)

# ------------------------------------------------------------------------------
class MultipleSelectFormField(TypedMultipleChoiceField):
    widget = CheckboxSelectMultiple

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
