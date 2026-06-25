from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Insumo, Producto, Bebida, RecetaProducto, DetalleReceta, Merma
import json


def inventario(request):
    return render(request, 'temp_inventario/inventario.html')


# ====================== INSUMOS ======================
def listar_insumos(request):
    insumos = Insumo.objects.all().order_by('nombre_insumo')
    return render(request, 'temp_inventario/listar_insumos.html', {'insumos': insumos})


def crear_insumo(request):
    if request.method == 'POST':
        try:
            nuevo_insumo = Insumo(
                nombre_insumo=request.POST['nombre_insumo'],
                cantidad_insumo=request.POST['cantidad_insumo'],
                unidad_medida=request.POST['unidad_medida'],
                precio_insumo=request.POST['precio_insumo']
            )
            nuevo_insumo.full_clean()
            nuevo_insumo.save()
            messages.success(request, f'Insumo "{nuevo_insumo.nombre_insumo}" creado correctamente.')
            return redirect('inventario:listar_insumos')
        except Exception as e:
            messages.error(request, f'Error al crear insumo: {str(e)}')

    unidades = Insumo.UNIDAD_CHOICES
    return render(request, 'temp_inventario/crear_insumo.html', {'unidades': unidades})


def editar_insumo(request, id):
    insumo_obj = get_object_or_404(Insumo, id_insumo=id)

    if request.method == 'POST':
        try:
            insumo_obj.cantidad_insumo = request.POST['cantidad_insumo']
            insumo_obj.unidad_medida   = request.POST['unidad_medida']
            insumo_obj.precio_insumo   = request.POST['precio_insumo']
            insumo_obj.full_clean()
            insumo_obj.save()
            messages.success(request, f'Insumo "{insumo_obj.nombre_insumo}" actualizado.')
            return redirect('inventario:listar_insumos')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')

    unidades = Insumo.UNIDAD_CHOICES
    return render(request, 'temp_inventario/editar_insumo.html', {
        'insumo': insumo_obj,
        'unidades': unidades
    })


# ====================== PRODUCTOS ======================
def listar_productos(request):
    productos = Producto.objects.all().order_by('nombre_producto')

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

    return render(request, 'temp_inventario/listar_productos.html', {'productos_info': productos_info})


def crear_producto(request):
    insumos = Insumo.objects.all().order_by('nombre_insumo')

    if request.method == 'POST':
        try:
           
            nuevo_producto = Producto(
                nombre_producto=request.POST['nombre_producto'],
                precio_producto=request.POST['precio_producto'],
                activo=request.POST.get('activo') == 'on',
            )
            nuevo_producto.full_clean()
            nuevo_producto.save()

            # Lógica de receta
            insumo_ids = request.POST.getlist('insumo_id[]')
            cantidades  = request.POST.getlist('cantidad_requerida[]')

            if any(i for i in insumo_ids if i):
                receta = RecetaProducto.objects.create(
                    producto=nuevo_producto,
                    activa=True
                )
                for insumo_id, cantidad in zip(insumo_ids, cantidades):
                    if insumo_id and cantidad:
                        DetalleReceta.objects.create(
                            receta=receta,
                            insumo_id=insumo_id,
                            cantidad_requerida=cantidad
                        )

            messages.success(request, f'Producto "{nuevo_producto.nombre_producto}" creado correctamente.')
            return redirect('inventario:listar_productos')

        except Exception as e:
            messages.error(request, f'Error al crear producto: {str(e)}')

    return render(request, 'temp_inventario/crear_producto.html', {
        'insumos': insumos
    })


def editar_producto(request, id):
    producto_obj = get_object_or_404(Producto, id_producto=id)
    insumos      = Insumo.objects.all().order_by('nombre_insumo')

    try:
        receta_existente  = producto_obj.receta
        detalles_existentes = receta_existente.detalles.all()
    except RecetaProducto.DoesNotExist:
        receta_existente    = None
        detalles_existentes = []

    if request.method == 'POST':
        try:

            producto_obj.nombre_producto  = request.POST['nombre_producto']
            producto_obj.precio_producto  = request.POST['precio_producto']
            producto_obj.activo           = request.POST.get('activo') == 'on'
            producto_obj.full_clean()
            producto_obj.save()

            insumo_ids = request.POST.getlist('insumo_id[]')
            cantidades  = request.POST.getlist('cantidad_requerida[]')

            if any(i for i in insumo_ids if i):
                if receta_existente:
                    receta_existente.detalles.all().delete()
                    receta = receta_existente
                else:
                    receta = RecetaProducto.objects.create(
                        producto=producto_obj,
                        activa=True
                    )
                for insumo_id, cantidad in zip(insumo_ids, cantidades):
                    if insumo_id and cantidad:
                        DetalleReceta.objects.create(
                            receta=receta,
                            insumo_id=insumo_id,
                            cantidad_requerida=cantidad
                        )
            else:
                if receta_existente:
                    receta_existente.delete()

            messages.success(request, f'Producto "{producto_obj.nombre_producto}" actualizado.')
            return redirect('inventario:listar_productos')

        except Exception as e:
            messages.error(request, f'Error al actualizar producto: {str(e)}')

    insumos_json = json.dumps([
        {'id': i.id_insumo, 'nombre': i.nombre_insumo, 'unidad': i.get_unidad_medida_display()}
        for i in insumos
    ])

  

    return render(request, 'temp_inventario/editar_producto.html', {
        'producto':             producto_obj,
        'insumos':              insumos,
        'insumos_json':         insumos_json,
        'detalles_existentes':  detalles_existentes,
    })


# ====================== BEBIDAS ======================
def listar_bebidas(request):
    bebidas = Bebida.objects.all().order_by('nombre_bebida')
    return render(request, 'temp_inventario/listar_bebidas.html', {'bebidas': bebidas})


def crear_bebida(request):
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

    if request.method == 'POST':
        try:

            bebida_obj.nombre_bebida   = request.POST.get('nombre_bebida',   bebida_obj.nombre_bebida)
            bebida_obj.cantidad_bebida = request.POST.get('cantidad_bebida', bebida_obj.cantidad_bebida)
            bebida_obj.precio_compra   = request.POST['precio_compra']
            bebida_obj.precio_venta    = request.POST['precio_venta']
            bebida_obj.tamaño_bebida   = request.POST.get('tamaño_bebida',   bebida_obj.tamaño_bebida)
            bebida_obj.full_clean()
            bebida_obj.save()

            messages.success(request, f'Bebida "{bebida_obj.nombre_bebida}" actualizada correctamente.')
            return redirect('inventario:listar_bebidas')

        except Exception as e:
            messages.error(request, f'Error al actualizar bebida: {str(e)}')

   

    return render(request, 'temp_inventario/editar_bebida.html', {
        'bebida':         bebida_obj,
        'tamaño_choices': Bebida.TAMAÑO_CHOICES,
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
                cantidad_insumo_dañado=request.POST['cantidad_insumo_dañado'],
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

        except Exception as e:
            messages.error(request, f'Error al registrar merma: {str(e)}')

    insumos = Insumo.objects.all().order_by('nombre_insumo')
    return render(request, 'temp_inventario/crear_merma.html', {'insumos': insumos})