from io import BytesIO

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from PIL import Image, ImageDraw, ImageFont

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
    if request.method == 'POST':
        form = PedidoCrearForm(request.POST)
        if form.is_valid():
            try:
                datos = dict(form.cleaned_data)
                nueva_mesa_num = datos.pop('nueva_mesa', None)
                if (
                    datos.get('tipo') == Pedido.TipoPedido.MESA
                    and nueva_mesa_num
                    and not datos.get('mesa')
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
        form = PedidoCrearForm()

    return render(request, 'pedidos/crear.html', {
        'form': form,
        'tipos': Pedido.TipoPedido.choices,
        'mesas_disponibles': Mesa.objects.filter(activa=True).order_by('numero_mesa'),
    })


def _render_detalle(request, pedido, *, form_producto=None, form_bebida=None, error_accion=None, error_items=None):
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
    return get_object_or_404(
        Pedido.objects.select_related('mesa', 'mesero').prefetch_related('productos__producto', 'bebidas__bebida'),
        pk=pedido_id,
    )


@rol_requerido(*ROLES_PEDIDOS)
def detalle_pedido(request, pedido_id):
    pedido = _get_pedido_detalle(pedido_id)
    return _render_detalle(request, pedido)


@rol_requerido(*ROLES_PEDIDOS)
@require_POST
def agregar_producto(request, pedido_id):
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
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    try:
        services.eliminar_item(pedido, tipo_item, item_id)
        messages.success(request, 'Ítem eliminado.')
    except ValidationError as e:
        messages.error(request, '; '.join(e.messages))
    return redirect('pedidos:detalle', pedido_id=pedido_id)


@rol_requerido(*ROLES_TODOS)
@require_POST
def cambiar_estado(request, pedido_id):
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
def mesa_crear(request):
    form = MesaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        mesa = form.save()
        messages.success(request, f'Mesa {mesa.numero_mesa} creada.')
        return redirect('pedidos:mesas')
    return render(request, 'pedidos/mesa_form.html', {
        'form': form,
        'modo': 'crear',
    })


@admin_requerido
def mesa_editar(request, mesa_id):
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
    entero = int(valor or 0)
    return f'${entero:,.0f}'.replace(',', '.')


_FUENTES_TTF = [
    '/system/fonts/Roboto-Regular.ttf',
    '/system/fonts/DroidSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/dejavu/DejaVuSans.ttf',
]
_FUENTES_TTF_BOLD = [
    '/system/fonts/Roboto-Medium.ttf',
    '/system/fonts/DroidSans-Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
]


def _cargar_fuente(rutas, size):
    for ruta in rutas:
        try:
            return ImageFont.truetype(ruta, size=size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


@rol_requerido(*ROLES_PEDIDOS)
def factura_imagen(request, pedido_id):
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

    ancho = 560
    margen_x = 36

    fuente_marca = _cargar_fuente(_FUENTES_TTF_BOLD, 30)
    fuente_titulo = _cargar_fuente(_FUENTES_TTF_BOLD, 22)
    fuente_sub = _cargar_fuente(_FUENTES_TTF, 14)
    fuente_seccion = _cargar_fuente(_FUENTES_TTF_BOLD, 14)
    fuente_bold = _cargar_fuente(_FUENTES_TTF_BOLD, 13)
    fuente = _cargar_fuente(_FUENTES_TTF, 13)
    fuente_pequena = _cargar_fuente(_FUENTES_TTF, 11)

    color_primario = (231, 76, 60)
    color_texto = (33, 37, 41)
    color_gris = (108, 117, 125)
    color_linea = (222, 226, 230)
    color_fondo_alt = (248, 249, 250)

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

    alto_header = 110
    alto_factura = 46
    alto_meta = 20 + 22 * len(lineas_meta) + 16
    alto_productos = (34 + 26 * len(productos) + 12) if productos else 0
    alto_bebidas = (34 + 26 * len(bebidas) + 12) if bebidas else 0
    alto_total = 70
    alto_footer = 60

    alto = alto_header + alto_factura + alto_meta + alto_productos + alto_bebidas + alto_total + alto_footer

    img = Image.new('RGB', (ancho, alto), 'white')
    draw = ImageDraw.Draw(img)

    draw.rectangle([(0, 0), (ancho, alto_header)], fill=color_primario)
    draw.text((ancho // 2, 30), 'FLAME SYSTEM', font=fuente_marca, fill='white', anchor='mt')
    draw.text((ancho // 2, 68), 'Comprobante de pedido', font=fuente_sub, fill=(255, 235, 230), anchor='mt')

    y = alto_header + 14
    draw.rectangle([(margen_x, y), (ancho - margen_x, y + 32)], fill=color_fondo_alt)
    draw.text((margen_x + 12, y + 16), 'FACTURA', font=fuente_bold, fill=color_gris, anchor='lm')
    draw.text((ancho - margen_x - 12, y + 16), pedido.numero_factura or '—',
              font=fuente_titulo, fill=color_primario, anchor='rm')
    y += 46

    for etiqueta, valor in lineas_meta:
        draw.text((margen_x, y), etiqueta, font=fuente_bold, fill=color_gris)
        draw.text((ancho - margen_x, y), str(valor), font=fuente, fill=color_texto, anchor='rt')
        y += 22
    y += 12

    def _dibujar_seccion(titulo, items, obtener_nombre):
        nonlocal y
        draw.line([(margen_x, y), (ancho - margen_x, y)], fill=color_linea, width=1)
        y += 10
        draw.text((margen_x, y), titulo, font=fuente_seccion, fill=color_primario)
        draw.text((ancho - margen_x, y), 'SUBTOTAL', font=fuente_pequena, fill=color_gris, anchor='rt')
        y += 22
        for idx, d in enumerate(items):
            if idx % 2 == 1:
                draw.rectangle(
                    [(margen_x - 6, y - 4), (ancho - margen_x + 6, y + 20)],
                    fill=color_fondo_alt,
                )
            draw.text((margen_x, y), f'{d.cantidad}x', font=fuente_bold, fill=color_texto)
            draw.text((margen_x + 34, y), obtener_nombre(d), font=fuente, fill=color_texto)
            draw.text((ancho - margen_x, y), _fmt_moneda(d.subtotal), font=fuente_bold, fill=color_texto, anchor='rt')
            y += 26
        y += 8

    if productos:
        _dibujar_seccion('PRODUCTOS', productos, lambda d: d.producto.nombre_producto)

    if bebidas:
        _dibujar_seccion('BEBIDAS', bebidas, lambda d: d.bebida.nombre_bebida)

    draw.line([(margen_x, y), (ancho - margen_x, y)], fill=color_texto, width=2)
    y += 14
    draw.rectangle(
        [(margen_x, y), (ancho - margen_x, y + 44)],
        fill=color_primario,
    )
    draw.text((margen_x + 16, y + 22), 'TOTAL', font=fuente_titulo, fill='white', anchor='lm')
    draw.text((ancho - margen_x - 16, y + 22), _fmt_moneda(totales['total']),
              font=fuente_titulo, fill='white', anchor='rm')
    y += 60

    draw.text((ancho // 2, y), '¡Gracias por su compra!', font=fuente_sub, fill=color_texto, anchor='mt')

    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    nombre = f'{pedido.numero_factura or f"pedido-{pedido.id_pedido}"}.png'
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="{nombre}"'
    return response


@rol_requerido(*ROLES_COCINA)
def cocina(request):
    pedidos = (
        Pedido.objects
        .filter(estado__in=[Pedido.EstadoPedido.PENDIENTE, Pedido.EstadoPedido.COCINA])
        .select_related('mesa')
        .prefetch_related('productos__producto', 'bebidas__bebida')
        .order_by('fecha_creacion')
    )
    return render(request, 'pedidos/cocina.html', {
        'pedidos': pedidos,
        'estados': Pedido.EstadoPedido,
    })
