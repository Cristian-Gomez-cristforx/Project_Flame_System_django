from django.contrib import admin

from .models import Perfil


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'activo', 'telefono', 'fecha_creacion')
    list_filter = ('rol', 'activo')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name')
    autocomplete_fields = ('usuario',)
