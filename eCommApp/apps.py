from django.apps import AppConfig


class EcommappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'eCommApp'

    def ready(self):
        import eCommApp.signals