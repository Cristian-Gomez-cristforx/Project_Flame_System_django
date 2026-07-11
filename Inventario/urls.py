from django.urls import path

from . import views


app_name = 'inventario'

urlpatterns = [
    path('', views.inventario, name='inventario'),

    # Insumos
    path('insumos/', views.listar_insumos, name='listar_insumos'),
    path('insumos/crear/', views.crear_insumo, name='crear_insumo'),
    path('insumos/editar/<int:id>/', views.editar_insumo, name='editar_insumo'),
    path('insumos/agregar-stock/<int:id>/', views.agregar_stock_insumo, name='agregar_stock_insumo'),

    # Turno
    path('insumos/turno/abrir/', views.abrir_turno, name='abrir_turno'),
    path('insumos/turno/cerrar/', views.cerrar_turno, name='cerrar_turno'),

    # Productos
    path('productos/', views.listar_productos, name='listar_productos'),
    path('productos/crear/', views.crear_producto, name='crear_producto'),
    path('productos/editar/<int:id>/', views.editar_producto, name='editar_producto'),

    # Bebidas
    path('bebidas/', views.listar_bebidas, name='listar_bebidas'),
    path('bebidas/crear/', views.crear_bebida, name='crear_bebida'),
    path('bebidas/editar/<int:id>/', views.editar_bebida, name='editar_bebida'),

    # Categorías
    path('categorias/', views.listar_categorias, name='listar_categorias'),
    path('categorias/crear/', views.crear_categoria, name='crear_categoria'),
    path('categorias/editar/<int:id>/', views.editar_categoria, name='editar_categoria'),
    path('categorias/eliminar/<int:id>/', views.eliminar_categoria, name='eliminar_categoria'),

    # Mermas
    path('mermas/', views.listar_mermas, name='listar_mermas'),
    path('mermas/crear/', views.crear_merma, name='crear_merma'),
]
