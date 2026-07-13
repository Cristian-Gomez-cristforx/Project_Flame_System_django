"""Agregaciones de reportes sobre pedidos, mermas e inventario."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
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
    """Rango por defecto para los reportes: solo hoy."""
    hoy = timezone.localdate()
    return hoy, hoy


def _limites(desde: date, hasta: date):
    """Convierte un rango de fechas en datetimes con timezone (inicio y fin del día)."""
    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(desde, time.min), tz)
    fin = timezone.make_aware(datetime.combine(hasta, time.max), tz)
    return inicio, fin


def resumen_ventas(desde: date, hasta: date) -> dict:
    """Agrega ventas del rango: totales, cantidades, ticket promedio y desglose producto/bebida."""
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


def _siguiente_mes(mes: date) -> date:
    if mes.month == 12:
        return date(mes.year + 1, 1, 1)
    return date(mes.year, mes.month + 1, 1)


def _mes_anterior(mes: date) -> date:
    if mes.month == 1:
        return date(mes.year - 1, 12, 1)
    return date(mes.year, mes.month - 1, 1)


def rango_meses_por_defecto():
    """Rango por defecto: últimos 6 meses (mes actual y los 5 anteriores)."""
    hasta = timezone.localdate().replace(day=1)
    desde = hasta
    for _ in range(5):
        desde = _mes_anterior(desde)
    return desde, hasta


def ventas_por_mes(desde_mes: date = None, hasta_mes: date = None):
    """Serie mensual de ventas dentro del rango de meses (rellena con ceros los meses sin datos)."""
    if desde_mes is None or hasta_mes is None:
        desde_mes, hasta_mes = rango_meses_por_defecto()

    desde_mes = desde_mes.replace(day=1)
    hasta_mes = hasta_mes.replace(day=1)

    claves = []
    cursor = hasta_mes
    while cursor >= desde_mes:
        claves.append(cursor)
        cursor = _mes_anterior(cursor)

    tz = timezone.get_current_timezone()
    limite_inferior = timezone.make_aware(datetime.combine(desde_mes, time.min), tz)
    limite_superior = timezone.make_aware(datetime.combine(_siguiente_mes(hasta_mes), time.min), tz)

    pedidos = Pedido.objects.filter(
        estado__in=ESTADOS_INGRESO,
        fecha_creacion__gte=limite_inferior,
        fecha_creacion__lt=limite_superior,
    )

    productos_por_mes = (
        DetallePedidoProducto.objects
        .filter(pedido__in=pedidos)
        .annotate(mes=TruncMonth('pedido__fecha_creacion'))
        .values('mes')
        .annotate(total=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()))
    )
    bebidas_por_mes = (
        DetallePedidoBebida.objects
        .filter(pedido__in=pedidos)
        .annotate(mes=TruncMonth('pedido__fecha_creacion'))
        .values('mes')
        .annotate(total=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()))
    )
    pedidos_por_mes = (
        pedidos
        .annotate(mes=TruncMonth('fecha_creacion'))
        .values('mes')
        .annotate(cantidad=Count('id_pedido'))
    )
    productos_top = (
        DetallePedidoProducto.objects
        .filter(pedido__in=pedidos)
        .annotate(mes=TruncMonth('pedido__fecha_creacion'))
        .values('mes', 'producto__nombre_producto')
        .annotate(unidades=Sum('cantidad'))
        .order_by('mes', '-unidades')
    )

    resumen = {
        clave: {'cantidad': 0, 'total': Decimal('0'), 'top_producto': None}
        for clave in claves
    }

    def _clave(row_mes):
        return date(row_mes.year, row_mes.month, 1)

    for row in pedidos_por_mes:
        clave = _clave(row['mes'])
        if clave in resumen:
            resumen[clave]['cantidad'] = row['cantidad']
    for row in productos_por_mes:
        clave = _clave(row['mes'])
        if clave in resumen:
            resumen[clave]['total'] += row['total']
    for row in bebidas_por_mes:
        clave = _clave(row['mes'])
        if clave in resumen:
            resumen[clave]['total'] += row['total']
    for row in productos_top:
        clave = _clave(row['mes'])
        if clave in resumen and resumen[clave]['top_producto'] is None:
            resumen[clave]['top_producto'] = {
                'nombre': row['producto__nombre_producto'],
                'unidades': row['unidades'],
            }

    return [
        {
            'mes': clave,
            'cantidad': resumen[clave]['cantidad'],
            'total': resumen[clave]['total'],
            'top_producto': resumen[clave]['top_producto'],
        }
        for clave in claves
    ]


def producto_mas_vendido_rango(desde_mes: date, hasta_mes: date):
    """Devuelve el producto más vendido (por unidades) dentro del rango de meses, o None si no hay ventas."""
    desde_mes = desde_mes.replace(day=1)
    hasta_mes = hasta_mes.replace(day=1)

    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(desde_mes, time.min), tz)
    fin = timezone.make_aware(datetime.combine(_siguiente_mes(hasta_mes), time.min), tz)

    return (
        DetallePedidoProducto.objects
        .filter(
            pedido__fecha_creacion__gte=inicio,
            pedido__fecha_creacion__lt=fin,
            pedido__estado__in=ESTADOS_INGRESO,
        )
        .values('producto__nombre_producto')
        .annotate(
            unidades=Sum('cantidad'),
            ingresos=Coalesce(
                Sum('subtotal'),
                Value(Decimal('0')),
                output_field=DecimalField(),
            ),
        )
        .order_by('-unidades')
        .first()
    )


def top_productos(desde: date, hasta: date, limite: int = 10):
    """Ranking de productos más vendidos en el rango (por unidades)."""
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
    """Ranking de bebidas más vendidas en el rango (por unidades)."""
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
    """Devuelve los pedidos pagados/finalizados del rango, ordenados por fecha descendente."""
    inicio, fin = _limites(desde, hasta)
    pedidos = (
        Pedido.objects
        .filter(fecha_creacion__range=(inicio, fin), estado__in=ESTADOS_INGRESO)
        .order_by('-fecha_creacion')
    )
    return pedidos.select_related('mesero', 'mesa')


def resumen_mermas(desde: date, hasta: date) -> dict:
    """Agrega mermas del rango: total, costo, desglose por motivo y por insumo."""
    inicio, fin = _limites(desde, hasta)
    mermas = Merma.objects.filter(fecha_merma__range=(inicio, fin))

    total_agg = mermas.aggregate(
        costo=Coalesce(Sum('costo_total_merma'), Value(Decimal('0')), output_field=DecimalField()),
        unidades=Coalesce(Sum('cantidad_mermada'), Value(0)),
    )

    por_motivo = (
        mermas.values('motivo')
        .annotate(
            frecuencia=Count('id_merma'),
            gramos=Coalesce(
                Sum('cantidad_mermada', filter=Q(insumo__unidad_medida='g')),
                Value(0),
            ),
            unidades=Coalesce(
                Sum('cantidad_mermada', filter=Q(insumo__unidad_medida='und')),
                Value(0),
            ),
            costo=Coalesce(
                Sum('costo_total_merma'),
                Value(Decimal('0')),
                output_field=DecimalField(),
            ),
        )
        .annotate(total=F('gramos') + F('unidades'))
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
    """Clasifica los insumos según su estado: en stock ok, stock bajo o sin turno abierto."""
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
