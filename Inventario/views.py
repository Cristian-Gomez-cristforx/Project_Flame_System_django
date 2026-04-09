# inventario/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Insumo, Producto, Bebida   # ← Corrección importante
# from .forms import InsumoForm, ProductoForm, BebidaForm   ← Lo descomentaremos después

# ====================== INSUMOS ======================
        
def listar_insumos(request):
    insumos = Insumo.objects.all().order_by('nombre_insumo')
    return render(request, 'inventario/listar_insumos.html', {'insumos': insumos})


def crear_insumo(request):
    if request.method == 'POST':
        
        try:
            nuevo_insumo = Insumo(
                nombre_insumo=request.POST['nombre_insumo'],
                cantidad_insumo=request.POST['cantidad_insumo'],
                precio_insumo=request.POST['precio_insumo']
            )
            nuevo_insumo.full_clean()      # ← Ejecuta las validaciones del modelo
            nuevo_insumo.save()
            messages.success(request, f'Insumo "{nuevo_insumo.nombre_insumo}" creado correctamente.')
            return redirect('inventario:listar_insumos')
        except Exception as e:
            messages.error(request, f'Error al crear insumo: {str(e)}')
    
    return render(request, 'inventario/crear_insumo.html')


def editar_insumo(request, id):
    insumo_obj = get_object_or_404(Insumo, id_insumo=id)
    
    if request.method == 'POST':
        try:
            insumo_obj.cantidad_insumo = request.POST['cantidad_insumo']
            insumo_obj.precio_insumo = request.POST['precio_insumo']
            insumo_obj.full_clean()
            insumo_obj.save()
            messages.success(request, f'Insumo "{insumo_obj.nombre_insumo}" actualizado.')
            return redirect('inventario:listar_insumos')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    return render(request, 'inventario/editar_insumo.html', {'insumo': insumo_obj})


# ====================== PRODUCTOS ======================

def listar_productos(request):
    productos = Producto.objects.all().order_by('nombre_producto')
    return render(request, 'inventario/listar_productos.html', {'productos': productos})


def crear_producto(request):
    if request.method == 'POST':
        try:
            nuevo_producto = Producto(
                nombre_producto=request.POST['nombre_producto'],
                precio_producto=request.POST['precio_producto'],
                ingrediente_producto=request.POST.get('ingrediente_producto', '')
            )
            nuevo_producto.full_clean()
            nuevo_producto.save()
            messages.success(request, f'Producto "{nuevo_producto.nombre_producto}" creado correctamente.')
            return redirect('inventario:listar_productos')
        except Exception as e:
            messages.error(request, f'Error al crear producto: {str(e)}')
    
    return render(request, 'inventario/crear_producto.html')


def editar_producto(request, id):
    producto_obj = get_object_or_404(Producto, id_producto=id)
    
    if request.method == 'POST':
        try:
            producto_obj.precio_producto = request.POST['precio_producto']
            producto_obj.full_clean()
            producto_obj.save()
            messages.success(request, f'Producto "{producto_obj.nombre_producto}" actualizado.')
            return redirect('inventario:listar_productos')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    return render(request, 'inventario/editar_producto.html', {'producto': producto_obj})


# ====================== BEBIDAS ======================

def listar_bebidas(request):
    bebidas = Bebida.objects.all().order_by('nombre_bebida')
    return render(request, 'inventario/listar_bebidas.html', {'bebidas': bebidas})


def crear_bebida(request):
    if request.method == 'POST':
        try:
            nueva_bebida = Bebida(
                nombre_bebida=request.POST['nombre_bebida'],
                cantidad_bebida=request.POST['cantidad_bebida'],
                precio_compra=request.POST['precio_compra'],
                precio_venta=request.POST['precio_venta'],
                tipo_bebida=request.POST['tipo_bebida'],
                tamaño_bebida=request.POST['tamaño_bebida']
            )
            nueva_bebida.full_clean()
            nueva_bebida.save()
            messages.success(request, f'Bebida "{nueva_bebida.nombre_bebida}" creada correctamente.')
            return redirect('inventario:listar_bebidas')
        except Exception as e:
            messages.error(request, f'Error al crear bebida: {str(e)}')
    
    return render(request, 'inventario/crear_bebida.html')


def editar_bebida(request, id):
    bebida_obj = get_object_or_404(Bebida, id_bebida=id)
    
    if request.method == 'POST':
        try:
            bebida_obj.precio_compra = request.POST['precio_compra']
            bebida_obj.precio_venta = request.POST['precio_venta']
            # Puedes agregar más campos si quieres editarlos
            bebida_obj.full_clean()
            bebida_obj.save()
            messages.success(request, f'Bebida "{bebida_obj.nombre_bebida}" actualizada.')
            return redirect('inventario:listar_bebidas')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    return render(request, 'inventario/editar_bebida.html', {'bebida': bebida_obj})


def buscar_producto(request):
    try:
        producto = Producto.objects.get(id_producto=request.GET.get('id'))
        return render(request, 'inventario/buscar_producto.html', {'producto': producto})
    except Producto.DoesNotExist:
        messages.error(request, 'Producto no encontrado.')
        return redirect('inventario:listar_productos')


def buscar_bebida(request):
    try:
        bebida = Bebida.objects.get(id_bebida=request.GET.get('id'))
        return render(request, 'inventario/buscar_bebida.html', {'bebida': bebida})
    except Bebida.DoesNotExist:
        messages.error(request, 'Bebida no encontrada.')
        return redirect('inventario:listar_bebidas')