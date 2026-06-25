from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator


def validar_solo_letras(valor):
    if not valor.replace(' ', '').isalpha():
        raise ValidationError('Este campo solo permite letras y espacios')


# ==================== CATEGORÍA ÚNICA (CON TIPO) ====================
class Categoria(models.Model):

   
    class Tipo(models.TextChoices):
        PRODUCTO = 'PRODUCTO', 'Producto'
        BEBIDA   = 'BEBIDA',   'Bebida'

    nombre_categoria = models.CharField(
        max_length=80,
        unique=True,
        validators=[validar_solo_letras],
        verbose_name="Nombre de la Categoría"
    )
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,   
        verbose_name="Tipo"
    )
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['tipo', 'nombre_categoria']

    def __str__(self):
        return f"{self.nombre_categoria} ({self.get_tipo_display()})"


# ==================== INSUMO ====================
class Insumo(models.Model):
    UNIDAD_CHOICES = [
        ('g',   'Gramos (g)'),
        ('kg',  'Kilogramos (kg)'),
        ('ml',  'Mililitros (ml)'),
        ('und', 'Unidades')
    ]

    id_insumo       = models.AutoField(primary_key=True)
    nombre_insumo   = models.CharField(max_length=100, validators=[validar_solo_letras])
    cantidad_insumo = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unidad_medida   = models.CharField(max_length=20, choices=UNIDAD_CHOICES, default='g')
    precio_insumo   = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    stock_maximo    = models.PositiveIntegerField(default=0, verbose_name="Stock Máximo")

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['nombre_insumo']

    def __str__(self):
     return f"{self.nombre_insumo} | {self.cantidad_insumo} {self.get_unidad_medida_display()} | ${self.precio_insumo:,}"
 
    stock_maximo = models.PositiveIntegerField(default=0, verbose_name="Stock Máximo")

    def __str__(self):
        return f"{self.nombre_insumo} | {self.cantidad_insumo} {self.get_unidad_medida_display()}"

    def save(self, *args, **kwargs):
        
        if self.cantidad_insumo > self.stock_maximo:
            self.stock_maximo = self.cantidad_insumo
        super().save(*args, **kwargs)

  
    @property
    def bajo_stock_30(self):
      
        if self.stock_maximo > 0:
            limite = self.stock_maximo * 0.3
            return self.cantidad_insumo <= limite
        return False

    @property
    def porcentaje_del_maximo(self):
        
        if self.stock_maximo > 0:
            return round((self.cantidad_insumo / self.stock_maximo) * 100, 1)
        return 100

    def abrir_turno(self):
   
        self.stock_maximo = self.cantidad_insumo
        self.save(update_fields=['stock_maximo'])

# ==================== PRODUCTO ====================
class Producto(models.Model):
    id_producto      = models.AutoField(primary_key=True)
    nombre_producto  = models.CharField(max_length=100, validators=[validar_solo_letras])
    precio_producto  = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    categoria        = models.ForeignKey(
        'Categoria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre_producto']

    def __str__(self):
        return f"{self.nombre_producto} - ${self.precio_producto:,}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.categoria_id:
            categoria, _ = Categoria.objects.get_or_create(
                nombre_categoria='Productos',
                defaults={'tipo': Categoria.Tipo.PRODUCTO}
            )
            self.categoria = categoria
        super().save(*args, **kwargs)


# ==================== BEBIDA ====================
class Bebida(models.Model):
    TAMAÑO_CHOICES = [
        ('350ml',    '350 ml'),
        ('500ml',    '500 ml'),
        ('1L',       '1 Litro'),
        ('1.5L',     '1.5 Litros'),
        ('2L',       '2 Litros'),
        ('3L',       '3 Litros'),
        ('Personal', 'Personal'),
        ('Otro',     'Otro'),
    ]

    id_bebida       = models.AutoField(primary_key=True)
    nombre_bebida   = models.CharField(max_length=100, validators=[validar_solo_letras])
    tamaño_bebida   = models.CharField(max_length=20, choices=TAMAÑO_CHOICES)
    cantidad_bebida = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_compra   = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    precio_venta    = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    categoria       = models.ForeignKey(
        'Categoria',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bebidas'
    )

    class Meta:
        verbose_name = "Bebida"
        verbose_name_plural = "Bebidas"
        ordering = ['nombre_bebida']

    def __str__(self):
        return f"{self.nombre_bebida} ({self.tamaño_bebida})"

   
    def save(self, *args, **kwargs):
        if not self.pk and not self.categoria_id:
            categoria, _ = Categoria.objects.get_or_create(
                nombre_categoria='Bebidas',
                defaults={'tipo': Categoria.Tipo.BEBIDA}
            )
            self.categoria = categoria
        super().save(*args, **kwargs)


# ==================== RECETA Y DETALLE ====================

class RecetaProducto(models.Model):
    producto          = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='receta')
    descripcion_receta = models.TextField(blank=True, null=True)
    activa            = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Receta de Producto"
        verbose_name_plural = "Recetas de Productos"

    def __str__(self):
        return f"Receta de {self.producto.nombre_producto}"

    def cuantas_unidades_posibles(self):
        """
        Calcula cuántas unidades del producto se pueden preparar
        con el stock actual de insumos según la receta.
        """
        if not self.detalles.exists():
            return 0

        max_posibles = float('inf')
        for detalle in self.detalles.select_related('insumo').all():
            if detalle.cantidad_requerida <= 0:
                continue
            stock_disponible = detalle.insumo.cantidad_insumo
            posibles = stock_disponible // detalle.cantidad_requerida
            if posibles < max_posibles:
                max_posibles = posibles

        return int(max_posibles) if max_posibles != float('inf') else 0


class DetalleReceta(models.Model):
    receta             = models.ForeignKey(RecetaProducto, on_delete=models.CASCADE, related_name='detalles')
    insumo             = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name='en_recetas')
    cantidad_requerida = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = "Detalle de Receta"
        verbose_name_plural = "Detalles de Receta"
        unique_together = ('receta', 'insumo')

    def __str__(self):
        return f"{self.insumo.nombre_insumo}: {self.cantidad_requerida}"

def cuantas_unidades_posibles(self):

    if not self.detalles.exists():
        return 0

    max_posibles = float('inf')
    for detalle in self.detalles.select_related('insumo').all():
        if detalle.cantidad_requerida <= 0:
            continue
        stock_disponible = detalle.insumo.cantidad_insumo
        posibles = stock_disponible // detalle.cantidad_requerida
        if posibles < max_posibles:
            max_posibles = posibles

    return int(max_posibles) if max_posibles != float('inf') else 0
    


# ==================== MERMA ====================
class Merma(models.Model):
    MOTIVOS_CHOICES = [
        ('Caducado',           'Caducado'),
        ('Dañado',             'Dañado'),
        ('Error preparación',  'Error en preparación'),
        ('Robo / Pérdida',     'Robo o pérdida'),
        ('Otro',               'Otro'),
    ]

    id_merma         = models.AutoField(primary_key=True)
    insumo           = models.ForeignKey('Insumo', on_delete=models.PROTECT, related_name='mermas')
    fecha_merma      = models.DateTimeField(auto_now_add=True)
    cantidad_mermada = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    motivo           = models.CharField(max_length=150, choices=MOTIVOS_CHOICES)
    descripcion      = models.TextField(blank=True, null=True)
    precio_insumo    = models.DecimalField(max_digits=12, decimal_places=2)
    costo_total_merma = models.DecimalField(max_digits=12, decimal_places=2)
    responsable      = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Merma"
        verbose_name_plural = "Mermas"
        ordering = ['-fecha_merma']

    def __str__(self):
        return f"Merma #{self.id_merma} - {self.insumo.nombre_insumo}"

    def save(self, *args, **kwargs):
        self.precio_insumo = self.insumo.precio_insumo
        if self.insumo.cantidad_insumo > 0:
            precio_por_unidad = self.insumo.precio_insumo / self.insumo.cantidad_insumo
            self.costo_total_merma = self.cantidad_mermada * precio_por_unidad
        else:
            self.costo_total_merma = 0

        if self.cantidad_mermada > self.insumo.cantidad_insumo:
            raise ValidationError("Stock insuficiente")

        self.insumo.cantidad_insumo -= self.cantidad_mermada
        self.insumo.save()
        super().save(*args, **kwargs)