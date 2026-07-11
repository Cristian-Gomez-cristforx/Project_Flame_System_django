from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

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
        'mesas_libres': Mesa.objects.filter(activa=True, ocupada=False).order_by('numero_mesa'),
    })


def _render_detalle(request, pedido, *, form_producto=None, form_bebida=None, error_accion=None):
    totales = services.calcular_totales(pedido)
    return render(request, 'pedidos/detalle.html', {
        'pedido': pedido,
        'totales': totales,
        'form_producto': form_producto or AgregarProductoForm(),
        'form_bebida': form_bebida or AgregarBebidaForm(),
        'form_pago': PagoForm(instance=pedido),
        'estados': Pedido.EstadoPedido,
        'error_accion': error_accion,
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
    form = AgregarProductoForm(request.POST)
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
    form = AgregarBebidaForm(request.POST)
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
        error = '; '.join(e.messages)
        if next_url:
            messages.error(request, error)
            return redirect(next_url)
        pedido = _get_pedido_detalle(pedido_id)
        return _render_detalle(request, pedido, error_accion=error)


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
    form = MesaForm(request.POST or None, instance=mesa)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Mesa {mesa.numero_mesa} actualizada.')
        return redirect('pedidos:mesas')
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
