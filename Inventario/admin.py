from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Insumo, Producto, Bebida, RecetaProducto, DetalleReceta, Merma, Categoria
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError



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
                    'unidad_medida', 'stock_maximo', 'porcentaje_formateado',
                    'alerta_stock', 'precio_formateado','precio_gramo']
    
    readonly_fields = ['stock_maximo', 'precio_gramo',]
    search_fields = ['nombre_insumo']
    list_filter = ['unidad_medida', 'categoria']
    ordering = ['nombre_insumo']
    actions = ['abrir_turno', 'cierre_de_turno']
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'categoria':
            kwargs['queryset'] = Categoria.objects.filter(tipo=Categoria.Tipo.INSUMO)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def porcentaje_formateado(self, obj):
        return f"{obj.porcentaje_del_maximo}%"
    porcentaje_formateado.short_description = 'PORCENTAJE LIMITE'
    
    def precio_formateado(self, obj):
        return f"${obj.precio_insumo:,.0f}".replace(',','.')
    precio_formateado.short_description = 'Precio Insumo'


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
    list_display = ['id_producto', 'nombre_producto', 'categoria', 'precio_producto_formateado', 'activo']
    search_fields = ['nombre_producto']
    list_filter = ['activo', 'categoria']
    ordering = ['nombre_producto']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'categoria':
            kwargs['queryset'] = Categoria.objects.filter(tipo=Categoria.Tipo.PRODUCTO)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def precio_producto_formateado(self, obj):
        return f"${obj.precio_producto:,.0f}".replace(",", ".")

    precio_producto_formateado.short_description = "Precio Venta"
    precio_producto_formateado.admin_order_field = "precio_producto"
    

@admin.register(Bebida)
class BebidaAdmin(admin.ModelAdmin):
    list_display = ['id_bebida', 'nombre_bebida', 'categoria', 'tamaño_bebida',
                    'cantidad_bebida', 'precio_venta_formateado', 'estado_stock','precio_unitario_compra','precio_unitario_venta']
    search_fields = ['nombre_bebida']
    list_filter = ['tamaño_bebida', 'categoria']
    ordering = ['nombre_bebida']
    readonly_fields=[]
    exclude = ['precio_unitario_compra','precio_unitario_venta','bajo_stock_30']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'categoria':
            kwargs['queryset'] = Categoria.objects.filter(tipo=Categoria.Tipo.BEBIDA)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def precio_venta_formateado(self, obj):
        return f"${obj.precio_venta:,.0f}".replace(",", ".")

    precio_venta_formateado.short_description = "Precio Venta"
    precio_venta_formateado.admin_order_field = "precio_venta"
        
        

    def estado_stock(self, obj):
        if obj.cantidad_bebida == 0:
            return mark_safe('<span style="color:red; font-weight:bold;">Agotado</span>')
        elif obj.cantidad_bebida < 10:
            return mark_safe('<span style="color:orange; font-weight:bold;">Bajo stock</span>')
        return mark_safe('<span style="color:green;">OK</span>')
    estado_stock.short_description = 'Stock'
    
    def precio_unitario_compra(self, obj):
        return(
            f"${obj.precio_unitario_compra:,.0f}".replace(',','.')
        )
        
    precio_unitario_compra.short_description = 'precio_uni_compra'
    
    def precio_unitario_venta(self, obj):
        return(
            f"${obj.precio_unitario_venta:,.0f}".replace(',','.')
        )
    precio_unitario_venta.short_description = 'precio_uni_venta'


# ====================== DETALLE DE RECETA ======================
class DetalleRecetaInlineFormSet(BaseInlineFormSet):

    def clean(self):
        super().clean()

        cantidad_detalles = 0

        for form in self.forms:

            # Ignorar formularios vacíos
            if not form.cleaned_data:
                continue

            # Ignorar los que se eliminarán
            if form.cleaned_data.get("DELETE", False):
                continue

            # Si tiene un insumo seleccionado, cuenta como válido
            if form.cleaned_data.get("insumo"):
                cantidad_detalles += 1

        if cantidad_detalles == 0:
            raise ValidationError(
                "La receta debe tener al menos un insumo."
            )


class DetalleRecetaInline(admin.TabularInline):
    model = DetalleReceta
    formset = DetalleRecetaInlineFormSet
    extra = 1
    fields = ['insumo', 'cantidad_requerida','mostrar_costo']
    readonly_fields = ['mostrar_costo']
    
    def mostrar_costo(self, obj):
        if obj.pk:
            return(
                f"${obj.costo_detalle:,.0f}".replace(',','.')
            )
        return "$0"
    mostrar_costo.short_description = 'Precio cantidad'
    
    
        
@admin.register(RecetaProducto)
class RecetaProductoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'activa', 'unidades_posibles','costo_preparacion_formateado',]
    list_filter = ['activa']
    search_fields = ['producto__nombre_producto']
    inlines = [DetalleRecetaInline]
    

    
    
    def costo_preparacion_formateado(self, obj):
        return f"${obj.costo_preparacion:,.0f}".replace(',','.')
    
    costo_preparacion_formateado.short_description = 'Costo de Preparación'

    def unidades_posibles(self, obj):
        cantidad = obj.cuantas_unidades_posibles()
        return f"{cantidad} unidades" if cantidad > 0 else "Sin stock suficiente"
    unidades_posibles.short_description = 'Puede Preparar'


@admin.register(Merma)
class MermaAdmin(admin.ModelAdmin):
    list_display = ['id_merma', 'insumo_snapshot', 'cantidad_insumo_dañado', 'motivo',
                    'costo_total_formateado', 'fecha_merma', 'responsable',]
    search_fields = ['insumo__nombre_insumo', 'motivo', 'responsable']
    list_filter = ['motivo', 'fecha_merma']
    ordering = ['-fecha_merma']
    readonly_fields = ['fecha_merma', 'precio_insumo', 'costo_total_merma']
    exclude = ['insumo_snapshot']
    
    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)
    
    def costo_total_formateado(self, obj):
        return f"${obj.costo_total_merma:,.0f}".replace(',','.')
    costo_total_formateado.short_description = 'COSTO TOTAL MERMA'

    def cantidad_insumo_dañado(self, obj):
        return obj.cantidad_mermada
    cantidad_insumo_dañado.short_description = 'Cantidad Insumo Dañado'
    
    def insumo_snapshot(self, obj):
        return obj.insumo_snapshot
    insumo_snapshot.short_description = 'INSUMO AFECTADO'

    