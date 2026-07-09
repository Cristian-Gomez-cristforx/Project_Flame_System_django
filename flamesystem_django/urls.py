from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('cuentas/', include('login_modify_django.urls', namespace='login_modify')),
    path('inventario/', include('Inventario.urls', namespace='inventario')),
    path('pedidos/', include('Gestion_Pedidos.urls', namespace='pedidos')),
    path('reportes/', include('Reportes.urls', namespace='reportes')),
    path('', lambda r: redirect('login_modify:dashboard'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
