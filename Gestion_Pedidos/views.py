from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from login_modify_django.decorators import rol_requerido
from login_modify_django.models import Perfil

from . import services
from .forms import (
    AgregarBebidaForm,
    AgregarProductoForm,
    FiltroPedidosForm,
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
                pedido = services.crear_pedido(request.user, form.cleaned_data)
                messages.success(request, f'Pedido {pedido.numero_factura} creado. Agrega productos y bebidas.')
                return redirect('pedidos:detalle', pedido_id=pedido.id_pedido)
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
    else:
        form = PedidoCrearForm()

    return render(request, 'pedidos/crear.html', {
        'form': form,
        'tipos': Pedido.TipoPedido.choices,
    })


@rol_requerido(*ROLES_PEDIDOS)
def detalle_pedido(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.select_related('mesa', 'mesero').prefetch_related('productos__producto', 'bebidas__bebida'),
        pk=pedido_id,
    )
    totales = services.calcular_totales(pedido)

    return render(request, 'pedidos/detalle.html', {
        'pedido': pedido,
        'totales': totales,
        'form_producto': AgregarProductoForm(),
        'form_bebida': AgregarBebidaForm(),
        'form_pago': PagoForm(instance=pedido),
        'estados': Pedido.EstadoPedido,
    })


@rol_requerido(*ROLES_PEDIDOS)
@require_POST
def agregar_producto(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    form = AgregarProductoForm(request.POST)
    if form.is_valid():
        try:
            services.agregar_producto(
                pedido,
                form.cleaned_data['producto'],
                form.cleaned_data['cantidad'],
            )
            messages.success(request, 'Producto agregado.')
        except ValidationError as e:
            messages.error(request, '; '.join(e.messages))
    else:
        messages.error(request, 'Formulario inválido.')
    return redirect('pedidos:detalle', pedido_id=pedido_id)


@rol_requerido(*ROLES_PEDIDOS)
@require_POST
def agregar_bebida(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    form = AgregarBebidaForm(request.POST)
    if form.is_valid():
        try:
            services.agregar_bebida(
                pedido,
                form.cleaned_data['bebida'],
                form.cleaned_data['cantidad'],
            )
            messages.success(request, 'Bebida agregada.')
        except ValidationError as e:
            messages.error(request, '; '.join(e.messages))
    else:
        messages.error(request, 'Formulario inválido.')
    return redirect('pedidos:detalle', pedido_id=pedido_id)


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
    try:
        services.cambiar_estado(pedido, nuevo)
        messages.success(request, f'Pedido → {pedido.get_estado_display()}.')
    except ValidationError as e:
        messages.error(request, '; '.join(e.messages))
    return redirect(request.POST.get('next') or reverse('pedidos:detalle', args=[pedido_id]))


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
    mesas = Mesa.objects.filter(activa=True).order_by('numero_mesa')
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

    return render(request, 'pedidos/mesas.html', {'mesas_data': data})


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
