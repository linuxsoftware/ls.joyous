from django.apps import AppConfig

class JoyousAppConfig(AppConfig):
    name = 'ls.joyous'
    label = 'joyous'
    verbose_name = "Joyous Wagtail Calendar"

    def ready(self):
        from ls.joyous import signals
