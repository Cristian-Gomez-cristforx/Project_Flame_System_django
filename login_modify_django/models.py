from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Perfil(models.Model):

    class Rol(models.TextChoices):
        ADMIN    = 'ADMIN',    'Administrador'
        MESERO   = 'MESERO',   'Mesero'
        COCINERO = 'COCINERO', 'Cocinero'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.MESERO,
    )
    telefono = models.CharField(max_length=20, blank=True)
    documento = models.CharField(max_length=30, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    def __str__(self):
        return f'{self.usuario.get_username()} ({self.get_rol_display()})'

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMIN or self.usuario.is_superuser

    @property
    def es_mesero(self):
        return self.rol == self.Rol.MESERO

    @property
    def es_cocinero(self):
        return self.rol == self.Rol.COCINERO


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_para_usuario(sender, instance, created, **kwargs):
    if created:
        rol = Perfil.Rol.ADMIN if instance.is_superuser else Perfil.Rol.MESERO
        Perfil.objects.create(usuario=instance, rol=rol)
