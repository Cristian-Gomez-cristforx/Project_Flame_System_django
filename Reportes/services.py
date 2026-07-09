"""Agregaciones de reportes sobre pedidos, mermas e inventario."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from Gestion_Pedidos.models import (
    DetallePedidoBebida,
    DetallePedidoProducto,
    Pedido,
)
from Inventario.models import Insumo, Merma


ESTADOS_INGRESO = [
    Pedido.EstadoPedido.PAGADO,
    Pedido.EstadoPedido.FINALIZADO,
]


def rango_por_defecto():
    hoy = timezone.localdate()
    return hoy - timedelta(days=6), hoy


def _limites(desde: date, hasta: date):
    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(desde, time.min), tz)
    fin = timezone.make_aware(datetime.combine(hasta, time.max), tz)
    return inicio, fin


def resumen_ventas(desde: date, hasta: date) -> dict:
    inicio, fin = _limites(desde, hasta)
    pedidos = Pedido.objects.filter(
        fecha_creacion__range=(inicio, fin),
        estado__in=ESTADOS_INGRESO,
    )

    productos_agg = DetallePedidoProducto.objects.filter(pedido__in=pedidos).aggregate(
        total=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()),
        unidades=Coalesce(Sum('cantidad'), Value(0)),
    )
    bebidas_agg = DetallePedidoBebida.objects.filter(pedido__in=pedidos).aggregate(
        total=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()),
        unidades=Coalesce(Sum('cantidad'), Value(0)),
    )

    total_pedidos = pedidos.count()
    total_ingresos = productos_agg['total'] + bebidas_agg['total']
    ticket_promedio = (total_ingresos / total_pedidos) if total_pedidos else Decimal('0')

    return {
        'desde': desde,
        'hasta': hasta,
        'total_pedidos': total_pedidos,
        'total_ingresos': total_ingresos,
        'total_productos': productos_agg['total'],
        'total_bebidas': bebidas_agg['total'],
        'unidades_productos': productos_agg['unidades'],
        'unidades_bebidas': bebidas_agg['unidades'],
        'ticket_promedio': ticket_promedio,
    }


def top_productos(desde: date, hasta: date, limite: int = 10):
    inicio, fin = _limites(desde, hasta)
    return (
        DetallePedidoProducto.objects
        .filter(
            pedido__fecha_creacion__range=(inicio, fin),
            pedido__estado__in=ESTADOS_INGRESO,
        )
        .values('producto__nombre_producto')
        .annotate(
            unidades=Sum('cantidad'),
            ingresos=Sum('subtotal'),
        )
        .order_by('-unidades')[:limite]
    )


def top_bebidas(desde: date, hasta: date, limite: int = 10):
    inicio, fin = _limites(desde, hasta)
    return (
        DetallePedidoBebida.objects
        .filter(
            pedido__fecha_creacion__range=(inicio, fin),
            pedido__estado__in=ESTADOS_INGRESO,
        )
        .values('bebida__nombre_bebida', 'bebida__tamaño_bebida')
        .annotate(
            unidades=Sum('cantidad'),
            ingresos=Sum('subtotal'),
        )
        .order_by('-unidades')[:limite]
    )


def pedidos_por_dia(desde: date, hasta: date):
    inicio, fin = _limites(desde, hasta)
    pedidos = (
        Pedido.objects
        .filter(fecha_creacion__range=(inicio, fin), estado__in=ESTADOS_INGRESO)
        .order_by('-fecha_creacion')
    )
    return pedidos.select_related('mesero', 'mesa')


def resumen_mermas(desde: date, hasta: date) -> dict:
    inicio, fin = _limites(desde, hasta)
    mermas = Merma.objects.filter(fecha_merma__range=(inicio, fin))

    total_agg = mermas.aggregate(
        costo=Coalesce(Sum('costo_total_merma'), Value(Decimal('0')), output_field=DecimalField()),
        unidades=Coalesce(Sum('cantidad_mermada'), Value(0)),
    )

    por_motivo = (
        mermas.values('motivo')
        .annotate(costo=Sum('costo_total_merma'), unidades=Sum('cantidad_mermada'))
        .order_by('-costo')
    )

    por_insumo = (
        mermas.values('insumo__nombre_insumo')
        .annotate(costo=Sum('costo_total_merma'), unidades=Sum('cantidad_mermada'))
        .order_by('-costo')[:10]
    )

    return {
        'desde': desde,
        'hasta': hasta,
        'total_registros': mermas.count(),
        'total_costo': total_agg['costo'],
        'total_unidades': total_agg['unidades'],
        'por_motivo': list(por_motivo),
        'por_insumo': list(por_insumo),
        'detalle': mermas.select_related('insumo').order_by('-fecha_merma'),
    }


def estado_inventario():
    insumos = list(Insumo.objects.select_related('categoria').order_by('nombre_insumo'))
    stock_bajo = [i for i in insumos if i.stock_maximo > 0 and i.bajo_stock_30]
    sin_turno = [i for i in insumos if i.stock_maximo == 0]
    ok = [i for i in insumos if i.stock_maximo > 0 and not i.bajo_stock_30]

    return {
        'total_insumos': len(insumos),
        'stock_bajo': stock_bajo,
        'sin_turno': sin_turno,
        'ok': ok,
    }
