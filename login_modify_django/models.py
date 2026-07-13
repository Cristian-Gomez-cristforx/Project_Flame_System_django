import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


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


@receiver(post_save, sender=Perfil)
def sincronizar_grupo_al_guardar_perfil(sender, instance, **kwargs):
    """Refleja el rol del Perfil como pertenencia a un grupo de Django."""
    from .permisos import sincronizar_grupo_usuario
    try:
        sincronizar_grupo_usuario(instance.usuario, instance.rol)
    except Exception:
        # Silencioso durante migraciones iniciales cuando aún no existen todas las tablas.
        pass


class RecuperacionContrasena(models.Model):
    PIN_VIGENCIA_MIN = 15
    MAX_INTENTOS = 5

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recuperaciones',
    )
    pin_hash = models.CharField(max_length=64)
    creado_en = models.DateTimeField(auto_now_add=True)
    expira_en = models.DateTimeField()
    intentos = models.PositiveIntegerField(default=0)
    verificado = models.BooleanField(default=False)
    usado = models.BooleanField(default=False)

    class Meta:
        ordering = ['-creado_en']

    @staticmethod
    def _hash(pin: str) -> str:
        return hashlib.sha256(pin.encode('utf-8')).hexdigest()

    @classmethod
    def generar_para(cls, usuario):
        cls.objects.filter(usuario=usuario, usado=False).update(usado=True)
        pin = f'{secrets.randbelow(1000000):06d}'
        recup = cls.objects.create(
            usuario=usuario,
            pin_hash=cls._hash(pin),
            expira_en=timezone.now() + timedelta(minutes=cls.PIN_VIGENCIA_MIN),
        )
        return recup, pin

    def esta_vigente(self):
        return (
            not self.usado
            and self.expira_en > timezone.now()
            and self.intentos < self.MAX_INTENTOS
        )

    def verificar(self, pin: str) -> bool:
        if not self.esta_vigente():
            return False
        self.intentos += 1
        if self._hash(pin) == self.pin_hash:
            self.verificado = True
            self.save(update_fields=['verificado', 'intentos'])
            return True
        self.save(update_fields=['intentos'])
        return False
