from django.urls import path

from . import views


app_name = 'reportes'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('ventas/', views.ventas, name='ventas'),
    path('mermas/', views.mermas, name='mermas'),
    path('descargar-pedidos/', views.descargar_reporte_pedidos, name='descargar_pedidos'),
]
