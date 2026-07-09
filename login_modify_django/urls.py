from django.urls import path

from . import views


app_name = 'login_modify'

urlpatterns = [
    path('login/', views.FlameLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('usuarios/', views.usuarios_lista, name='usuarios_lista'),
    path('usuarios/nuevo/', views.usuario_crear, name='usuario_crear'),
    path('usuarios/<int:user_id>/editar/', views.usuario_editar, name='usuario_editar'),
    path('usuarios/<int:user_id>/toggle-activo/', views.usuario_toggle_activo, name='usuario_toggle_activo'),
]
