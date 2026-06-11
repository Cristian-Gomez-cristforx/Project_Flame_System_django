# inventario/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator


def validar_cantidad_positiva(value):
    if value < 0:
        raise ValidationError('La cantidad no puede ser negativa.')

# ==================== VALIDACIONES ====================

def validar_solo_letras(valor):
    "Solo letras y espacios (incluye tildes y ñ)"
    if not valor.replace(' ', '').isalpha():
        raise ValidationError('Este campo solo permite letras y espacios')


# ==================== MODELO CATEGORÍA ====================
class Categoria(models.Model):
    nombre_categoria = models.CharField(
        max_length=80,
        unique=True,
        validators=[
            validar_solo_letras,
            RegexValidator(
                regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message='Solo se permiten letras y espacios'
            )
        ],
        verbose_name="Nombre de la Categoría"
    )
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre_categoria']

    def __str__(self):
        return self.nombre_categoria


# ==================== INSUMO ====================
class Insumo(models.Model):

    UNIDAD_CHOICES = [
        ('g',          'Gramos (g)'),
        ('kg',         'Kilogramos (kg)'),
        ('ml',         'Mililitros (ml)'),
        ('und',        'Unidades')
    ]

    id_insumo = models.AutoField(primary_key=True)
    nombre_insumo = models.CharField(
        max_length=100,
        validators=[validar_solo_letras],
        verbose_name="Nombre del Insumo"
    )
    cantidad_insumo = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad en Stock"
    )
    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDAD_CHOICES,
        default='g',
        verbose_name="Unidad de Medida"
    )
    precio_insumo = models.DecimalField(
        max_digits=8,
        decimal_places=0,
        validators=[MinValueValidator(1)],
        verbose_name="Precio de Compra"
    )

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['nombre_insumo']

    def __str__(self):
        return f"{self.nombre_insumo} - {self.cantidad_insumo} {self.get_unidad_medida_display()} | ${self.precio_insumo:,}"
# ==================== PRODUCTO ====================
class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre_producto = models.CharField(
        max_length=100,
        validators=[validar_solo_letras],
        verbose_name="Nombre del Producto"
    )
    precio_producto = models.DecimalField(
        max_digits=8,
        decimal_places=0,
        validators=[MinValueValidator(1)],
        verbose_name="Precio de Venta"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos',
        verbose_name="Categoría"
    )
    
    activo = models.BooleanField(default=True, verbose_name="Producto Activo")
    
    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre_producto']

    def __str__(self):
        return f"{self.nombre_producto} - ${self.precio_producto:,}"


# ==================== BEBIDA ====================

class Bebida(models.Model):
    id_bebida = models.AutoField(primary_key=True)
    nombre_bebida = models.CharField(max_length=100, validators=[validar_solo_letras])
    
    # Tipo de Bebida (texto libre)
    tipo_bebida = models.CharField(
        max_length=50, 
        verbose_name="Tipo de Bebida",
        validators=[validar_solo_letras]   # ← Esto evita números y símbolos
    )
    
    # Tamaño con opciones predefinidas
    TAMAÑO_CHOICES = [
        ('350ml', '350 ml'),
        ('500ml', '500 ml'),
        ('1L', '1 Litro'),
        ('1.5L', '1.5 Litros'),
        ('2L', '2 Litros'),
        ('3L', '3 Litros'),
        ('Personal', 'Personal'),
        ('Otro', 'Otro'),
    ]
    
    tamaño_bebida = models.CharField(
        max_length=20, 
        choices=TAMAÑO_CHOICES,
        verbose_name="Tamaño"
    )
    
    cantidad_bebida = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_compra = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    precio_venta = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Bebida"
        verbose_name_plural = "Bebidas"
        ordering = ['nombre_bebida']

    def __str__(self):
        return f"{self.nombre_bebida} ({self.tamaño_bebida})"
    
    # ==================== RECETA DEL PRODUCTO ====================
class RecetaProducto(models.Model):

    producto = models.OneToOneField(
        Producto,
        on_delete=models.CASCADE,
        related_name='receta',
        verbose_name="Producto"
    )
    descripcion_receta = models.TextField(
        blank=True,
        null=True,
        verbose_name="Descripción / Instrucciones de preparación"
    )
    activa = models.BooleanField(default=True, verbose_name="Receta Activa")

    class Meta:
        verbose_name = "Receta de Producto"
        verbose_name_plural = "Recetas de Productos"

    def __str__(self):
        return f"Receta de {self.producto.nombre_producto}"

    def puede_prepararse(self):

        detalles = self.detalles.all()

        if not detalles.exists():
            return False, " Esta receta no tiene insumos registrados."

        faltantes = []

        for detalle in detalles:
            stock_actual = detalle.insumo.cantidad_insumo
            cantidad_necesaria = detalle.cantidad_requerida

            if stock_actual < cantidad_necesaria:
                faltantes.append(
                    f"{detalle.insumo.nombre_insumo}: "
                    f"necesitas {cantidad_necesaria} {detalle.unidad}, "
                    f"pero solo hay {stock_actual}"
                )

        if faltantes:
            mensaje = "No se puede preparar. Stock insuficiente en:\n" + "\n".join(faltantes)
            return False, mensaje

        return True, f" Se puede preparar '{self.producto.nombre_producto}' correctamente."

    def cuantas_unidades_posibles(self):

        detalles = self.detalles.all()

        if not detalles.exists():
            return 0

        minimo = None

        for detalle in detalles:
            if detalle.cantidad_requerida > 0:
                posibles = detalle.insumo.cantidad_insumo // detalle.cantidad_requerida
                if minimo is None or posibles < minimo:
                    minimo = posibles

        return minimo if minimo is not None else 0

    def descontar_insumos(self):

        puede, mensaje = self.puede_prepararse()

        if not puede:
            raise ValidationError(mensaje)

        for detalle in self.detalles.all():
            insumo = detalle.insumo
            insumo.cantidad_insumo -= detalle.cantidad_requerida
            insumo.save()


# ==================== DETALLE DE RECETA ====================
class DetalleReceta(models.Model):

    receta = models.ForeignKey(
        RecetaProducto,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name="Receta"
    )
    insumo = models.ForeignKey(
        Insumo,
        on_delete=models.PROTECT,
        related_name='en_recetas',
        verbose_name="Insumo"
    )
    cantidad_requerida = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad Requerida"
    )

    class Meta:
        verbose_name = "Detalle de Receta"
        verbose_name_plural = "Detalles de Receta"
        unique_together = ('receta', 'insumo')

    def unidad(self):
  
        return self.insumo.get_unidad_medida_display()

    def __str__(self):
        return (
            f"{self.insumo.nombre_insumo}: "
            f"{self.cantidad_requerida} {self.unidad()} "   # ← viene del insumo
            f"→ {self.receta.producto.nombre_producto}"
        )