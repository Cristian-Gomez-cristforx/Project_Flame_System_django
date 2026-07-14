from datetime import datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.utils import timezone

from login_modify_django.decorators import admin_requerido

from Gestion_Pedidos.models import Pedido

from . import services
from .forms import FiltroPedidosReporteForm, RangoFechasForm, RangoMesesForm


_LOGO_FADEADO_CACHE = None


def _logo_marca_agua():
    """Devuelve un ImageReader del logo con opacidad reducida (cacheado)."""
    global _LOGO_FADEADO_CACHE
    if _LOGO_FADEADO_CACHE is not None:
        return _LOGO_FADEADO_CACHE

    from PIL import Image as PILImage
    from reportlab.lib.utils import ImageReader

    ruta = Path(settings.MEDIA_ROOT) / 'admin-interface' / 'favicon' / 'favicon_mejorado.png'
    if not ruta.exists():
        return None

    img = PILImage.open(ruta).convert('RGBA')
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * 0.08))
    img.putalpha(a)

    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    _LOGO_FADEADO_CACHE = ImageReader(buf)
    return _LOGO_FADEADO_CACHE


def _rango_desde_request(request):
    """Extrae desde/hasta de la request o devuelve el rango por defecto (últimos 7 días)."""
    form = RangoFechasForm(request.GET or None)
    if request.GET and form.is_valid():
        return form.cleaned_data['desde'], form.cleaned_data['hasta'], form

    desde, hasta = services.rango_por_defecto()
    if not request.GET:
        form = RangoFechasForm(initial={'desde': desde, 'hasta': hasta})
    return desde, hasta, form


@admin_requerido
def dashboard(request):
    """Reporte de pedidos: tabla filtrable por fechas, estado, tipo y cliente."""
    hoy = timezone.localdate()
    tz = timezone.get_current_timezone()

    ESTADOS_DEFAULT = [Pedido.EstadoPedido.FINALIZADO, Pedido.EstadoPedido.CANCELADO]

    filtrado = bool(request.GET)
    if filtrado:
        form = FiltroPedidosReporteForm(request.GET)
    else:
        form = FiltroPedidosReporteForm(initial={'desde': hoy, 'hasta': hoy})

    pedidos_qs = (
        Pedido.objects
        .select_related('mesa', 'mesero')
        .order_by('-fecha_creacion')
    )

    if filtrado and form.is_valid():
        cd = form.cleaned_data
        desde = cd.get('desde') or hoy
        hasta = cd.get('hasta') or hoy
    else:
        desde = hasta = hoy

    inicio = timezone.make_aware(datetime.combine(desde, datetime.min.time()), tz)
    fin = timezone.make_aware(datetime.combine(hasta, datetime.max.time()), tz)
    pedidos_qs = pedidos_qs.filter(fecha_creacion__range=(inicio, fin))

    if filtrado and form.is_valid():
        cd = form.cleaned_data
        if cd.get('estado'):
            pedidos_qs = pedidos_qs.filter(estado=cd['estado'])
        else:
            pedidos_qs = pedidos_qs.filter(estado__in=ESTADOS_DEFAULT)
        if cd.get('tipo'):
            pedidos_qs = pedidos_qs.filter(tipo=cd['tipo'])
        if cd.get('q'):
            from django.db.models import Q
            q = cd['q']
            pedidos_qs = pedidos_qs.filter(
                Q(nombre_cliente__icontains=q)
                | Q(numero_factura__icontains=q)
                | Q(mesero__username__icontains=q)
                | Q(mesero__first_name__icontains=q)
                | Q(mesero__last_name__icontains=q)
            )
    else:
        pedidos_qs = pedidos_qs.filter(estado__in=ESTADOS_DEFAULT)

    return render(request, 'reportes/dashboard.html', {
        'form': form,
        'pedidos': pedidos_qs,
        'filtrado': filtrado,
    })


@admin_requerido
def ventas(request):
    """Reporte de ventas: reutiliza el contexto del dashboard de inicio pero con su propia sección/plantilla."""
    from login_modify_django.views import construir_contexto_dashboard
    return render(request, 'reportes/ventas.html', construir_contexto_dashboard(request))


@admin_requerido
def mermas(request):
    """Reporte de mermas del rango: totales, desglose por motivo y por insumo."""
    desde, hasta, form = _rango_desde_request(request)
    resumen = services.resumen_mermas(desde, hasta)

    return render(request, 'reportes/mermas.html', {
        'form': form,
        'resumen': resumen,
    })


@admin_requerido
def estabilidad(request):
    """Reporte de estabilidad: serie mensual de ventas y producto más vendido dentro del rango de meses."""
    desde_defecto, hasta_defecto = services.rango_meses_por_defecto()

    filtrado = bool(request.GET.get('desde_mes') or request.GET.get('hasta_mes'))
    form = RangoMesesForm(request.GET or None)
    if filtrado and form.is_valid():
        desde_mes = form.cleaned_data['desde_mes']
        hasta_mes = form.cleaned_data['hasta_mes']
    else:
        desde_mes, hasta_mes = desde_defecto, hasta_defecto
        if not filtrado:
            form = RangoMesesForm(initial={
                'desde_mes': desde_defecto.strftime('%Y-%m'),
                'hasta_mes': hasta_defecto.strftime('%Y-%m'),
            })

    return render(request, 'reportes/estabilidad.html', {
        'form': form,
        'ventas_mensuales': services.ventas_por_mes(desde_mes, hasta_mes),
        'producto_top': services.producto_mas_vendido_rango(desde_mes, hasta_mes),
        'desde_mes': desde_mes,
        'hasta_mes': hasta_mes,
        'filtrado': filtrado,
    })


MESES_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']


def _fecha_larga(d):
    """Convierte una fecha a texto largo en español (ej: '12 de julio 2026')."""
    return f'{d.day} de {MESES_ES[d.month - 1]} {d.year}'


def _fmt_moneda(valor):
    """Formatea un número como moneda con separador de miles en pesos colombianos."""
    entero = int(valor or 0)
    return f'${entero:,.0f}'.replace(',', '.')


@admin_requerido
def descargar_reporte_pedidos(request):
    """Genera un PDF A4 con el listado completo de pedidos del rango y lo devuelve como descarga."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as canvas_mod
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    desde_str = request.GET.get('desde')
    hasta_str = request.GET.get('hasta')

    if not desde_str or not hasta_str:
        return HttpResponseBadRequest('Faltan fechas.')

    try:
        desde = datetime.strptime(desde_str, '%Y-%m-%d').date()
        hasta = datetime.strptime(hasta_str, '%Y-%m-%d').date()
    except ValueError:
        return HttpResponseBadRequest('Fechas inválidas.')

    hoy = timezone.localdate()
    if desde > hoy or hasta > hoy:
        return HttpResponseBadRequest('Las fechas no pueden ser posteriores a hoy.')
    if desde > hasta:
        return HttpResponseBadRequest('La fecha "Desde" no puede ser posterior a "Hasta".')

    tz = timezone.get_current_timezone()
    inicio = timezone.make_aware(datetime.combine(desde, datetime.min.time()), tz)
    fin = timezone.make_aware(datetime.combine(hasta, datetime.max.time()), tz)

    pedidos = list(
        Pedido.objects
        .filter(fecha_creacion__range=(inicio, fin), estado__in=[Pedido.EstadoPedido.FINALIZADO, Pedido.EstadoPedido.CANCELADO])
        .select_related('mesa', 'mesero')
        .prefetch_related('productos', 'bebidas')
        .order_by('-fecha_creacion')
    )

    buffer = BytesIO()

    TEXTO = colors.HexColor('#2B2320')
    GRIS = colors.HexColor('#7A6D64')
    BORDE = colors.HexColor('#E5DDD4')
    ACENTO = colors.HexColor('#D9480F')
    ACENTO_OSCURO = colors.HexColor('#B83A08')
    FONDO_ALT = colors.HexColor('#FAF6F1')

    logo = _logo_marca_agua()

    def _footer(canv, doc_):
        canv.saveState()
        if logo is not None:
            tamano = 110 * mm
            x = (A4[0] - tamano) / 2
            y = (A4[1] - tamano) / 2
            canv.drawImage(logo, x, y, width=tamano, height=tamano, mask='auto')
        canv.setFont('Times-Italic', 8)
        canv.setFillColor(GRIS)
        pagina = canv.getPageNumber()
        canv.drawCentredString(A4[0] / 2, 12 * mm, f'Página {pagina}')
        canv.drawString(20 * mm, 12 * mm, 'Flame System')
        canv.drawRightString(A4[0] - 20 * mm, 12 * mm,
                             timezone.localtime().strftime('%d/%m/%Y %H:%M'))
        canv.setStrokeColor(BORDE)
        canv.setLineWidth(0.5)
        canv.line(20 * mm, 16 * mm, A4[0] - 20 * mm, 16 * mm)
        canv.restoreState()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title='Reporte de pedidos - Flame System',
        author='Flame System',
    )

    estilos = getSampleStyleSheet()
    estilo_titulo = ParagraphStyle(
        'titulo', parent=estilos['Heading1'],
        alignment=TA_CENTER, textColor=ACENTO,
        fontName='Times-Bold', fontSize=22, leading=26, spaceAfter=2,
    )
    estilo_subtitulo = ParagraphStyle(
        'subtitulo', parent=estilos['Normal'],
        alignment=TA_CENTER, textColor=GRIS,
        fontName='Times-Italic', fontSize=12, leading=14, spaceAfter=14,
    )
    estilo_h2 = ParagraphStyle(
        'h2', parent=estilos['Heading2'],
        textColor=ACENTO_OSCURO, fontName='Times-Bold',
        fontSize=13, leading=16, spaceBefore=10, spaceAfter=6,
    )
    estilo_parrafo = ParagraphStyle(
        'parrafo', parent=estilos['Normal'],
        fontName='Times-Roman', fontSize=11, leading=14,
        alignment=TA_JUSTIFY, textColor=TEXTO, spaceAfter=4,
    )
    estilo_items = ParagraphStyle(
        'items', parent=estilos['Normal'],
        fontName='Times-Roman', fontSize=8, leading=10, textColor=TEXTO,
    )
    estilo_celda = ParagraphStyle(
        'celda', parent=estilos['Normal'],
        fontName='Times-Roman', fontSize=8.5, leading=10.5, textColor=TEXTO,
        alignment=TA_LEFT,
    )
    estilo_items_total = ParagraphStyle(
        'items_total', parent=estilos['Normal'],
        fontName='Times-Bold', fontSize=8, leading=10, textColor=ACENTO_OSCURO,
    )
    estilo_pie = ParagraphStyle(
        'pie', parent=estilos['Normal'],
        fontName='Times-Italic', fontSize=9, textColor=GRIS,
        alignment=TA_CENTER, spaceBefore=20,
    )

    elementos = []
    elementos.append(Paragraph('Reporte de pedidos', estilo_titulo))
    elementos.append(Paragraph(
        f'Desde <b>{_fecha_larga(desde)}</b> hasta <b>{_fecha_larga(hasta)}</b>',
        estilo_subtitulo,
    ))
    elementos.append(Paragraph(
        f'Generado el {timezone.localtime().strftime("%d/%m/%Y a las %H:%M")}',
        estilo_subtitulo,
    ))
    elementos.append(HRFlowable(width='100%', thickness=0.75, color=ACENTO, spaceAfter=10))


    total_ingresos = Decimal('0')
    total_items = 0
    filas = []
    for p in pedidos:
        subtotal_pedido = Decimal('0')
        items_pedido = 0
        detalle_lineas = []

        for d in p.productos.all():
            detalle_lineas.append(
                f'{d.cantidad}× {d.producto.nombre_producto} — {_fmt_moneda(d.subtotal)}'
            )
            subtotal_pedido += Decimal(d.subtotal)
            items_pedido += d.cantidad

        for d in p.bebidas.all():
            detalle_lineas.append(
                f'{d.cantidad}× {d.bebida.nombre_bebida} — {_fmt_moneda(d.subtotal)}'
            )
            subtotal_pedido += Decimal(d.subtotal)
            items_pedido += d.cantidad

        if p.estado in (Pedido.EstadoPedido.PAGADO, Pedido.EstadoPedido.FINALIZADO):
            total_ingresos += subtotal_pedido
        total_items += items_pedido

        if detalle_lineas:
            detalle_html = '<br/>'.join(detalle_lineas)
        else:
            detalle_html = '<i>Sin ítems</i>'

        cliente = f'Mesa {p.mesa.numero_mesa}' if p.mesa else (p.nombre_cliente or '—')
        fecha_local = timezone.localtime(p.fecha_creacion)
        fecha_html = f'{fecha_local.strftime("%d/%m/%Y")}<br/>{fecha_local.strftime("%H:%M")}'
        filas.append([
            Paragraph(p.numero_factura or f'#{p.id_pedido}', estilo_celda),
            Paragraph(fecha_html, estilo_celda),
            p.get_tipo_display(),
            Paragraph(cliente, estilo_celda),
            Paragraph(p.mesero.get_username(), estilo_celda),
            Paragraph(detalle_html, estilo_items),
            _fmt_moneda(subtotal_pedido),
        ])

    elementos.append(Paragraph('Resumen general del periodo', estilo_h2))
    resumen_data = [
        ['Total de pedidos', str(len(pedidos))],
        ['Ítems totales vendidos', str(total_items)],
        ['Ingresos (pagados / finalizados)', _fmt_moneda(total_ingresos)],
    ]
    tabla_resumen = Table(resumen_data, colWidths=[110 * mm, 60 * mm], hAlign='LEFT')
    tabla_resumen.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),
        ('FONTNAME', (0, 0), (0, -1), 'Times-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), TEXTO),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 0.75, ACENTO),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, BORDE),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elementos.append(tabla_resumen)

    elementos.append(Paragraph('Detalle de pedidos', estilo_h2))

    if not filas:
        elementos.append(Paragraph(
            'No se encontraron pedidos registrados dentro del período seleccionado.',
            estilo_parrafo,
        ))
    else:
        encabezados = ['Factura', 'Fecha', 'Tipo', 'Cliente / Mesa',
                       'Mesero', 'Ítems', 'Total']
        data = [encabezados] + filas
        tabla = Table(data, repeatRows=1, colWidths=[
            26 * mm, 20 * mm, 16 * mm, 24 * mm,
            22 * mm, 42 * mm, 20 * mm,
        ])
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ACENTO),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('VALIGN', (5, 1), (5, -1), 'TOP'),
            ('FONTNAME', (0, 1), (-1, -1), 'Times-Roman'),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXTO),
            ('LINEBELOW', (0, 0), (-1, 0), 0.75, ACENTO_OSCURO),
            ('LINEBELOW', (0, 1), (-1, -1), 0.25, BORDE),
            ('BOX', (0, 0), (-1, -1), 0.5, ACENTO),
            ('ALIGN', (6, 1), (6, -1), 'RIGHT'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla)

        elementos.append(Spacer(1, 8))
        total_general = Table(
            [['TOTAL GENERAL', _fmt_moneda(total_ingresos)]],
            colWidths=[130 * mm, 40 * mm], hAlign='RIGHT',
        )
        total_general.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), ACENTO),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
            ('FONTNAME', (0, 0), (-1, -1), 'Times-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elementos.append(total_general)

    elementos.append(Paragraph(
        '— Fin del reporte —',
        estilo_pie,
    ))

    doc.build(elementos, onFirstPage=_footer, onLaterPages=_footer)
    buffer.seek(0)

    nombre = f'reporte-pedidos-{desde.isoformat()}-a-{hasta.isoformat()}.pdf'
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response


def services_totales_pedido(pedido):
    """Calcula el total y las unidades vendidas de un solo pedido (helper puntual)."""
    total = Decimal('0')
    unidades = 0
    for d in pedido.productos.all():
        total += Decimal(d.subtotal)
        unidades += d.cantidad
    for d in pedido.bebidas.all():
        total += Decimal(d.subtotal)
        unidades += d.cantidad
    return {'total': total, 'unidades': unidades}
