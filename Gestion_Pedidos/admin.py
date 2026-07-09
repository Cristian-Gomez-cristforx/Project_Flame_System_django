from django.contrib import admin
from .models import Pedido, DetallePedidoProducto, DetallePedidoBebida,DetallePedidoInsumo, Mesa


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero_mesa', 'activa', 'ocupada')
    list_filter = ('activa', 'ocupada')

# Register your models here.

class DetallePedidoProductoInline(admin.TabularInline):
    model = DetallePedidoProducto
    extra = 0
    readonly_fields = ('precio_unitario','subtotal',)

    

    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(
           db_field,
           request,
           **kwargs)
        if db_field.name == "producto":
            field.widget.can_add_related = False
            field.widget.can_change_related = False
            field.widget.can_delete_related = False
            field.widget.can_view_related = True
        return field

class DetallePedidoBebidaInline(admin.TabularInline):
    model = DetallePedidoBebida
    extra = 0
    readonly_fields = ('precio_unitario','subtotal',)
    

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    readonly_fields = ('numero_factura',)
    list_display = [
        'estado',
        'tipo',
        'nombre_cliente',
        'telefono_cliente',
        'mesero',
        'fecha_creacion'
    ]
    
    
    search_fields = ['nombre_cliente','telefono_cliente']
    
    list_filter = ['estado','tipo']
    inlines = [
        DetallePedidoProductoInline,
        DetallePedidoBebidaInline
    ]
@admin.register(DetallePedidoProducto)
class DetallePedidoProductoAdmin(admin.ModelAdmin):

    list_display = ['pedido','producto','cantidad',    ]

   

@admin.register(DetallePedidoBebida)
class DetallePedidoBebidaAdmin(admin.ModelAdmin):

    list_display = ['pedido','bebida','cantidad']



@admin.register(DetallePedidoInsumo)
class DetallePedidoInsumoAdmin(admin.ModelAdmin):

    list_display = ['detalle_producto','insumo','cantidad_requerida','precio_insumo','usar']


    