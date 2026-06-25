# inventario/urls.py

from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    
    path('', views.inventario, name='inventario'),                   

    # Insumos
    path('insumos/', views.listar_insumos, name='listar_insumos'),
    path('insumos/crear/', views.crear_insumo, name='crear_insumo'),
    path('insumos/editar/<int:id>/', views.editar_insumo, name='editar_insumo'),

    # Productos
    path('productos/', views.listar_productos, name='listar_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:id>/', views.editar_producto, name='editar_producto'),

    # Bebidas
    path('bebidas/', views.listar_bebidas, name='listar_bebidas'),
    path('bebidas/crear/', views.crear_bebida, name='crear_bebida'),
    path('bebidas/editar/<int:id>/', views.editar_bebida, name='editar_bebida'),

    # ====================== MERMAS ======================
    path('mermas/', views.listar_mermas, name='listar_mermas'),
    path('mermas/crear/', views.crear_merma, name='crear_merma'),
]