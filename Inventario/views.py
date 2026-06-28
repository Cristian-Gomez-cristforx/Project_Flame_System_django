from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Insumo, Producto, Bebida, RecetaProducto, DetalleReceta, Merma, Categoria
from django.db.models import Q
from django.core.exceptions import ValidationError


def inventario(request):
    return render(request, 'temp_inventario/inventario.html')


# ====================== INSUMOS ======================
def listar_insumos(request):
    insumos = Insumo.objects.all().order_by('nombre_insumo')
    q = request.GET.get('q', '').strip()
    if q:
        insumos = insumos.filter(
            Q(nombre_insumo__icontains=q) |
            Q(id_insumo=q) if q.isdigit() else Q()
        )
    return render(request, 'temp_inventario/listar_insumos.html', {'insumos': insumos})


def crear_insumo(request):
    if request.method == 'POST':
        try:
            
            categoria_id = request.POST.get('categoria')
            nueva_categoria = request.POST.get('nueva_categoria', '').strip()
            
            # Si escribo una nueva categoría, este camoi y logica es para eso, agregar una aparte.
            if nueva_categoria:
                categoria, creada = Categoria.objects.get_or_create(
                    nombre_categoria=nueva_categoria,
                    defaults={'tipo': Categoria.Tipo.INSUMO}
                )
            else:
                categoria = Categoria.objects.get(id=categoria_id)
            
            nuevo_insumo = Insumo(
                nombre_insumo=request.POST['nombre_insumo'],
                cantidad_insumo=request.POST['cantidad_insumo'],
                unidad_medida=request.POST['unidad_medida'],
                precio_insumo=request.POST['precio_insumo'],
                categoria=categoria,
            )
            nuevo_insumo.full_clean()
            nuevo_insumo.save()

            messages.success(
                request, 
                f'Insumo "{nuevo_insumo.nombre_insumo}" creado correctamente.')
            
            return redirect('inventario:listar_insumos')

        except Exception as e:
            messages.error(request, f'Error al crear insumo: {str(e)}')

    unidades = Insumo.UNIDAD_CHOICES
    
    categorias = Categoria.objects.filter(
        tipo=Categoria.Tipo.INSUMO
    )
    
    return render(
        request, 
        'temp_inventario/crear_insumo.html',
        {
           'unidades': unidades,
           'categorias': categorias
    }
        )


def editar_insumo(request, id):
    insumo_obj = get_object_or_404(Insumo, id_insumo=id)

    if request.method == 'POST':
        try:
            insumo_obj.nombre_insumo   = request.POST['nombre_insumo']
            insumo_obj.cantidad_insumo = request.POST['cantidad_insumo']
            insumo_obj.unidad_medida   = request.POST['unidad_medida']
            insumo_obj.precio_insumo   = request.POST['precio_insumo']

            insumo_obj.full_clean()
            insumo_obj.save()

            messages.success(request, f'Insumo "{insumo_obj.nombre_insumo}" actualizado correctamente.')
            return redirect('inventario:listar_insumos')

        except Exception as e:
            messages.error(request, f'Error al actualizar insumo: {str(e)}')

    unidades = Insumo.UNIDAD_CHOICES
    return render(request, 'temp_inventario/editar_insumo.html', {
        'insumo': insumo_obj,
        'unidades': unidades
    })


# ====================== PRODUCTOS ======================
def listar_productos(request):
    productos = Producto.objects.all().order_by('nombre_producto')
    q = request.GET.get('q', '').strip()
    if q:
        productos = productos.filter(
            Q(nombre_producto__icontains=q) |
            Q(categoria__nombre_categoria__icontains=q) |
            Q(id_producto=q) if q.isdigit() else Q()
        )

    productos_info = []
    for producto in productos:
        try:
            receta = producto.receta
            unidades = receta.cuantas_unidades_posibles()
            tiene_receta = True
        except RecetaProducto.DoesNotExist:
            unidades = 0
            tiene_receta = False

        productos_info.append({
            'producto': producto,
            'unidades_posibles': unidades,
            'tiene_receta': tiene_receta,
        })

    return render(request, 'temp_inventario/listar_producto.html', {'productos_info': productos_info})


def crear_producto(request):
    # Categoría se asigna automáticamente desde el modelo (tipo PRODUCTO)
    if request.method == 'POST':
        try:
            nuevo_producto = Producto(
                nombre_producto=request.POST['nombre_producto'],
                precio_producto=request.POST['precio_producto'],
                activo=request.POST.get('activo') == 'on',
            )
            nuevo_producto.full_clean()
            nuevo_producto.save()

            messages.success(request, f'Producto "{nuevo_producto.nombre_producto}" creado correctamente.')
            return redirect('inventario:listar_productos')

        except Exception as e:
            messages.error(request, f'Error al crear producto: {str(e)}')

    return render(request, 'temp_inventario/crear_producto.html')


def editar_producto(request, id):
    producto_obj = get_object_or_404(Producto, id_producto=id)
    categorias = Categoria.objects.filter(tipo=Categoria.Tipo.PRODUCTO).order_by('nombre_categoria')

    if request.method == 'POST':
        try:
            categoria_id = request.POST.get('categoria')
            producto_obj.nombre_producto = request.POST['nombre_producto']
            producto_obj.precio_producto = request.POST['precio_producto']
            producto_obj.activo = request.POST.get('activo') == 'on'
            producto_obj.categoria_id = categoria_id if categoria_id else None
            producto_obj.full_clean()
            producto_obj.save()

            messages.success(request, f'Producto "{producto_obj.nombre_producto}" actualizado.')
            return redirect('inventario:listar_productos')

        except Exception as e:
            messages.error(request, f'Error al actualizar producto: {str(e)}')

    return render(request, 'temp_inventario/editar_producto.html', {
        'producto': producto_obj,
        'categorias': categorias
    })


# ====================== BEBIDAS ======================
def listar_bebidas(request):
    bebidas = Bebida.objects.all().order_by('nombre_bebida')
    q = request.GET.get('q', '').strip()
    if q:
        bebidas = bebidas.filter(
            Q(nombre_bebida__icontains=q) |
            Q(categoria__nombre_categoria__icontains=q) |
            Q(id_bebida=q) if q.isdigit() else Q()
        )
    return render(request, 'temp_inventario/listar_bebida.html', {'bebidas': bebidas})


def crear_bebida(request):
    # Categoría se asigna automáticamente desde el modelo (tipo BEBIDA)
    if request.method == 'POST':
        try:
            nueva_bebida = Bebida(
                nombre_bebida=request.POST['nombre_bebida'],
                cantidad_bebida=request.POST['cantidad_bebida'],
                precio_compra=request.POST['precio_compra'],
                precio_venta=request.POST['precio_venta'],
                tamaño_bebida=request.POST['tamaño_bebida'],
            )
            nueva_bebida.full_clean()
            nueva_bebida.save()

            messages.success(request, f'Bebida "{nueva_bebida.nombre_bebida}" creada correctamente.')
            return redirect('inventario:listar_bebidas')

        except Exception as e:
            messages.error(request, f'Error al crear bebida: {str(e)}')

    return render(request, 'temp_inventario/crear_bebida.html', {
        'tamaño_choices': Bebida.TAMAÑO_CHOICES
    })


def editar_bebida(request, id):
    bebida_obj = get_object_or_404(Bebida, id_bebida=id)
    categorias = Categoria.objects.filter(tipo=Categoria.Tipo.BEBIDA).order_by('nombre_categoria')

    if request.method == 'POST':
        try:
            categoria_id = request.POST.get('categoria')
            bebida_obj.nombre_bebida   = request.POST.get('nombre_bebida', bebida_obj.nombre_bebida)
            bebida_obj.cantidad_bebida = request.POST.get('cantidad_bebida', bebida_obj.cantidad_bebida)
            bebida_obj.precio_compra   = request.POST['precio_compra']
            bebida_obj.precio_venta    = request.POST['precio_venta']
            bebida_obj.tamaño_bebida   = request.POST.get('tamaño_bebida', bebida_obj.tamaño_bebida)
            bebida_obj.categoria_id    = categoria_id if categoria_id else None

            bebida_obj.full_clean()
            bebida_obj.save()

            messages.success(request, f'Bebida "{bebida_obj.nombre_bebida}" actualizada correctamente.')
            return redirect('inventario:listar_bebidas')

        except Exception as e:
            messages.error(request, f'Error al actualizar bebida: {str(e)}')

    return render(request, 'temp_inventario/editar_bebida.html', {
        'bebida': bebida_obj,
        'tamaño_choices': Bebida.TAMAÑO_CHOICES,
        'categorias': categorias
    })


# ====================== MERMAS ======================
def listar_mermas(request):
    mermas = Merma.objects.all().order_by('-fecha_merma')
    return render(request, 'temp_inventario/listar_mermas.html', {'mermas': mermas})


def crear_merma(request):
    if request.method == 'POST':
        try:
            insumo_id  = request.POST.get('insumo')
            insumo_obj = Insumo.objects.get(id_insumo=insumo_id)

            nueva_merma = Merma(
                insumo=insumo_obj,
                cantidad_mermada=int(request.POST['cantidad_mermada']),  # ← casteo a int
                motivo=request.POST['motivo'],
                descripcion=request.POST.get('descripcion', ''),
                responsable=request.POST['responsable'],
            )
            nueva_merma.full_clean()
            nueva_merma.save()

            messages.success(
                request,
                f'Merma registrada correctamente. Se descontaron {nueva_merma.cantidad_mermada} '
                f'unidades de {insumo_obj.nombre_insumo}.'
            )
            return redirect('inventario:listar_mermas')

        except ValidationError as e:
            # Error específico de validación (stock insuficiente, etc.)
            messages.error(request, f'Error de validación: {e}')
        except Exception as e:
            messages.error(request, f'Error al registrar merma: {str(e)}')

    insumos = Insumo.objects.all().order_by('nombre_insumo')
    return render(request, 'temp_inventario/crear_merma.html', {'insumos': insumos})