from django.apps import AppConfig


class PagesConfig(AppConfig):
    name = 'pages'

    def ready(self):
        from . import checks  # noqa: F401
