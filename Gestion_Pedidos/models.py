from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from Inventario.models import (Producto,Bebida,Insumo)

class Mesa(models.Model):
    numero_mesa = models.PositiveIntegerField(unique=True)
    activa = models.BooleanField(default=True) #Esta es para decir si las mesass siguen en el negocio, NO es para decir si están ocupadas o no.
    ocupada = models.BooleanField(default=False)#Esta si es para decir que estan ucupadas

    class Meta:
        ordering = ['numero_mesa']

    def __str__(self):
        return f"Mesa {self.numero_mesa}"
    
class Pedido(models.Model):
    
    id_pedido = models.AutoField(primary_key=True)
    numero_factura= models.CharField(max_length=20,unique=True,blank=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True) #Esta se va a ir actualizando,cada vez que haya cambio en pedido,hasta finalizar, por lo cual seria fecha de entrega del pedido.
    inventario_descontado = models.BooleanField(default=False)
    class TipoPedido(models.TextChoices):
          MESA= 'Mesa','Mesa'
          RECOGIDA= 'Recoger', 'Recoger'
          DOMICILIO= 'Domicilio','Domicilio'
    tipo= models.CharField(max_length=20,choices=TipoPedido.choices,default=TipoPedido.MESA) 
    class EstadoPedido(models.TextChoices):
          PENDIENTE = 'Pendiente', 'Pendiente'
          COCINA = 'En cocina', 'En cocina'
          COCINADO = 'Cocinado', 'Cocinado'
          PAGADO = 'Pagado', 'Pagado'
          FINALIZADO = 'Finalizado', 'Finalizado'
          CANCELADO = 'Cancelado', 'Cancelado'

    class TipoPago(models.TextChoices):
          EFECTIVO = "Efectivo", "Efectivo"
          TRANSFERENCIA = "Transferencia", "Transferencia"
          TARJETA = "Tarjeta", "Tarjeta"
    
    tipo_pago = models.CharField(max_length=20,choices=TipoPago.choices,blank=True,null=True)
    estado = models.CharField(max_length=20,choices=EstadoPedido.choices,default=EstadoPedido.PENDIENTE)
    mesero = models.ForeignKey(User,on_delete=models.PROTECT)
    direccion_pedi= models.CharField(max_length=150,blank=True,null=True, verbose_name="Dirección")
    mesa = models.ForeignKey(
         Mesa,
         on_delete=models.PROTECT,
         null=True,
         blank=True,
         related_name='pedidos')
    nombre_cliente = models.CharField(max_length=70,blank=True,verbose_name="Nombre del cliente")
    telefono_cliente = models.CharField(max_length=20,blank=True,verbose_name="Teléfono del cliente")
    minutos_recogida = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name="Tiempo pactado de recogida (minutos)",
    )
    
    def clean(self):

        if self.estado == self.EstadoPedido.PAGADO and not self.tipo_pago:
           raise ValidationError(
                "Debe seleccionar un tipo de pago.")
         
        if (
           self.tipo == self.TipoPedido.MESA
           and not self.mesa
           and not getattr(self, '_defer_mesa', False)):
           raise ValidationError(
               "Debe seleccionar una mesa.")
        
        if (
           self.tipo == self.TipoPedido.DOMICILIO and not self.direccion_pedi):
           raise ValidationError(
               "Debe ingresar una dirección.")
        
        if (
           self.tipo == self.TipoPedido.RECOGIDA and self.mesa):
           raise ValidationError("Los pedidos para recoger no usan mesa.")

        if (
           self.tipo == self.TipoPedido.RECOGIDA and not self.minutos_recogida):
           raise ValidationError(
               "Debe indicar el tiempo pactado de recogida en minutos.")
        
        
        if (
            self.estado == self.EstadoPedido.FINALIZADO and not self.tipo_pago):
            raise ValidationError("Debe registrar un pago antes de finalizar.")



    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)

        if not self.numero_factura:
           self.numero_factura = (f"FAC-{self.fecha_creacion.year}-{self.id_pedido:06d}")
           super().save(update_fields=['numero_factura'])

    def __str__(self):
       return f"{self.numero_factura} - {self.estado}"



class DetallePedidoProducto(models.Model):

    pedido = models.ForeignKey(Pedido,on_delete=models.CASCADE,related_name='productos')

    producto = models.ForeignKey(Producto,on_delete=models.PROTECT)

    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    precio_unitario = models.DecimalField(max_digits=10,decimal_places=0,validators=[MinValueValidator(0)])

    subtotal = models.DecimalField(max_digits=10,decimal_places=0,validators=[MinValueValidator(0)])

    def save(self, *args, **kwargs):

        self.precio_unitario = self.producto.precio_producto

        self.subtotal = (self.cantidad*self.precio_unitario)

        super().save(*args, **kwargs)

    

    

class DetallePedidoBebida(models.Model):

    pedido = models.ForeignKey(Pedido,on_delete=models.CASCADE,related_name='bebidas')

    bebida = models.ForeignKey(Bebida,on_delete=models.PROTECT)

    cantidad = models.PositiveIntegerField()

    precio_unitario = models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(0)])

    subtotal = models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(0)])

    def save(self, *args, **kwargs):

        self.precio_unitario = self.bebida.precio_venta#Cambiar por precio_unidad_venta

        self.subtotal = (self.cantidad *self.precio_unitario)

        super().save(*args, **kwargs)

    def __str__(self):
       return f"{self.bebida} x {self.cantidad}"

class DetallePedidoInsumo(models.Model):

    detalle_producto = models.ForeignKey(DetallePedidoProducto,on_delete=models.CASCADE, related_name='insumos')

    insumo = models.ForeignKey(Insumo,on_delete=models.PROTECT, verbose_name="Insumos Utilizados")

    cantidad_requerida = models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(1)])

    precio_insumo = models.DecimalField(max_digits=10,decimal_places=2,validators=[MinValueValidator(1)])

    usar = models.BooleanField(default=True)


    def __str__(self):
       return f"{self.insumo}"