# inventario/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator

# ==================== VALIDACIONES ====================

def validar_solo_letras(valor):
    """Solo letras y espacios"""
    if not valor.replace(' ', '').isalpha():
        raise ValidationError('Este campo solo permite letras y espacios')


def validar_cantidad_positiva(valor):
    """Cantidad debe ser mayor a 0"""
    if valor <= 0:
        raise ValidationError('La cantidad debe ser mayor a 0')


def validar_precio_positivo(valor):
    """Precio debe ser mayor a 0"""
    if valor <= 0:
        raise ValidationError('El precio debe ser mayor a 0')


# ==================== MODELOS ====================

class Insumo(models.Model):
    id_insumo = models.AutoField(primary_key=True)
    nombre_insumo = models.CharField(
        max_length=100,
        validators=[
            validar_solo_letras,
            RegexValidator(regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', message='Solo se permiten letras y espacios')
        ],
        verbose_name="Nombre del Insumo"
    )
    cantidad_insumo = models.PositiveIntegerField(
        validators=[validar_cantidad_positiva],
        verbose_name="Cantidad"
    )
    precio_insumo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Precio de Compra"
    )

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['nombre_insumo']

    def __str__(self):
        return f"{self.nombre_insumo} - {self.cantidad_insumo} und | ${self.precio_insumo}"

    def clean(self):
        super().clean()
        if self.cantidad_insumo <= 0:
            raise ValidationError({'cantidad_insumo': 'La cantidad no puede ser cero o negativa'})


class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre_producto = models.CharField(
        max_length=100,
        validators=[validar_solo_letras],
        verbose_name="Nombre del Producto"
    )
    precio_producto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Precio de Venta"
    )
    
    ingrediente_producto = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Ingredientes (temporal)"
    )

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre_producto']

    def __str__(self):
        return f"{self.nombre_producto} - ${self.precio_producto}"


class Bebida(models.Model):
    id_bebida = models.AutoField(primary_key=True)
    nombre_bebida = models.CharField(
        max_length=100,
        validators=[validar_solo_letras],
        verbose_name="Nombre de la Bebida"
    )
    cantidad_bebida = models.PositiveIntegerField(
        validators=[validar_cantidad_positiva],
        verbose_name="Cantidad en Stock"
    )
    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Precio de Compra"
    )
    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="Precio de Venta"
    )
    tipo_bebida = models.CharField(max_length=50, verbose_name="Tipo de Bebida")
    tamaño_bebida = models.CharField(max_length=20, verbose_name="Tamaño")

    class Meta:
        verbose_name = "Bebida"
        verbose_name_plural = "Bebidas"
        ordering = ['nombre_bebida']

    def __str__(self):
        return f"{self.nombre_bebida} ({self.tamaño_bebida}) - ${self.precio_venta}"