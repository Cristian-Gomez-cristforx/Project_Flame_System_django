from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from login_modify_django.decorators import admin_requerido

from .forms import (
    BebidaForm,
    CategoriaForm,
    DetalleRecetaFormSet,
    InsumoAgregarStockForm,
    InsumoForm,
    MermaForm,
    ProductoForm,
    RecetaProductoForm,
)
from .models import Bebida, Categoria, Insumo, Merma, Producto, RecetaProducto, DetalleReceta


@admin_requerido
def inventario(request):
    return render(request, 'temp_inventario/inventario.html')


# ====================== INSUMOS ======================
@admin_requerido
def listar_insumos(request):
    insumos = Insumo.objects.all().order_by('nombre_insumo')
    q = request.GET.get('q', '').strip()
    if q:
        insumos = insumos.filter(
            Q(nombre_insumo__icontains=q) |
            Q(id_insumo=q) if q.isdigit() else Q(nombre_insumo__icontains=q)
        )
    return render(request, 'temp_inventario/listar_insumos.html', {'insumos': insumos})


@admin_requerido
def crear_insumo(request):
    form = InsumoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        insumo = form.save()
        messages.success(request, f'Insumo "{insumo.nombre_insumo}" creado correctamente.')
        return redirect('inventario:listar_insumos')

    return render(request, 'temp_inventario/crear_insumo.html', {
        'form': form,
        'unidades': Insumo.UNIDAD_CHOICES,
        'categorias': Categoria.objects.filter(tipo=Categoria.Tipo.INSUMO),
    })


@admin_requerido
def editar_insumo(request, id):
    insumo_obj = get_object_or_404(Insumo, id_insumo=id)
    form = InsumoForm(request.POST or None, instance=insumo_obj)

    if request.method == 'POST' and form.is_valid():
        insumo = form.save()
        messages.success(request, f'Insumo "{insumo.nombre_insumo}" actualizado correctamente.')
        return redirect('inventario:listar_insumos')

    return render(request, 'temp_inventario/editar_insumo.html', {
        'form': form,
        'insumo': insumo_obj,
        'unidades': Insumo.UNIDAD_CHOICES,
        'categorias': Categoria.objects.filter(tipo=Categoria.Tipo.INSUMO),
    })


# ====================== PRODUCTOS ======================
@admin_requerido
def listar_productos(request):
    productos = Producto.objects.all().order_by('nombre_producto')
    q = request.GET.get('q', '').strip()
    if q:
        productos = productos.filter(
            Q(nombre_producto__icontains=q) |
            Q(categoria__nombre_categoria__icontains=q) |
            Q(id_producto=q) if q.isdigit() else Q(nombre_producto__icontains=q)
        )

    productos_info = []
    for producto in productos:
        try:
            receta = producto.receta
            unidades = receta.cuantas_unidades_posibles()
            tiene_receta = True
            detalles = list(receta.detalles.select_related('insumo').all())
            costo_prep = receta.costo_preparacion
            ganancia = receta.ganancia_estimada
        except RecetaProducto.DoesNotExist:
            receta = None
            unidades = 0
            tiene_receta = False
            detalles = []
            costo_prep = None
            ganancia = None

        productos_info.append({
            'producto': producto,
            'unidades_posibles': unidades,
            'tiene_receta': tiene_receta,
            'receta': receta,
            'detalles': detalles,
            'costo_preparacion': costo_prep,
            'ganancia_estimada': ganancia,
        })

    return render(request, 'temp_inventario/listar_producto.html', {'productos_info': productos_info})


@admin_requerido
def crear_producto(request):
    form = ProductoForm(request.POST or None)
    formset = DetalleRecetaFormSet(request.POST or None, prefix='detalles')

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                producto = form.save()
                receta = RecetaProducto.objects.create(producto=producto, activa=True)
                formset.instance = receta
                formset.save()
                receta.full_clean()
            messages.success(request, f'Producto "{producto.nombre_producto}" y su receta creados correctamente.')
            return redirect('inventario:listar_productos')
        except ValidationError as e:
            messages.error(request, '; '.join(e.messages))

    return render(request, 'temp_inventario/crear_producto.html', {
        'form': form,
        'formset': formset,
        'categorias': Categoria.objects.filter(tipo=Categoria.Tipo.PRODUCTO).order_by('nombre_categoria'),
    })


@admin_requerido
def editar_producto(request, id):
    producto_obj = get_object_or_404(Producto, id_producto=id)
    receta_obj, _ = RecetaProducto.objects.get_or_create(
        producto=producto_obj,
        defaults={'activa': True},
    )
    form = ProductoForm(request.POST or None, instance=producto_obj)
    formset = DetalleRecetaFormSet(request.POST or None, instance=receta_obj, prefix='detalles')

    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        try:
            with transaction.atomic():
                producto = form.save()
                formset.instance = receta_obj
                formset.save()
                receta_obj.full_clean()
            messages.success(request, f'Producto "{producto.nombre_producto}" actualizado.')
            return redirect('inventario:listar_productos')
        except ValidationError as e:
            messages.error(request, '; '.join(e.messages))

    return render(request, 'temp_inventario/editar_producto.html', {
        'form': form,
        'formset': formset,
        'producto': producto_obj,
        'categorias': Categoria.objects.filter(tipo=Categoria.Tipo.PRODUCTO).order_by('nombre_categoria'),
    })


# ====================== BEBIDAS ======================
@admin_requerido
def listar_bebidas(request):
    bebidas = Bebida.objects.all().order_by('nombre_bebida')
    q = request.GET.get('q', '').strip()
    if q:
        bebidas = bebidas.filter(
            Q(nombre_bebida__icontains=q) |
            Q(categoria__nombre_categoria__icontains=q) |
            Q(id_bebida=q) if q.isdigit() else Q(nombre_bebida__icontains=q)
        )
    return render(request, 'temp_inventario/listar_bebida.html', {'bebidas': bebidas})


@admin_requerido
def crear_bebida(request):
    form = BebidaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        bebida = form.save()
        messages.success(request, f'Bebida "{bebida.nombre_bebida}" creada correctamente.')
        return redirect('inventario:listar_bebidas')

    return render(request, 'temp_inventario/crear_bebida.html', {
        'form': form,
        'tamaño_choices': Bebida.TAMAÑO_CHOICES,
        'categorias': Categoria.objects.filter(tipo=Categoria.Tipo.BEBIDA).order_by('nombre_categoria'),
    })


@admin_requerido
def editar_bebida(request, id):
    bebida_obj = get_object_or_404(Bebida, id_bebida=id)
    form = BebidaForm(request.POST or None, instance=bebida_obj)

    if request.method == 'POST' and form.is_valid():
        bebida = form.save()
        messages.success(request, f'Bebida "{bebida.nombre_bebida}" actualizada correctamente.')
        return redirect('inventario:listar_bebidas')

    return render(request, 'temp_inventario/editar_bebida.html', {
        'form': form,
        'bebida': bebida_obj,
        'tamaño_choices': Bebida.TAMAÑO_CHOICES,
        'categorias': Categoria.objects.filter(tipo=Categoria.Tipo.BEBIDA).order_by('nombre_categoria'),
    })


# ====================== MERMAS ======================
@admin_requerido
def listar_mermas(request):
    mermas = Merma.objects.all().order_by('-fecha_merma')
    return render(request, 'temp_inventario/listar_mermas.html', {'mermas': mermas})


@admin_requerido
def crear_merma(request):
    form = MermaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        merma = form.save()
        messages.success(
            request,
            f'Merma registrada correctamente. Se descontaron {merma.cantidad_mermada} '
            f'unidades de {merma.insumo.nombre_insumo}.'
        )
        return redirect('inventario:listar_mermas')

    return render(request, 'temp_inventario/crear_merma.html', {
        'form': form,
        'insumos': Insumo.objects.all().order_by('nombre_insumo'),
    })


# ====================== AGREGAR STOCK ======================
@admin_requerido
def agregar_stock_insumo(request, id):
    insumo_obj = get_object_or_404(Insumo, id_insumo=id)
    form = InsumoAgregarStockForm(request.POST or None, instance=insumo_obj)

    if request.method == 'POST' and form.is_valid():
        try:
            form.save()
            messages.success(request, f'Stock actualizado. Cantidad actual: {insumo_obj.cantidad_insumo}.')
            return redirect('inventario:listar_insumos')
        except ValidationError as e:
            messages.error(request, '; '.join(e.messages))

    return render(request, 'temp_inventario/agregar_stock.html', {
        'form': form,
        'insumo': insumo_obj,
    })


# ====================== TURNO ======================
@admin_requerido
@require_POST
def abrir_turno(request):
    ids = request.POST.getlist('insumos')
    if not ids:
        messages.warning(request, 'Selecciona al menos un insumo.')
        return redirect('inventario:listar_insumos')

    insumos = Insumo.objects.filter(id_insumo__in=ids)
    for insumo in insumos:
        insumo.abrir_turno()
    messages.success(request, f'Turno abierto para {insumos.count()} insumo(s).')
    return redirect('inventario:listar_insumos')


@admin_requerido
@require_POST
def cerrar_turno(request):
    ids = request.POST.getlist('insumos')
    if not ids:
        messages.warning(request, 'Selecciona al menos un insumo.')
        return redirect('inventario:listar_insumos')

    actualizados = Insumo.objects.filter(id_insumo__in=ids).update(stock_maximo=0)
    messages.success(request, f'Turno cerrado para {actualizados} insumo(s).')
    return redirect('inventario:listar_insumos')


# ====================== RECETAS ======================
@admin_requerido
def listar_recetas(request):
    recetas = (
        RecetaProducto.objects
        .select_related('producto')
        .prefetch_related('detalles__insumo')
        .order_by('producto__nombre_producto')
    )
    q = request.GET.get('q', '').strip()
    if q:
        recetas = recetas.filter(producto__nombre_producto__icontains=q)

    recetas_info = [
        {
            'receta': r,
            'unidades_posibles': r.cuantas_unidades_posibles(),
        }
        for r in recetas
    ]

    return render(request, 'temp_inventario/listar_recetas.html', {'recetas_info': recetas_info})


@admin_requerido
def crear_receta(request):
    if request.method == 'POST':
        form = RecetaProductoForm(request.POST)
        formset = DetalleRecetaFormSet(request.POST, prefix='detalles')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    receta = form.save()
                    formset.instance = receta
                    formset.save()
                    receta.full_clean()
                messages.success(request, f'Receta de "{receta.producto.nombre_producto}" creada.')
                return redirect('inventario:listar_recetas')
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
    else:
        form = RecetaProductoForm()
        formset = DetalleRecetaFormSet(prefix='detalles')

    return render(request, 'temp_inventario/crear_receta.html', {
        'form': form,
        'formset': formset,
    })


@admin_requerido
def editar_receta(request, id):
    receta = get_object_or_404(RecetaProducto, pk=id)

    if request.method == 'POST':
        form = RecetaProductoForm(request.POST, instance=receta)
        formset = DetalleRecetaFormSet(request.POST, instance=receta, prefix='detalles')

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    formset.save()
                    receta.full_clean()
                messages.success(request, 'Receta actualizada.')
                return redirect('inventario:listar_recetas')
            except ValidationError as e:
                messages.error(request, '; '.join(e.messages))
    else:
        form = RecetaProductoForm(instance=receta)
        formset = DetalleRecetaFormSet(instance=receta, prefix='detalles')

    return render(request, 'temp_inventario/editar_receta.html', {
        'form': form,
        'formset': formset,
        'receta': receta,
    })


@admin_requerido
@require_POST
def eliminar_receta(request, id):
    receta = get_object_or_404(RecetaProducto, pk=id)
    nombre = receta.producto.nombre_producto
    receta.delete()
    messages.success(request, f'Receta de "{nombre}" eliminada.')
    return redirect('inventario:listar_recetas')


# ====================== CATEGORÍAS ======================
@admin_requerido
def listar_categorias(request):
    tipo = request.GET.get('tipo', '').strip()
    categorias = Categoria.objects.all().order_by('tipo', 'nombre_categoria')
    if tipo:
        categorias = categorias.filter(tipo=tipo)

    return render(request, 'temp_inventario/listar_categorias.html', {
        'categorias': categorias,
        'tipos': Categoria.Tipo.choices,
        'tipo_actual': tipo,
    })


@admin_requerido
def crear_categoria(request):
    form = CategoriaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            categoria = form.save()
            messages.success(request, f'Categoría "{categoria.nombre_categoria}" creada.')
            return redirect('inventario:listar_categorias')
        except ValidationError as e:
            messages.error(request, '; '.join(e.messages))

    return render(request, 'temp_inventario/crear_categoria.html', {'form': form})


@admin_requerido
def editar_categoria(request, id):
    categoria = get_object_or_404(Categoria, pk=id)
    form = CategoriaForm(request.POST or None, instance=categoria)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Categoría actualizada.')
        return redirect('inventario:listar_categorias')

    return render(request, 'temp_inventario/editar_categoria.html', {
        'form': form,
        'categoria': categoria,
    })


@admin_requerido
@require_POST
def eliminar_categoria(request, id):
    categoria = get_object_or_404(Categoria, pk=id)
    total_uso = (
        categoria.insumos.count() +
        categoria.productos.count() +
        categoria.bebidas.count()
    )
    if total_uso > 0:
        messages.error(
            request,
            f'No se puede eliminar "{categoria.nombre_categoria}": tiene {total_uso} ítem(s) asociado(s).'
        )
    else:
        nombre = categoria.nombre_categoria
        categoria.delete()
        messages.success(request, f'Categoría "{nombre}" eliminada.')

    return redirect('inventario:listar_categorias')
