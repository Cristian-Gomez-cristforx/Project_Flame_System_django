from django.apps import AppConfig


class LoginModifyDjangoConfig(AppConfig):
    name = 'login_modify_django'
    verbose_name = 'Autenticación y perfiles'

    def ready(self):
        from . import models  # noqa: F401
