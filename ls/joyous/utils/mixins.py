# ------------------------------------------------------------------------------
# Useful Mixins
# ------------------------------------------------------------------------------
from django.contrib.contenttypes.models import ContentType


# ------------------------------------------------------------------------------
class ProxyPageMixin:
    """
    Adding this mixin allows inheritance without needing a new table.  The
    proxy model has its own content type which allows it to be selected as a
    separate page type in the Wagtail admin interface.  No change is made to
    the manager, but peers() will return a queryset of others of the same type.
    See also https://github.com/wagtail/wagtail/pull/1736
    """
    class Meta:
        proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initContentType()

    def _initContentType(self):
        if getattr(self, 'id', object()) is None:
            self.content_type = self._getContentType()

    @classmethod
    def peers(cls):
        """Return others of the same type"""
        return cls.objects.filter(content_type=cls._getContentType())

    @classmethod
    def _getContentType(cls):
        return ContentType.objects.get_for_model(cls, for_concrete_model=False)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
