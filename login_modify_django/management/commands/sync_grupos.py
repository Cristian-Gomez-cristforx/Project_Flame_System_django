from django.core.management.base import BaseCommand

from login_modify_django.models import Perfil
from login_modify_django.permisos import (
    ROL_GRUPO,
    sincronizar_grupos,
    sincronizar_grupo_usuario,
)


class Command(BaseCommand):
    help = (
        'Crea/actualiza los grupos de Django con los permisos por rol '
        'y sincroniza a qué grupo pertenece cada usuario según su Perfil.rol.'
    )

    def handle(self, *args, **options):
        self.stdout.write('Sincronizando grupos y permisos...')
        sincronizar_grupos()
        for nombre in ROL_GRUPO.values():
            self.stdout.write(f'  ✓ grupo "{nombre}"')

        self.stdout.write('\nAsignando usuarios existentes a su grupo...')
        perfiles = Perfil.objects.select_related('usuario').all()
        for perfil in perfiles:
            sincronizar_grupo_usuario(perfil.usuario, perfil.rol)
            self.stdout.write(f'  · {perfil.usuario.username} → {ROL_GRUPO[perfil.rol]}')

        self.stdout.write(self.style.SUCCESS('\nSincronización completada.'))
