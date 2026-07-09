from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from Inventario.models import RecetaProducto

from .models import DetallePedidoInsumo, Pedido


TRANSICIONES_VALIDAS = {
    Pedido.EstadoPedido.PENDIENTE: {Pedido.EstadoPedido.COCINA, Pedido.EstadoPedido.CANCELADO},
    Pedido.EstadoPedido.COCINA: {Pedido.EstadoPedido.COCINADO, Pedido.EstadoPedido.CANCELADO},
    Pedido.EstadoPedido.COCINADO: {Pedido.EstadoPedido.PAGADO, Pedido.EstadoPedido.CANCELADO},
    Pedido.EstadoPedido.PAGADO: {Pedido.EstadoPedido.FINALIZADO},
    Pedido.EstadoPedido.FINALIZADO: set(),
    Pedido.EstadoPedido.CANCELADO: set(),
}


def calcular_totales(pedido):
    total_productos = sum(
        (d.subtotal for d in pedido.productos.all()),
        Decimal('0'),
    )
    total_bebidas = sum(
        (d.subtotal for d in pedido.bebidas.all()),
        Decimal('0'),
    )
    return {
        'total_productos': total_productos,
        'total_bebidas': total_bebidas,
        'total': total_productos + total_bebidas,
    }


def _copiar_receta_a_detalle(detalle_producto):
    try:
        receta = detalle_producto.producto.receta
    except RecetaProducto.DoesNotExist:
        return

    for item in receta.detalles.select_related('insumo').all():
        DetallePedidoInsumo.objects.create(
            detalle_producto=detalle_producto,
            insumo=item.insumo,
            cantidad_requerida=item.cantidad_requerida,
            precio_insumo=item.insumo.precio_gramo or 0,
            usar=True,
        )


@transaction.atomic
def agregar_producto(pedido, producto, cantidad):
    if pedido.estado not in {Pedido.EstadoPedido.PENDIENTE}:
        raise ValidationError('Solo se pueden agregar productos a pedidos pendientes.')

    detalle = pedido.productos.create(producto=producto, cantidad=cantidad, precio_unitario=0, subtotal=0)
    _copiar_receta_a_detalle(detalle)
    return detalle


@transaction.atomic
def agregar_bebida(pedido, bebida, cantidad):
    if pedido.estado not in {Pedido.EstadoPedido.PENDIENTE}:
        raise ValidationError('Solo se pueden agregar bebidas a pedidos pendientes.')

    return pedido.bebidas.create(bebida=bebida, cantidad=cantidad, precio_unitario=0, subtotal=0)


@transaction.atomic
def cambiar_estado(pedido, nuevo_estado):
    if nuevo_estado not in TRANSICIONES_VALIDAS.get(pedido.estado, set()):
        raise ValidationError(
            f'No se puede pasar de "{pedido.get_estado_display()}" a "{nuevo_estado}".'
        )

    if nuevo_estado == Pedido.EstadoPedido.COCINA:
        if not pedido.productos.exists() and not pedido.bebidas.exists():
            raise ValidationError('El pedido no tiene productos ni bebidas.')

    if nuevo_estado == Pedido.EstadoPedido.PAGADO and not pedido.tipo_pago:
        raise ValidationError('Registra un tipo de pago antes de marcar como pagado.')

    pedido.estado = nuevo_estado
    pedido.full_clean()
    pedido.save()

    if nuevo_estado == Pedido.EstadoPedido.PAGADO and not pedido.inventario_descontado:
        pedido.descontar_inventario()
        pedido.inventario_descontado = True
        pedido.save(update_fields=['inventario_descontado'])

    if nuevo_estado == Pedido.EstadoPedido.FINALIZADO and pedido.mesa:
        pedido.mesa.ocupada = False
        pedido.mesa.save(update_fields=['ocupada'])

    if nuevo_estado == Pedido.EstadoPedido.CANCELADO and pedido.mesa:
        pedido.mesa.ocupada = False
        pedido.mesa.save(update_fields=['ocupada'])


@transaction.atomic
def registrar_pago(pedido, tipo_pago):
    pedido.tipo_pago = tipo_pago
    pedido.save(update_fields=['tipo_pago'])
    cambiar_estado(pedido, Pedido.EstadoPedido.PAGADO)


@transaction.atomic
def crear_pedido(mesero, datos_form):
    pedido = Pedido(mesero=mesero, **datos_form)
    pedido.full_clean()
    pedido.save()

    if pedido.mesa:
        pedido.mesa.ocupada = True
        pedido.mesa.save(update_fields=['ocupada'])

    return pedido


def eliminar_item(pedido, tipo_item, item_id):
    if pedido.estado != Pedido.EstadoPedido.PENDIENTE:
        raise ValidationError('Solo se pueden eliminar ítems de pedidos pendientes.')

    if tipo_item == 'producto':
        pedido.productos.filter(pk=item_id).delete()
    elif tipo_item == 'bebida':
        pedido.bebidas.filter(pk=item_id).delete()
    else:
        raise ValidationError('Tipo de ítem inválido.')
