from django.contrib import admin
from .models import (Insumo, Producto,  Bebida, RecetaProducto,  DetalleReceta,  Merma)
from django.utils.safestring import mark_safe



# ====================== INSUMO ======================
from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Insumo


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = [
        'id_insumo', 
        'nombre_insumo', 
        'cantidad_insumo', 
        'unidad_medida', 
        'stock_maximo',
        'porcentaje_del_maximo',
        'alerta_stock'
    ]
    search_fields = ['nombre_insumo']
    list_filter = ['unidad_medida']
    ordering = ['nombre_insumo']
    actions = ['abrir_turno', 'cierre_de_turno']

    def alerta_stock(self, obj):
        if obj.bajo_stock_30:
            return mark_safe('<span style="color:red; font-weight:bold;"> Bajo Stock</span>')
        else:
            return mark_safe('<span style="color:green;">OK</span>')
    
    alerta_stock.short_description = "Alerta Stock"

    # ====================== ABRIR TURNO ======================
    @admin.action(description="Abrir Turno (Establecer stock máximo actual)")
    def abrir_turno(self, request, queryset):
        for insumo in queryset:
            insumo.abrir_turno()
        self.message_user(request, f" Se actualizó el stock máximo de {queryset.count()} insumo(s).")

    # ====================== CIERRE DE TURNO ======================
    @admin.action(description="Cierre de Turno (Resetear stock máximo a 0)")
    def cierre_de_turno(self, request, queryset):
        for insumo in queryset:
            insumo.stock_maximo = 0
            insumo.save(update_fields=['stock_maximo'])
        self.message_user(request, f" Se cerró el turno de {queryset.count()} insumo(s). Stock máximo reseteado a 0.")


# ====================== PRODUCTO ======================
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['id_producto', 'nombre_producto', 'categoria', 'precio_producto', 'activo']
    search_fields = ['nombre_producto']
    list_filter = ['categoria', 'activo']
    ordering = ['nombre_producto']
    exclude = ['categoria']


# ====================== BEBIDA ======================
@admin.register(Bebida)
class BebidaAdmin(admin.ModelAdmin):
    list_display = ['id_bebida', 'nombre_bebida', 'categoria', 'tamaño_bebida', 'cantidad_bebida', 'precio_venta', 'estado_stock']
    search_fields = ['nombre_bebida']
    list_filter = ['categoria', 'tamaño_bebida']
    ordering = ['nombre_bebida']
    exclude = ['categoria']

    def estado_stock(self, obj):
        if obj.cantidad_bebida == 0:
            return mark_safe('<span style="color:red; font-weight:bold;">Agotado</span>')
        elif obj.cantidad_bebida < 10:
            return mark_safe('<span style="color:orange; font-weight:bold;">Bajo stock</span>')
        else:
            return mark_safe('<span style="color:green;">OK</span>')

    estado_stock.short_description = "Stock"


# ====================== DETALLE DE RECETA ======================
class DetalleRecetaInline(admin.TabularInline):
    model = DetalleReceta
    extra = 1
    fields = ['insumo', 'cantidad_requerida']


# ====================== RECETA PRODUCTO ======================
@admin.register(RecetaProducto)
class RecetaProductoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'activa', 'unidades_posibles']
    list_filter = ['activa']
    search_fields = ['producto__nombre_producto']
    inlines = [DetalleRecetaInline]

    def unidades_posibles(self, obj):
       
        cantidad = obj.cuantas_unidades_posibles()
        if cantidad > 0:
            return f" {cantidad} unidades"
        else:
            return " Sin stock suficiente"
    
    unidades_posibles.short_description = "Puede Preparar"

# ====================== MERMAS ======================
@admin.register(Merma)
class MermaAdmin(admin.ModelAdmin):
    list_display = ['id_merma', 'insumo', 'cantidad_insumo_dañado', 'motivo', 'costo_total_merma', 'fecha_merma', 'responsable']
    search_fields = ['insumo__nombre_insumo', 'motivo', 'responsable']
    list_filter = ['motivo', 'fecha_merma']
    ordering = ['-fecha_merma']
    
    readonly_fields = ['fecha_merma', 'precio_insumo', 'costo_total_merma']

   
    def cantidad_insumo_dañado(self, obj):
        return obj.cantidad_mermada
    
    cantidad_insumo_dañado.short_description = "Cantidad Insumo Dañado"

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ['insumo', 'cantidad_mermada']
        return self.readonly_fields