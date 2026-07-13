from django.apps import AppConfig


def _sync_grupos_post_migrate(sender, **kwargs):
    """Al terminar migrate de esta app: crea/actualiza grupos y sincroniza usuarios."""
    try:
        from .permisos import sincronizar_grupos, sincronizar_todos_los_usuarios
        sincronizar_grupos()
        sincronizar_todos_los_usuarios()
    except Exception:
        # En el primer migrate puede que otras apps aún no estén listas; se recupera
        # solo al siguiente migrate o ejecutando "python manage.py sync_grupos".
        pass


class LoginModifyDjangoConfig(AppConfig):
    name = 'login_modify_django'
    verbose_name = 'Autenticación y perfiles'

    def ready(self):
        from django.db.models.signals import post_migrate
        from . import models  # noqa: F401
        post_migrate.connect(_sync_grupos_post_migrate, sender=self)
