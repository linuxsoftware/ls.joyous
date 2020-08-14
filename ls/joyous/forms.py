# ------------------------------------------------------------------------------
# Joyous Forms
# ------------------------------------------------------------------------------
import warnings
from django.conf import settings
from wagtail.core.models import PageBase, Page
from wagtail.admin import widgets
from wagtail.admin.forms import WagtailAdminPageForm

# ------------------------------------------------------------------------------
class BorgPageForm(WagtailAdminPageForm):
    """
    Your page form will be assimilated.
    """
    @classmethod
    def assimilate(cls, form_class):
        if issubclass(form_class, WagtailAdminPageForm):
            cls.assimilated_class = form_class

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        form_class = self.__class__
        assimilated_class = getattr(self, 'assimilated_class', None)
        if assimilated_class:
            assimilated_class.Meta = form_class.Meta
            assimilated_class._meta = form_class._meta
            assimilated_class.formsets = form_class.formsets
            assimilated_class._has_explicit_formsets = \
                    form_class._has_explicit_formsets
            self.assimilated = assimilated_class(*args, **kwargs)
        else:
            self.assimilated = None

    def clean(self):
        if self.assimilated:
            self.assimilated.fields = self.fields
            self.assimilated.cleaned_data = self.cleaned_data
            cleaned_data = self.assimilated.clean()
            if self.assimilated._errors is not None:
                if self._errors is not None:
                    self._errors.update(self.assimilated._errors)
                else:
                    self._errors = self.assimilated._errors
            return cleaned_data
        else:
            return super().clean()

    def save(self, commit=True):
        if self.assimilated:
            return self.assimilated.save(commit)
        else:
            return super().save(commit)

# ------------------------------------------------------------------------------
class FormClassOverwriteWarning(RuntimeWarning):
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
        my_form_class = cls._base_form_class
        if my_form_class is None:
            cls._base_form_class = form_class
        else:
            if getattr(settings, "JOYOUS_DEFEND_FORMS", False):
                if issubclass(my_form_class, BorgPageForm):
                    my_form_class.assimilate(form_class)
            else:
                cls._base_form_class = form_class
                warning = FormClassOverwriteWarning(
                              "{} has been overwritten with {}, "
                              "consider enabling JOYOUS_DEFEND_FORMS"
                              .format(my_form_class.__name__,
                                      form_class.__name__))
                warnings.warn(warning, stacklevel=2)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
