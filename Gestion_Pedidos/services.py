from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from Inventario.models import Bebida, Insumo, RecetaProducto

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


def _consumo_por_insumo(pedido):
    consumo = defaultdict(lambda: Decimal('0'))
    detalles = (
        pedido.productos
        .prefetch_related('insumos__insumo')
        .all()
    )
    for detalle_producto in detalles:
        for detalle_insumo in detalle_producto.insumos.all():
            if not detalle_insumo.usar:
                continue
            consumo[detalle_insumo.insumo_id] += (
                Decimal(detalle_insumo.cantidad_requerida) * detalle_producto.cantidad
            )
    return dict(consumo)


def _consumo_por_bebida(pedido):
    consumo = defaultdict(int)
    for detalle_bebida in pedido.bebidas.all():
        consumo[detalle_bebida.bebida_id] += detalle_bebida.cantidad
    return dict(consumo)


def _fmt_cantidad(n):
    d = Decimal(n)
    if d == d.to_integral_value():
        return str(int(d))
    return format(d.normalize(), 'f')


def _validar_stock_suficiente(pedido):
    consumo_insumo = _consumo_por_insumo(pedido)
    consumo_bebida = _consumo_por_bebida(pedido)

    faltantes = []

    if consumo_insumo:
        for insumo in Insumo.objects.filter(pk__in=consumo_insumo.keys()):
            requerido = consumo_insumo[insumo.pk]
            if requerido > insumo.cantidad_insumo:
                unidad = insumo.unidad_medida
                faltantes.append(
                    f'{insumo.nombre_insumo}: se requieren {_fmt_cantidad(requerido)}{unidad}, hay {insumo.cantidad_insumo}{unidad}'
                )

    if consumo_bebida:
        for bebida in Bebida.objects.filter(pk__in=consumo_bebida.keys()):
            requerido = consumo_bebida[bebida.pk]
            if requerido > bebida.cantidad_bebida:
                faltantes.append(
                    f'{bebida.nombre_bebida}: se requieren {_fmt_cantidad(requerido)}und, hay {bebida.cantidad_bebida}und'
                )

    if faltantes:
        raise ValidationError(
            ['Stock insuficiente para enviar a cocina:'] + faltantes
        )


def _descontar_stock(pedido):
    for insumo_id, cantidad in _consumo_por_insumo(pedido).items():
        Insumo.objects.filter(pk=insumo_id).update(
            cantidad_insumo=F('cantidad_insumo') - cantidad,
        )
    for bebida_id, cantidad in _consumo_por_bebida(pedido).items():
        Bebida.objects.filter(pk=bebida_id).update(
            cantidad_bebida=F('cantidad_bebida') - cantidad,
        )


def _restaurar_stock(pedido):
    for insumo_id, cantidad in _consumo_por_insumo(pedido).items():
        Insumo.objects.filter(pk=insumo_id).update(
            cantidad_insumo=F('cantidad_insumo') + cantidad,
        )
    for bebida_id, cantidad in _consumo_por_bebida(pedido).items():
        Bebida.objects.filter(pk=bebida_id).update(
            cantidad_bebida=F('cantidad_bebida') + cantidad,
        )


@transaction.atomic
def cambiar_estado(pedido, nuevo_estado):
    if nuevo_estado not in TRANSICIONES_VALIDAS.get(pedido.estado, set()):
        raise ValidationError(
            f'No se puede pasar de "{pedido.get_estado_display()}" a "{nuevo_estado}".'
        )

    if nuevo_estado == Pedido.EstadoPedido.COCINA:
        if not pedido.productos.exists() and not pedido.bebidas.exists():
            raise ValidationError('El pedido no tiene productos ni bebidas.')
        if not pedido.inventario_descontado:
            _validar_stock_suficiente(pedido)

    if nuevo_estado == Pedido.EstadoPedido.PAGADO and not pedido.tipo_pago:
        raise ValidationError('Registra un tipo de pago antes de marcar como pagado.')

    pedido.estado = nuevo_estado
    pedido.full_clean()
    pedido.save()

    if nuevo_estado == Pedido.EstadoPedido.COCINA and not pedido.inventario_descontado:
        _descontar_stock(pedido)
        pedido.inventario_descontado = True
        pedido.save(update_fields=['inventario_descontado'])

    if nuevo_estado == Pedido.EstadoPedido.FINALIZADO and pedido.mesa:
        pedido.mesa.ocupada = False
        pedido.mesa.save(update_fields=['ocupada'])

    if nuevo_estado == Pedido.EstadoPedido.CANCELADO:
        if pedido.mesa:
            pedido.mesa.ocupada = False
            pedido.mesa.save(update_fields=['ocupada'])
        if pedido.inventario_descontado:
            _restaurar_stock(pedido)
            pedido.inventario_descontado = False
            pedido.save(update_fields=['inventario_descontado'])


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
