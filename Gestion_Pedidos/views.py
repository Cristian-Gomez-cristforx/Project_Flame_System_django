from io import BytesIO

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from login_modify_django.decorators import admin_requerido, rol_requerido
from login_modify_django.models import Perfil

from . import services
from .forms import (
    AgregarBebidaForm,
    AgregarProductoForm,
    FiltroPedidosForm,
    MesaForm,
    PagoForm,
    PedidoCrearForm,
)
from .models import Mesa, Pedido


ROLES_PEDIDOS = (Perfil.Rol.ADMIN, Perfil.Rol.MESERO)
ROLES_COCINA = (Perfil.Rol.ADMIN, Perfil.Rol.COCINERO)
ROLES_TODOS = (Perfil.Rol.ADMIN, Perfil.Rol.MESERO, Perfil.Rol.COCINERO)


@rol_requerido(*ROLES_PEDIDOS)
def lista_pedidos(request):
    """Listado de pedidos con filtros por estado, tipo y búsqueda libre (últimos 100)."""
    filtro = FiltroPedidosForm(request.GET or None)
    pedidos = Pedido.objects.select_related('mesa', 'mesero').order_by('-fecha_creacion')

    if filtro.is_valid():
        estado = filtro.cleaned_data.get('estado')
        tipo = filtro.cleaned_data.get('tipo')
        q = (filtro.cleaned_data.get('q') or '').strip()

        if estado:
            pedidos = pedidos.filter(estado=estado)
        if tipo:
            pedidos = pedidos.filter(tipo=tipo)
        if q:
            pedidos = pedidos.filter(
                Q(numero_factura__icontains=q) |
                Q(nombre_cliente__icontains=q) |
                Q(telefono_cliente__icontains=q)
            )

    return render(request, 'pedidos/lista.html', {
        'pedidos': pedidos[:100],
        'filtro': filtro,
    })


@rol_requerido(*ROLES_PEDIDOS)
def crear_pedido(request):
    """Alta de un pedido nuevo; si se indicó nueva mesa la crea antes de asociarla."""
    perfil = getattr(request.user, 'perfil', None)
    puede_crear_mesa = request.user.is_superuser or bool(perfil and perfil.es_admin)
    if request.method == 'POST':
        form = PedidoCrearForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                datos = dict(form.cleaned_data)
                nueva_mesa_num = datos.pop('nueva_mesa', None)
                if (
                    datos.get('tipo') == Pedido.TipoPedido.MESA
                    and nueva_mesa_num
                    and not datos.get('mesa')
                    and puede_crear_mesa
                ):
                    datos['mesa'] = Mesa.objects.create(
                        numero_mesa=nueva_mesa_num,
                        activa=True,
                        ocupada=False,
                    )
                pedido = services.crear_pedido(request.user, datos)
                messages.success(request, f'Pedido {pedido.numero_factura} creado. Agrega productos y bebidas.')
                return redirect('pedidos:detalle', pedido_id=pedido.id_pedido)
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
    else:
        form = PedidoCrearForm(user=request.user)

    return render(request, 'pedidos/crear.html', {
        'form': form,
        'tipos': Pedido.TipoPedido.choices,
        'mesas_disponibles': Mesa.objects.filter(activa=True).order_by('numero_mesa'),
        'puede_crear_mesa': puede_crear_mesa,
    })


def _render_detalle(request, pedido, *, form_producto=None, form_bebida=None, error_accion=None, error_items=None):
    """Helper que renderiza la vista de detalle con todos sus formularios y totales."""
    totales = services.calcular_totales(pedido)
    return render(request, 'pedidos/detalle.html', {
        'pedido': pedido,
        'totales': totales,
        'form_producto': form_producto or AgregarProductoForm(pedido=pedido),
        'form_bebida': form_bebida or AgregarBebidaForm(pedido=pedido),
        'form_pago': PagoForm(instance=pedido),
        'estados': Pedido.EstadoPedido,
        'error_accion': error_accion,
        'error_items': error_items,
        'mesas_disponibles': Mesa.objects.filter(activa=True).order_by('numero_mesa'),
        'puede_cambiar_mesa': (
            pedido.tipo == Pedido.TipoPedido.MESA
            and pedido.estado in {Pedido.EstadoPedido.PENDIENTE, Pedido.EstadoPedido.COCINA, Pedido.EstadoPedido.COCINADO}
        ),
    })


def _get_pedido_detalle(pedido_id):
    """Obtiene un pedido con sus relaciones precargadas (mesa, mesero, líneas)."""
    return get_object_or_404(
        Pedido.objects.select_related('mesa', 'mesero').prefetch_related(
            'productos__producto',
            'productos__insumos__insumo',
            'bebidas__bebida',
        ),
        pk=pedido_id,
    )


@rol_requerido(*ROLES_PEDIDOS)
def detalle_pedido(request, pedido_id):
    """Vista de detalle de un pedido con sus líneas, totales y acciones disponibles."""
    pedido = _get_pedido_detalle(pedido_id)
    return _render_detalle(request, pedido)


@rol_requerido(*ROLES_PEDIDOS)
@require_POST
def agregar_producto(request, pedido_id):
    """Añade una línea de producto al pedido; delega en services.agregar_producto."""
    pedido = _get_pedido_detalle(pedido_id)
    form = AgregarProductoForm(request.POST, pedido=pedido)
    if form.is_valid():
        try:
            services.agregar_producto(
                pedido,
                form.cleaned_data['producto'],
                form.cleaned_data['cantidad'],
            )
            messages.success(request, 'Producto agregado.')
            return redirect('pedidos:detalle', pedido_id=pedido_id)
        except ValidationError as e:
            form.add_error(None, '; '.join(e.messages))
    return _render_detalle(request, pedido, form_producto=form)


@rol_requerido(*ROLES_PEDIDOS)
@require_POST
def agregar_bebida(request, pedido_id):
    """Añade una línea de bebida al pedido; delega en services.agregar_bebida."""
    pedido = _get_pedido_detalle(pedido_id)
    form = AgregarBebidaForm(request.POST, pedido=pedido)
    if form.is_valid():
        try:
            services.agregar_bebida(
                pedido,
                form.cleaned_data['bebida'],
                form.cleaned_data['cantidad'],
            )
            messages.success(request, 'Bebida agregada.')
            return redirect('pedidos:detalle', pedido_id=pedido_id)
        except ValidationError as e:
            form.add_error(None, '; '.join(e.messages))
    return _render_detalle(request, pedido, form_bebida=form)


@rol_requerido(*ROLES_PEDIDOS)
@require_POST
def eliminar_item(request, pedido_id, tipo_item, item_id):
    """Elimina una línea (producto o bebida) del pedido pendiente."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    try:
        services.eliminar_item(pedido, tipo_item, item_id)
        messages.success(request, 'Ítem eliminado.')
    except ValidationError as e:
        messages.error(request, '; '.join(e.messages))
    return redirect('pedidos:detalle', pedido_id=pedido_id)


@rol_requerido(*ROLES_PEDIDOS)
@require_POST
def editar_receta_detalle(request, pedido_id, detalle_id):
    """Actualiza qué insumos se usan en la receta de una línea de producto del pedido."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    if pedido.estado != Pedido.EstadoPedido.PENDIENTE:
        messages.error(request, 'Solo se puede modificar la receta de pedidos pendientes.')
        return redirect('pedidos:detalle', pedido_id=pedido_id)

    detalle = get_object_or_404(pedido.productos, pk=detalle_id)
    seleccionados = set(request.POST.getlist('insumo'))
    for insumo_detalle in detalle.insumos.all():
        nuevo = str(insumo_detalle.pk) in seleccionados
        if insumo_detalle.usar != nuevo:
            insumo_detalle.usar = nuevo
            insumo_detalle.save(update_fields=['usar'])

    messages.success(request, f'Receta de {detalle.producto.nombre_producto} actualizada.')
    return redirect('pedidos:detalle', pedido_id=pedido_id)


@rol_requerido(*ROLES_TODOS)
@require_POST
def cambiar_estado(request, pedido_id):
    """Solicita la transición de estado del pedido; muestra faltantes si el stock no alcanza."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    nuevo = request.POST.get('estado')
    next_url = request.POST.get('next')
    try:
        services.cambiar_estado(pedido, nuevo)
        messages.success(request, f'Pedido → {pedido.get_estado_display()}.')
        return redirect(next_url or reverse('pedidos:detalle', args=[pedido_id]))
    except ValidationError as e:
        mensajes = list(e.messages)
        if len(mensajes) > 1:
            titulo, items = mensajes[0], mensajes[1:]
        else:
            titulo, items = (mensajes[0] if mensajes else ''), None
        if next_url:
            messages.error(request, ' '.join(mensajes))
            return redirect(next_url)
        pedido = _get_pedido_detalle(pedido_id)
        return _render_detalle(request, pedido, error_accion=titulo, error_items=items)


@rol_requerido(*ROLES_PEDIDOS)
@require_POST
def cambiar_mesa(request, pedido_id):
    """Reasigna la mesa de un pedido (permite crear una mesa nueva sobre la marcha)."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)

    if pedido.tipo != Pedido.TipoPedido.MESA:
        messages.error(request, 'Este pedido no es de tipo mesa.')
        return redirect('pedidos:detalle', pedido_id=pedido_id)

    if pedido.estado in {Pedido.EstadoPedido.FINALIZADO, Pedido.EstadoPedido.CANCELADO, Pedido.EstadoPedido.PAGADO}:
        messages.error(request, 'No se puede cambiar la mesa en el estado actual del pedido.')
        return redirect('pedidos:detalle', pedido_id=pedido_id)

    nueva_pk = request.POST.get('mesa')
    nueva_num = (request.POST.get('nueva_mesa') or '').strip()

    if nueva_num:
        try:
            numero = int(nueva_num)
        except (TypeError, ValueError):
            messages.error(request, 'Número de mesa inválido.')
            return redirect('pedidos:detalle', pedido_id=pedido_id)
        if numero < 1:
            messages.error(request, 'El número de mesa debe ser mayor a 0.')
            return redirect('pedidos:detalle', pedido_id=pedido_id)
        if Mesa.objects.filter(numero_mesa=numero).exists():
            messages.error(request, f'La mesa {numero} ya existe. Selecciónala en el listado.')
            return redirect('pedidos:detalle', pedido_id=pedido_id)
        nueva = Mesa.objects.create(numero_mesa=numero, activa=True, ocupada=False)
    else:
        nueva = get_object_or_404(Mesa, pk=nueva_pk)

    if not nueva.activa:
        messages.error(request, f'La mesa {nueva.numero_mesa} está inactiva.')
        return redirect('pedidos:detalle', pedido_id=pedido_id)
    if nueva.ocupada and nueva.pk != (pedido.mesa_id or 0):
        messages.error(request, f'La mesa {nueva.numero_mesa} está ocupada.')
        return redirect('pedidos:detalle', pedido_id=pedido_id)

    mesa_anterior = pedido.mesa
    if mesa_anterior and mesa_anterior.pk == nueva.pk:
        return redirect('pedidos:detalle', pedido_id=pedido_id)

    if mesa_anterior:
        mesa_anterior.ocupada = False
        mesa_anterior.save(update_fields=['ocupada'])

    nueva.ocupada = True
    nueva.save(update_fields=['ocupada'])
    pedido.mesa = nueva
    pedido.save(update_fields=['mesa'])

    messages.success(request, f'Mesa cambiada a {nueva.numero_mesa}.')
    return redirect('pedidos:detalle', pedido_id=pedido_id)


@rol_requerido(*ROLES_PEDIDOS)
def cobrar_pedido(request, pedido_id):
    """Formulario de cobro: recoge el tipo de pago y marca el pedido como pagado."""
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    totales = services.calcular_totales(pedido)

    if request.method == 'POST':
        form = PagoForm(request.POST, instance=pedido)
        if form.is_valid():
            try:
                services.registrar_pago(pedido, form.cleaned_data['tipo_pago'])
                messages.success(request, f'Pago registrado ({pedido.get_tipo_pago_display()}).')
                return redirect('pedidos:detalle', pedido_id=pedido.id_pedido)
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
    else:
        form = PagoForm(instance=pedido)

    return render(request, 'pedidos/cobrar.html', {
        'pedido': pedido,
        'form': form,
        'totales': totales,
    })


@rol_requerido(*ROLES_PEDIDOS)
def lista_mesas(request):
    """Muestra el mapa de mesas indicando cuál tiene un pedido activo asociado."""
    perfil = getattr(request.user, 'perfil', None)
    es_admin = request.user.is_superuser or (perfil and perfil.es_admin)

    mesas_qs = Mesa.objects.all() if es_admin else Mesa.objects.filter(activa=True)
    mesas = mesas_qs.order_by('-activa', 'numero_mesa')

    activos = {
        Pedido.EstadoPedido.PENDIENTE,
        Pedido.EstadoPedido.COCINA,
        Pedido.EstadoPedido.COCINADO,
        Pedido.EstadoPedido.PAGADO,
    }
    pedidos_activos = {
        p.mesa_id: p
        for p in Pedido.objects.filter(mesa__in=mesas, estado__in=activos)
    }

    data = [
        {'mesa': mesa, 'pedido': pedidos_activos.get(mesa.id)}
        for mesa in mesas
    ]

    return render(request, 'pedidos/mesas.html', {
        'mesas_data': data,
        'es_admin': es_admin,
    })


@admin_requerido
@require_POST
def mesa_crear(request):
    """Alta de una nueva mesa desde el modal de la lista de mesas."""
    form = MesaForm(request.POST)
    if form.is_valid():
        mesa = form.save()
        messages.success(request, f'Mesa {mesa.numero_mesa} creada.')
    else:
        errores = '; '.join(f'{", ".join(v)}' for v in form.errors.values())
        messages.error(request, f'No se pudo crear la mesa. {errores}')
    return redirect('pedidos:mesas')


@admin_requerido
def mesa_editar(request, mesa_id):
    """Edita el número o el estado activo de una mesa existente."""
    mesa = get_object_or_404(Mesa, pk=mesa_id)
    if request.method == 'POST':
        form = MesaForm(request.POST, instance=mesa)
        if form.is_valid():
            form.save()
            messages.success(request, f'Mesa {mesa.numero_mesa} actualizada.')
        else:
            errores = '; '.join(f'{k}: {", ".join(v)}' for k, v in form.errors.items())
            messages.error(request, f'No se pudo actualizar la mesa. {errores}')
        return redirect('pedidos:mesas')
    form = MesaForm(instance=mesa)
    return render(request, 'pedidos/mesa_form.html', {
        'form': form,
        'modo': 'editar',
        'mesa': mesa,
    })


@admin_requerido
@require_POST
def mesa_eliminar(request, mesa_id):
    """Elimina una mesa si no tiene pedidos asociados y no está ocupada."""
    mesa = get_object_or_404(Mesa, pk=mesa_id)
    total_pedidos = mesa.pedidos.count()
    if total_pedidos > 0:
        messages.error(
            request,
            f'No se puede eliminar la Mesa {mesa.numero_mesa}: tiene {total_pedidos} pedido(s) asociado(s). '
            'Puedes desactivarla en su lugar.'
        )
    elif mesa.ocupada:
        messages.error(
            request,
            f'No se puede eliminar la Mesa {mesa.numero_mesa}: está ocupada.'
        )
    else:
        numero = mesa.numero_mesa
        mesa.delete()
        messages.success(request, f'Mesa {numero} eliminada.')
    return redirect('pedidos:mesas')


def _fmt_moneda(valor):
    """Formatea un número como moneda con separador de miles en pesos colombianos."""
    entero = int(valor or 0)
    return f'${entero:,.0f}'.replace(',', '.')


_FUENTES_FACTURA_REGISTRADAS = False


def _registrar_fuentes_factura():
    """Registra las fuentes TTF (con soporte de acentos y ñ) para el PDF de factura."""
    global _FUENTES_FACTURA_REGISTRADAS
    if _FUENTES_FACTURA_REGISTRADAS:
        return
    rutas_reg = [
        '/system/fonts/Roboto-Regular.ttf',
        '/system/fonts/DroidSans.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans.ttf',
    ]
    rutas_bold = [
        '/system/fonts/Roboto-Medium.ttf',
        '/system/fonts/DroidSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    ]
    for r in rutas_reg:
        try:
            pdfmetrics.registerFont(TTFont('FacturaBase', r))
            break
        except Exception:
            continue
    for r in rutas_bold:
        try:
            pdfmetrics.registerFont(TTFont('FacturaBold', r))
            break
        except Exception:
            continue
    _FUENTES_FACTURA_REGISTRADAS = True


def _f_base():
    """Devuelve el nombre de la fuente base para el PDF (con fallback a Helvetica)."""
    return 'FacturaBase' if 'FacturaBase' in pdfmetrics.getRegisteredFontNames() else 'Helvetica'


def _f_bold():
    """Devuelve el nombre de la fuente en negrita para el PDF (con fallback razonable)."""
    if 'FacturaBold' in pdfmetrics.getRegisteredFontNames():
        return 'FacturaBold'
    if 'FacturaBase' in pdfmetrics.getRegisteredFontNames():
        return 'FacturaBase'
    return 'Helvetica-Bold'


def _truncar(texto, ancho_max_pt, fuente, size):
    """Recorta un texto al ancho máximo indicado, agregando '…' al final si sobra."""
    if pdfmetrics.stringWidth(texto, fuente, size) <= ancho_max_pt:
        return texto
    while texto and pdfmetrics.stringWidth(texto + '…', fuente, size) > ancho_max_pt:
        texto = texto[:-1]
    return texto + '…'


@rol_requerido(*ROLES_PEDIDOS)
def factura_imagen(request, pedido_id):
    """Genera el PDF tipo ticket (80mm) del pedido y lo devuelve como descarga."""
    pedido = _get_pedido_detalle(pedido_id)

    estados_permitidos = {
        Pedido.EstadoPedido.COCINADO,
        Pedido.EstadoPedido.PAGADO,
        Pedido.EstadoPedido.FINALIZADO,
    }
    if pedido.estado not in estados_permitidos:
        messages.error(request, 'La factura solo se puede descargar cuando el pedido está cocinado.')
        return redirect('pedidos:lista')

    totales = services.calcular_totales(pedido)
    _registrar_fuentes_factura()
    fb = _f_base()
    fB = _f_bold()

    ancho = 80 * mm
    margen = 6 * mm
    ancho_util = ancho - 2 * margen

    lineas_meta = [
        ('Fecha', pedido.fecha_creacion.strftime('%d/%m/%Y %H:%M')),
        ('Tipo', pedido.get_tipo_display()),
        ('Mesero', pedido.mesero.get_username()),
    ]
    if pedido.mesa:
        lineas_meta.append(('Mesa', f'Mesa {pedido.mesa.numero_mesa}'))
    if pedido.nombre_cliente:
        lineas_meta.append(('Cliente', pedido.nombre_cliente))
    if pedido.telefono_cliente:
        lineas_meta.append(('Teléfono', pedido.telefono_cliente))
    if pedido.direccion_pedi:
        lineas_meta.append(('Dirección', pedido.direccion_pedi))
    if pedido.tipo_pago:
        lineas_meta.append(('Pago', pedido.get_tipo_pago_display()))

    productos = list(pedido.productos.all())
    bebidas = list(pedido.bebidas.all())

    alto_header = 62
    alto_factura = 30
    alto_meta = 6 + 12 * len(lineas_meta) + 8
    alto_prod = (26 + 14 * len(productos) + 6) if productos else 0
    alto_beb = (26 + 14 * len(bebidas) + 6) if bebidas else 0
    alto_total = 46
    alto_gracias = 34
    alto = 14 + alto_header + alto_factura + alto_meta + alto_prod + alto_beb + alto_total + alto_gracias

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(ancho, alto))
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)

    def y_at(offset_desde_arriba):
        return alto - offset_desde_arriba

    def linea_divisora(y_top, punteada=True, grosor=0.6):
        c.setLineWidth(grosor)
        if punteada:
            c.setDash([1.5, 1.8])
        else:
            c.setDash([])
        c.line(margen, y_at(y_top), ancho - margen, y_at(y_top))
        c.setDash([])

    cursor = 18
    c.setFont(fB, 15)
    c.drawCentredString(ancho / 2, y_at(cursor + 12), 'FLAME SYSTEM')
    cursor += 20
    c.setFont(fb, 9)
    c.drawCentredString(ancho / 2, y_at(cursor + 10), 'Comprobante de pedido')
    cursor += 22
    linea_divisora(cursor)
    cursor += 10

    c.setFont(fB, 10)
    c.drawString(margen, y_at(cursor + 10), 'FACTURA')
    c.setFont(fB, 12)
    c.drawRightString(ancho - margen, y_at(cursor + 10), pedido.numero_factura or '—')
    cursor += 20
    linea_divisora(cursor)
    cursor += 10

    for etiqueta, valor in lineas_meta:
        c.setFont(fB, 8.5)
        c.drawString(margen, y_at(cursor + 9), etiqueta)
        c.setFont(fb, 8.5)
        ancho_valor = ancho_util - pdfmetrics.stringWidth(etiqueta, fB, 8.5) - 8
        c.drawRightString(ancho - margen, y_at(cursor + 9), _truncar(str(valor), ancho_valor, fb, 8.5))
        cursor += 12
    cursor += 8

    def dibujar_seccion(titulo, items, obtener_nombre):
        nonlocal cursor
        linea_divisora(cursor)
        cursor += 8
        c.setFont(fB, 9.5)
        c.drawString(margen, y_at(cursor + 10), titulo)
        c.setFont(fb, 8)
        c.drawRightString(ancho - margen, y_at(cursor + 10), 'SUBTOTAL')
        cursor += 16
        for d in items:
            c.setFont(fB, 9)
            c.drawString(margen, y_at(cursor + 10), f'{d.cantidad}x')
            c.setFont(fb, 9)
            nombre = obtener_nombre(d)
            ancho_nombre = ancho_util - 24 - pdfmetrics.stringWidth(_fmt_moneda(d.subtotal), fB, 9) - 6
            c.drawString(margen + 20, y_at(cursor + 10), _truncar(nombre, ancho_nombre, fb, 9))
            c.setFont(fB, 9)
            c.drawRightString(ancho - margen, y_at(cursor + 10), _fmt_moneda(d.subtotal))
            cursor += 14
        cursor += 6

    if productos:
        dibujar_seccion('PRODUCTOS', productos, lambda d: d.producto.nombre_producto)
    if bebidas:
        dibujar_seccion('BEBIDAS', bebidas, lambda d: d.bebida.nombre_bebida)

    linea_divisora(cursor, punteada=False, grosor=1)
    cursor += 12

    c.setLineWidth(1)
    c.rect(margen, y_at(cursor + 30), ancho_util, 30, stroke=1, fill=0)
    c.setFont(fB, 13)
    c.drawString(margen + 10, y_at(cursor + 20), 'TOTAL')
    c.drawRightString(ancho - margen - 10, y_at(cursor + 20), _fmt_moneda(totales['total']))
    cursor += 44

    linea_divisora(cursor)
    cursor += 14
    c.setFont(fb, 9)
    c.drawCentredString(ancho / 2, y_at(cursor + 10), '¡Gracias por su compra!')

    c.showPage()
    c.save()

    nombre = f'{pedido.numero_factura or f"pedido-{pedido.id_pedido}"}.pdf'
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response


@rol_requerido(*ROLES_COCINA)
def cocina(request):
    """Tablero de cocina con los pedidos ya enviados a cocina (no muestra los pendientes)."""
    pedidos = (
        Pedido.objects
        .filter(estado=Pedido.EstadoPedido.COCINA)
        .select_related('mesa')
        .prefetch_related('productos__producto', 'bebidas__bebida')
        .order_by('fecha_creacion')
    )
    return render(request, 'pedidos/cocina.html', {
        'pedidos': pedidos,
        'estados': Pedido.EstadoPedido,
    })
