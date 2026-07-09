from django.shortcuts import render

from login_modify_django.decorators import admin_requerido

from . import services
from .forms import RangoFechasForm


def _rango_desde_request(request):
    form = RangoFechasForm(request.GET or None)
    if request.GET and form.is_valid():
        return form.cleaned_data['desde'], form.cleaned_data['hasta'], form

    desde, hasta = services.rango_por_defecto()
    if not request.GET:
        form = RangoFechasForm(initial={'desde': desde, 'hasta': hasta})
    return desde, hasta, form


@admin_requerido
def dashboard(request):
    desde, hasta, form = _rango_desde_request(request)

    ventas = services.resumen_ventas(desde, hasta)
    mermas = services.resumen_mermas(desde, hasta)
    inventario = services.estado_inventario()
    top_prod = services.top_productos(desde, hasta, limite=5)

    return render(request, 'reportes/dashboard.html', {
        'form': form,
        'ventas': ventas,
        'mermas': mermas,
        'inventario': inventario,
        'top_productos': top_prod,
    })


@admin_requerido
def ventas(request):
    desde, hasta, form = _rango_desde_request(request)

    resumen = services.resumen_ventas(desde, hasta)
    top_prod = services.top_productos(desde, hasta)
    top_beb = services.top_bebidas(desde, hasta)
    pedidos = services.pedidos_por_dia(desde, hasta)

    return render(request, 'reportes/ventas.html', {
        'form': form,
        'resumen': resumen,
        'top_productos': top_prod,
        'top_bebidas': top_beb,
        'pedidos': pedidos,
    })


@admin_requerido
def mermas(request):
    desde, hasta, form = _rango_desde_request(request)
    resumen = services.resumen_mermas(desde, hasta)

    return render(request, 'reportes/mermas.html', {
        'form': form,
        'resumen': resumen,
    })


@admin_requerido
def inventario(request):
    estado = services.estado_inventario()
    return render(request, 'reportes/inventario.html', {'estado': estado})
