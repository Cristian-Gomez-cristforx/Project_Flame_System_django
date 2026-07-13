from django.urls import path

from . import views


app_name = 'pedidos'

urlpatterns = [
    path('', views.lista_pedidos, name='lista'),
    path('nuevo/', views.crear_pedido, name='crear'),
    path('mesas/', views.lista_mesas, name='mesas'),
    path('mesas/nueva/', views.mesa_crear, name='mesa_crear'),
    path('mesas/<int:mesa_id>/editar/', views.mesa_editar, name='mesa_editar'),
    path('mesas/<int:mesa_id>/eliminar/', views.mesa_eliminar, name='mesa_eliminar'),
    path('cocina/', views.cocina, name='cocina'),
    path('<int:pedido_id>/', views.detalle_pedido, name='detalle'),
    path('<int:pedido_id>/agregar-producto/', views.agregar_producto, name='agregar_producto'),
    path('<int:pedido_id>/agregar-bebida/', views.agregar_bebida, name='agregar_bebida'),
    path('<int:pedido_id>/eliminar/<str:tipo_item>/<int:item_id>/', views.eliminar_item, name='eliminar_item'),
    path('<int:pedido_id>/detalle-producto/<int:detalle_id>/editar-receta/', views.editar_receta_detalle, name='editar_receta_detalle'),
    path('<int:pedido_id>/cambiar-estado/', views.cambiar_estado, name='cambiar_estado'),
    path('<int:pedido_id>/cambiar-mesa/', views.cambiar_mesa, name='cambiar_mesa'),
    path('<int:pedido_id>/cobrar/', views.cobrar_pedido, name='cobrar'),
    path('<int:pedido_id>/factura.pdf', views.factura_imagen, name='factura_imagen'),
]
