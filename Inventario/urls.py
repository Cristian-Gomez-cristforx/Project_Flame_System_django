from django.urls import path
from . import views

app_name = 'inventario'   #debe quedar exactamente así

urlpatterns = [
    # ====================== INSUMOS ======================
    path('insumos/', views.listar_insumos, name='listar_insumos'),
    path('insumos/crear/', views.crear_insumo, name='crear_insumo'),
    path('insumos/editar/<int:id>/', views.editar_insumo, name='editar_insumo'),

    # ====================== PRODUCTOS ======================
    path('productos/', views.listar_productos, name='listar_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:id>/', views.editar_producto, name='editar_producto'),
    path('productos/buscar/', views.buscar_producto, name='buscar_producto'),

    # ====================== BEBIDAS ======================
    path('bebidas/', views.listar_bebidas, name='listar_bebidas'),
    path('bebidas/crear/', views.crear_bebida, name='crear_bebida'),
    path('bebidas/editar/<int:id>/', views.editar_bebida, name='editar_bebida'),
    path('bebidas/buscar/', views.buscar_bebida, name='buscar_bebida'),
]