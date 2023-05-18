# ------------------------------------------------------------------------------
# Joyous Forms
# ------------------------------------------------------------------------------
import warnings
from django.conf import settings
from wagtail.models import PageBase
from wagtail.admin.forms import WagtailAdminPageForm

# ------------------------------------------------------------------------------

class BorgPageForm(WagtailAdminPageForm):
    """
    Your page form will be assimilated.
    """
    @classmethod
    def assimilate(cls, form_class):
        if form_class is None or issubclass(form_class, WagtailAdminPageForm):
            cls.assimilated_class = form_class

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assimilated_class = getattr(self, 'assimilated_class', None)
        if (assimilated_class):
            borg_form_class = self._get_assimilated_form(assimilated_class)
            self.assimilated = borg_form_class(*args, **kwargs)
        else:
            self.assimilated = None

    def clean(self):
        if self.assimilated:
            self.assimilated.cleaned_data = self.cleaned_data
            self.assimilated._errors = self._errors
            cleaned_data = self.assimilated.clean()
            self._errors.update(self.assimilated._errors)
            return cleaned_data
        else:
            return super().clean()

    def save(self, commit=True):
        if self.assimilated:
            page = self.assimilated.save(commit)
        else:
            page = super().save(commit)
        return page

    def _get_assimilated_form(self, assimilated_class):
        # based on wagtail.admin.panels.get_form_for_model
        assimilated_class.declared_fields.update(self.declared_fields)
        attrs = {'model':    self._meta.model,
                 'fields':   self._meta.fields,
                 'formsets': self._meta.formsets,
                 'widgets':  self._meta.widgets}
        class_name = "Assimilated" + assimilated_class.__name__
        bases = (object,)
        if hasattr(assimilated_class, 'Meta'):
            bases = (assimilated_class.Meta,) + bases
        form_class_attrs = {
            'Meta': type('Meta', bases, attrs),
        }
        metaclass = type(assimilated_class)
        return metaclass(class_name,
                         (assimilated_class,),
                         form_class_attrs)

# ------------------------------------------------------------------------------
def _getName(thing):
    return getattr(thing, '__name__', repr(thing))

class FormClassOverwriteWarning(RuntimeWarning):
    pass

class FormCannotAssimilateWarning(RuntimeWarning):
    pass

class FormDefender(PageBase):
    """
    Metaclass for pages who don't want their base_form_class changed
    """
    def __new__(mcs, name, bases, attrs):
        new_attrs = dict((k if k != 'base_form_class' else '_'+k, v)
                         for k, v in attrs.items())
        cls = super().__new__(mcs, name, bases, new_attrs)
        return cls

    @property
    def base_form_class(cls):
        return cls._base_form_class

    @base_form_class.setter
    def base_form_class(cls, form_class):
        # Probably need to also call get_edit_handler.cache_clear()
        # after changing base_form_class for it to affect the
        # edit_handler.
        my_form_class = cls._base_form_class
        if my_form_class is None:
            cls._base_form_class = form_class
            return

        if (isinstance(form_class, type) and
            issubclass(form_class, my_form_class)):
            # don't assimilate or generate warning for subclasses
            cls._base_form_class = form_class
            return

        if getattr(settings, "JOYOUS_DEFEND_FORMS", False):
            if issubclass(my_form_class, BorgPageForm):
                my_form_class.assimilate(form_class)
            else:
                warning = FormCannotAssimilateWarning(
                          "{} cannot assimilate {}"
                          .format(_getName(my_form_class),
                                  _getName(form_class)))
                warnings.warn(warning, stacklevel=2)

        else:
            cls._base_form_class = form_class
            warning = FormClassOverwriteWarning(
                          "{} has been overwritten with {}, "
                          "consider enabling JOYOUS_DEFEND_FORMS"
                          .format(_getName(my_form_class),
                                  _getName(form_class)))
            warnings.warn(warning, stacklevel=2)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
