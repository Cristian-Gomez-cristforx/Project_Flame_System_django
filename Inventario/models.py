from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from decimal import Decimal, ROUND_HALF_UP
from math import ceil


def validar_solo_letras(valor):
    if not valor.replace(' ', '').isalpha():
        raise ValidationError('Este campo solo permite letras y espacios')


# ==================== CATEGORÍA ====================
class Categoria(models.Model):

    class Tipo(models.TextChoices):
        PRODUCTO = 'PRODUCTO', 'Producto'
        BEBIDA   = 'BEBIDA',   'Bebida'
        INSUMO   = 'INSUMO',   'Insumo'


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
   
    class Meta:
        
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['tipo', 'nombre_categoria']
        
        
    def clean(self):

        if Categoria.objects.filter(
            nombre_categoria__iexact=self.nombre_categoria
        ).exclude(
            pk=self.pk
        ).exists():

            raise ValidationError({
                'nombre_categoria':
                'Esta categoría ya existe.'
            })    

    def __str__(self):
        return self.nombre_categoria
    
    

# ==================== INSUMO ====================
class Insumo(models.Model):
    UNIDAD_CHOICES = [
        ('g',   'Gramos (g)'),
        ('und', 'Unidades')
    ]

    id_insumo       = models.AutoField(primary_key=True)
    nombre_insumo   = models.CharField(max_length=100, validators=[validar_solo_letras], unique=True)
    cantidad_insumo = models.PositiveIntegerField(validators=[MinValueValidator(0)])
    unidad_medida   = models.CharField(max_length=20, choices=UNIDAD_CHOICES, default='g')
    precio_insumo   = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    categoria       = models.ForeignKey(
        'Categoria', 
        on_delete=models.PROTECT, 
        
        related_name='insumos'
    )
    
    precio_gramo    = models.DecimalField(max_digits=7, decimal_places=2, default=0, verbose_name="Precio Gramo")
    stock_maximo    = models.PositiveIntegerField(default=0, editable=False)
    cantidad_a_agregar = models.DecimalField(max_digits=8, decimal_places=2,null=True, blank=True,default=0,validators=[MinValueValidator(0)])
    

    class Meta:
        verbose_name = "Insumo"
        verbose_name_plural = "Insumos"
        ordering = ['nombre_insumo']

    def __str__(self):
        return f"{self.nombre_insumo} | {self.cantidad_insumo} {self.get_unidad_medida_display()} | ${self.precio_gramo:,.0f}".replace(',','.')

    
    def clean(self):
        # Si el campo está vacío no hacer nada
        if not self.cantidad_a_agregar:
            return

        # Validar que no sea negativo
        if self.cantidad_a_agregar < 0:
            raise ValidationError({
                'cantidad_a_agregar':
                'La cantidad a agregar no puede ser negativa.'
            })

        # Solo validar si ya existe el objeto
        if self.pk:

            insumo_original = Insumo.objects.get(pk=self.pk)

            if self.cantidad_insumo != insumo_original.cantidad_insumo:
                raise ValidationError({
                    f'No puedes añadir {self.cantidad_a_agregar}|{self.unidad_medida} a la misma vez que quieres modficar la cantidad  actual de'
                        f'{insumo_original.cantidad_insumo}|{self.unidad_medida} ¡Elige la opción correcto!.'
                })
    
    def save(self, *args, **kwargs):
        # Ejecutar validaciones
        self.full_clean()

        edito_cantidad_directamente = False

        if self.pk:

            insumo_original = Insumo.objects.get(pk=self.pk)

            # Si agrega stock adicional
            if self.cantidad_a_agregar and self.cantidad_a_agregar > 0:

                precio_por_gramo = (
                    Decimal(insumo_original.precio_insumo)
                    / Decimal(insumo_original.cantidad_insumo)
                ).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP
                )

                costo_agregado = (
                    Decimal(self.cantidad_a_agregar)
                    * precio_por_gramo
                )

                # Sumar al stock actual de la BD
                self.cantidad_insumo = (
                    insumo_original.cantidad_insumo
                    + self.cantidad_a_agregar
                )

                # Sumar el costo adicional
                self.precio_insumo = (
                    insumo_original.precio_insumo
                    + costo_agregado
                ).quantize(
                    Decimal("1"),
                    rounding=ROUND_HALF_UP
                )

                # Reiniciar el campo temporal
                self.cantidad_a_agregar = 0

            elif self.cantidad_insumo != insumo_original.cantidad_insumo:
                edito_cantidad_directamente = True
        else:
            edito_cantidad_directamente = True

        # Actualizar stock máximo
        if edito_cantidad_directamente:
            self.stock_maximo = self.cantidad_insumo
        elif self.cantidad_insumo > self.stock_maximo:
            self.stock_maximo = self.cantidad_insumo

        # Actualizar precio por gramo
        if self.cantidad_insumo > 0:
            self.precio_gramo = (
                Decimal(self.precio_insumo) / Decimal(self.cantidad_insumo)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            self.precio_gramo = Decimal("0.00")
            
        

        super().save(*args, **kwargs)
        
    @property
    def bajo_stock_30(self):
        if self.stock_maximo > 0:
            return self.cantidad_insumo <= (self.stock_maximo * 0.3)
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
        on_delete=models.PROTECT, 
        related_name='productos'
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre_producto']

    def __str__(self):
        return f"{self.nombre_producto} - ${self.precio_producto:,}"
# ==================== BEBIDA ====================
class Bebida(models.Model):
    TAMAÑO_CHOICES = [
        ('350ml', '350 ml'), ('500ml', '500 ml'), ('1L', '1 Litro'),
        ('1.5L', '1.5 Litros'), ('2L', '2 Litros'), ('Personal', 'Personal'), ('Otro', 'Otro'),
    ]
    id_bebida          = models.AutoField(primary_key=True)
    nombre_bebida      = models.CharField(max_length=100, validators=[validar_solo_letras])
    tamaño_bebida      = models.CharField(max_length=20, choices=TAMAÑO_CHOICES)
    cantidad_bebida    = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_compra      = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    precio_venta       = models.DecimalField(max_digits=8, decimal_places=0, validators=[MinValueValidator(1)])
    categoria          = models.ForeignKey( 'Categoria',  on_delete=models.PROTECT,  related_name='bebidas' )
    cantidad_a_agregar = models.PositiveIntegerField(default=0, null=True, blank=True,verbose_name="Cantidad adicional")
    precio_unitario_compra = models.DecimalField(max_digits=8, decimal_places=0, default=0, verbose_name="Precio Unitario Compra")
    precio_unitario_venta = models.DecimalField(max_digits=8, decimal_places=0, default=0,verbose_name="Precio Unitario Venta")
    stock_maximo  = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        verbose_name = "Bebida"
        verbose_name_plural = "Bebidas"
        ordering = ['nombre_bebida']

    @property
    def bajo_stock_30(self):
        if self.stock_maximo > 0:
            return self.cantidad_bebida <= (self.stock_maximo * 0.3)
        return False

    @property
    def porcentaje_del_maximo(self):
        if self.stock_maximo > 0:
            return round((self.cantidad_bebida / self.stock_maximo) * 100, 1)
        return 100

    def __str__(self):
        return f"{self.nombre_bebida} ({self.tamaño_bebida})"
    
    def clean(self):
        
        if self.precio_venta <= self.precio_compra:
            raise ValidationError({
                'precio_venta':
                'Precio de venta debe ser mayor que el de compra.'
             })
            
        if not self.cantidad_a_agregar:
            return
        
        if self.cantidad_a_agregar < 0:
            raise ValidationError({
                'cantidad_a_agregar':
                'La cantidad a agregar no puede ser negativa.'
            })
            
        if self.pk:
            bebida_original = Bebida.objects.get(pk=self.pk)
            
            errores ={}
            
            if self.cantidad_bebida != bebida_original.cantidad_bebida:
                errores['cantidad_bebida'] = (
                    f'No puedes añadir {self.cantidad_a_agregar} a la misma vez que quieres modficar la cantidad  actual de'
                    f'{bebida_original.cantidad_bebida} ¡Elige la opción correcto!.'
                )
                
            if self.tamaño_bebida != bebida_original.tamaño_bebida:
                errores['tamaño_bebida'] = (
                    f'No puedes añadir {self.cantidad_a_agregar} a la misma vez que quieres modficar la cantidad  actual de'
                    f'{bebida_original.tamaño_bebida} ¡Elige la opción correcto!.'
                )
                
            if self.precio_compra != bebida_original.precio_compra:
                errores['precio_compra'] = (
                    f'No puedes añadir {self.cantidad_a_agregar} a la misma vez que quieres modficar la cantidad  actual de'
                    f'{bebida_original.precio_compra} ¡Elige la opción correcto!.'
                )
                
            if self.precio_venta != bebida_original.precio_venta:
                errores['precio_venta'] = (
                    f'No puedes añadir {self.cantidad_a_agregar} a la misma vez que quieres modficar la cantidad  actual de'
                    f'{bebida_original.precio_venta} ¡Elige la opción correcto!.'
                )
            
            if errores:
                raise ValidationError(errores)
            
    def save(self, *args, **kwargs):

        self.full_clean()
        
        if self.pk:
            bebida_original = Bebida.objects.get(pk=self.pk)

            if (
                self.cantidad_a_agregar and
                self.cantidad_a_agregar > 0
            ):

                # mantener el mismo margen de ganancia
                margen = (
                    bebida_original.precio_venta /
                    bebida_original.precio_compra
                )

                # precio unitario de compra actual
                precio_unitario = (
                    bebida_original.precio_compra /
                    bebida_original.cantidad_bebida
                )

                costo_adicional = (
                    self.cantidad_a_agregar *
                    precio_unitario
                )

                # actualizar cantidad
                self.cantidad_bebida = (
                    bebida_original.cantidad_bebida +
                    self.cantidad_a_agregar
                )

                # actualizar compra
                self.precio_compra = (
                    bebida_original.precio_compra +
                    costo_adicional
                )

                # actualizar venta
                self.precio_venta = round(
                    self.precio_compra * margen
                )

                # reiniciar
                self.cantidad_a_agregar = 0

        if self.cantidad_bebida > self.stock_maximo:
            self.stock_maximo = self.cantidad_bebida

        if self.cantidad_bebida > 0:
            self.precio_unitario_compra = (
                Decimal(self.precio_compra) / Decimal(self.cantidad_bebida)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            self.precio_unitario_venta = (
                Decimal(self.precio_venta) / Decimal(self.cantidad_bebida)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            self.precio_unitario_compra = Decimal("0.00")
            self.precio_unitario_venta = Decimal("0.00")

        super().save(*args, **kwargs)
        
        

                
            
# ==================== RECETA Y DETALLE ====================
class RecetaProducto(models.Model):
    producto = models.OneToOneField(Producto, on_delete=models.CASCADE, related_name='receta')
    activa   = models.BooleanField(default=True)

    @property
    def costo_preparacion(self):
        total = Decimal('0.00')
        
        for detalle in self.detalles.all():
            total += detalle.costo_detalle
            
        return total
    

    def clean(self):
        super().clean()
        
        if (
            self.pk and
            self.costo_preparacion >=
            self.producto.precio_producto
        ):
            raise ValidationError(
                "El costo de preparación no puede ser "
               " mayor al precio de producto.")
          

    class Meta:
        verbose_name = "Receta de Producto"
        verbose_name_plural = "Recetas de Productos"

    def __str__(self):
        return f"Receta de {self.producto.nombre_producto}"

    def cuantas_unidades_posibles(self):
        
        detalles = self.detalles.select_related('insumo').all()
        if not detalles:
            return 0

        max_unidades = None
        for detalle in detalles:
            if detalle.cantidad_requerida <= 0:
                continue
            stock = detalle.insumo.cantidad_insumo
            posibles = stock // detalle.cantidad_requerida
            if max_unidades is None or posibles < max_unidades:
                max_unidades = posibles

        return max_unidades if max_unidades is not None else 0


class DetalleReceta(models.Model):
    receta             = models.ForeignKey(RecetaProducto, on_delete=models.CASCADE, related_name='detalles')
    insumo             = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name='en_recetas')
    cantidad_requerida = models.PositiveIntegerField(validators=[MinValueValidator(1)])

      
    @property
    def costo_detalle(self):
        if self.insumo and self.insumo.precio_gramo:
            return(
                Decimal(self.cantidad_requerida)
                * Decimal(self.insumo.precio_gramo)
            )
            
        return Decimal('0.00')
            
    
    class Meta:
        verbose_name = "Detalle de Receta"
        verbose_name_plural = "Detalles de Receta"
        unique_together = ('receta', 'insumo')

    def __str__(self):
        return ""
    


# ==================== MERMA ====================
class Merma(models.Model):
    
    MOTIVOS_CHOICES = [
        ('Caducado', 'Caducado'),
        ('Dañado', 'Dañado'),
        ('Error preparación', 'Error en preparación'),
        ('Robo / Pérdida', 'Robo o pérdida'),
        ('Otro', 'Otro'),
    ]

    id_merma         = models.AutoField(primary_key=True)
    insumo           = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name='mermas')
    insumo_snapshot = models.CharField(max_length=100, null= True, blank=True)  
    fecha_merma      = models.DateTimeField(auto_now_add=True)
    cantidad_mermada = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    motivo           = models.CharField(max_length=150, choices=MOTIVOS_CHOICES)
    descripcion      = models.TextField(blank=True, null=True)
    precio_insumo    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_total_merma = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    responsable      = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Merma"
        verbose_name_plural = "Mermas"
        ordering = ['-fecha_merma']

    def __str__(self):
        return f"Merma #{self.id_merma} | {self.insumo.nombre_insumo}"

    def clean(self):
        super().clean()
        if self.insumo and self.cantidad_mermada is not None:
            if self.cantidad_mermada > self.insumo.cantidad_insumo:
                raise ValidationError({
                    'cantidad_mermada': 
                        f'No puedes registrar {self.cantidad_mermada} unidades de merma. '
                        f'El insumo "{self.insumo.nombre_insumo}" solo tiene '
                        f'{self.insumo.cantidad_insumo} {self.insumo.get_unidad_medida_display()} en stock.'
                })

    def save(self, *args, **kwargs):
        
        if not self.pk:
            self.insumo_snapshot = (
                f"{self.insumo.nombre_insumo} | "
                f"{self.insumo.cantidad_insumo} gramos | "
                f"${self.insumo.precio_insumo:,.0f}".replace(',','.')
            )

        
        self.full_clean()

     
        self.precio_insumo = self.insumo.precio_insumo

        if self.insumo.cantidad_insumo > 0:
            precio_por_unidad = Decimal(self.insumo.precio_insumo) / Decimal(self.insumo.cantidad_insumo)
            self.costo_total_merma = Decimal(self.cantidad_mermada) * precio_por_unidad
        else:
            self.costo_total_merma = Decimal('0.00')
            
            
        if not self.pk:
            
        
           self.insumo.cantidad_insumo -= self.cantidad_mermada

        self.insumo.precio_insumo = (
            self.insumo.precio_insumo - self.costo_total_merma
        ).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )

        if self.insumo.cantidad_insumo > 0:
            self.insumo.precio_gramo = (
                self.insumo.precio_insumo /
                self.insumo.cantidad_insumo
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )
        else:
            self.insumo.precio_gramo = Decimal("0.00")

        self.insumo.save(
            update_fields=[
                "cantidad_insumo",
                "precio_insumo",
                "precio_gramo",
            ]
        )

        super().save(*args, **kwargs)