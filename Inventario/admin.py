from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Insumo, Producto, Bebida, RecetaProducto, DetalleReceta, Merma, Categoria



# ====================== CATEGORÍA ======================
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display    = ['id', 'nombre_categoria', 'tipo']
    list_filter     = ['tipo']
    search_fields   = ['nombre_categoria']
    ordering        = ['tipo', 'nombre_categoria']
    



    def has_module_permission(self,request):
       return False



# ====================== INSUMO, PRODUCTO Y BEBIDA ======================
@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ['id_insumo', 'nombre_insumo', 'categoria', 'cantidad_insumo',
                    'unidad_medida', 'stock_maximo', 'porcentaje_del_maximo',
                    'alerta_stock', 'precio_formateado']
    readonly_fields = ('stock_maximo',)
    search_fields = ['nombre_insumo']
    list_filter = ['unidad_medida', 'categoria']
    ordering = ['nombre_insumo']
    actions = ['abrir_turno', 'cierre_de_turno']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'categoria':
            kwargs['queryset'] = Categoria.objects.filter(tipo=Categoria.Tipo.INSUMO)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description='Precio Insumo')
    def precio_formateado(self, obj):
        return f"${obj.precio_insumo:,.0f}"

    def alerta_stock(self, obj):
        if obj.bajo_stock_30:
            return mark_safe('<span style="color:red; font-weight:bold;">Bajo Stock</span>')
        return mark_safe('<span style="color:green;">OK</span>')
    alerta_stock.short_description = 'Alerta Stock'

    @admin.action(description='Abrir Turno (Establecer stock máximo actual)')
    def abrir_turno(self, request, queryset):
        for insumo in queryset:
            insumo.abrir_turno()
        self.message_user(request, f"Se actualizó el stock máximo de {queryset.count()} insumo(s).")

    @admin.action(description='Cierre de Turno (Resetear stock máximo a 0)')
    def cierre_de_turno(self, request, queryset):
      updated = queryset.update(stock_maximo=0)
      self.message_user(request, f"Se cerró el turno de {updated} insumo(s).")   


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['id_producto', 'nombre_producto', 'categoria', 'precio_producto', 'activo']
    search_fields = ['nombre_producto']
    list_filter = ['activo', 'categoria']
    ordering = ['nombre_producto']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'categoria':
            kwargs['queryset'] = Categoria.objects.filter(tipo=Categoria.Tipo.PRODUCTO)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Bebida)
class BebidaAdmin(admin.ModelAdmin):
    list_display = ['id_bebida', 'nombre_bebida', 'categoria', 'tamaño_bebida',
                    'cantidad_bebida', 'precio_venta', 'estado_stock']
    search_fields = ['nombre_bebida']
    list_filter = ['tamaño_bebida', 'categoria']
    ordering = ['nombre_bebida']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'categoria':
            kwargs['queryset'] = Categoria.objects.filter(tipo=Categoria.Tipo.BEBIDA)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def estado_stock(self, obj):
        if obj.cantidad_bebida == 0:
            return mark_safe('<span style="color:red; font-weight:bold;">Agotado</span>')
        elif obj.cantidad_bebida < 10:
            return mark_safe('<span style="color:orange; font-weight:bold;">Bajo stock</span>')
        return mark_safe('<span style="color:green;">OK</span>')
    estado_stock.short_description = 'Stock'


# ====================== DETALLE DE RECETA ======================
class DetalleRecetaInline(admin.TabularInline):
    model = DetalleReceta
    extra = 1
    fields = ['insumo', 'cantidad_requerida']


@admin.register(RecetaProducto)
class RecetaProductoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'activa', 'unidades_posibles']
    list_filter = ['activa']
    search_fields = ['producto__nombre_producto']
    inlines = [DetalleRecetaInline]

    def unidades_posibles(self, obj):
        cantidad = obj.cuantas_unidades_posibles()
        return f"{cantidad} unidades" if cantidad > 0 else "Sin stock suficiente"
    unidades_posibles.short_description = 'Puede Preparar'


@admin.register(Merma)
class MermaAdmin(admin.ModelAdmin):
    list_display = ['id_merma', 'insumo', 'cantidad_insumo_dañado', 'motivo',
                    'costo_total_merma', 'fecha_merma', 'responsable']
    search_fields = ['insumo__nombre_insumo', 'motivo', 'responsable']
    list_filter = ['motivo', 'fecha_merma']
    ordering = ['-fecha_merma']
    readonly_fields = ['fecha_merma', 'precio_insumo', 'costo_total_merma']

    def cantidad_insumo_dañado(self, obj):
        return obj.cantidad_mermada
    cantidad_insumo_dañado.short_description = 'Cantidad Insumo Dañado'

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['insumo', 'cantidad_mermada']
        return self.readonly_fields
    

class FlameAdminSite(admin.AdminSite):
    # Declaramos el archivo CSS de tus colores naranjas
    class Media:
        css = {
            'all': ('css/admin_personalizado.css',)
        }

# Reemplazamos el sitio de administración por defecto con el tuyo personalizado
admin.site.__class__ = FlameAdminSite

