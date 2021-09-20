from django.apps import AppConfig

class JoyousAppConfig(AppConfig):
    name = 'ls.joyous'
    label = 'joyous'
    verbose_name = "Joyous Calendar"
    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        from ls.joyous import signals
