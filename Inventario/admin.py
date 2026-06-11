from django.contrib import admin
from .models import Categoria, Insumo, Producto, Bebida, RecetaProducto, DetalleReceta


# ====================== CATEGORÍA ======================
@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre_categoria', 'descripcion']
    search_fields = ['nombre_categoria']
    ordering = ['nombre_categoria']


# ====================== INSUMO ======================
@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    list_display = ['id_insumo', 'nombre_insumo', 'cantidad_insumo', 'unidad_medida', 'precio_insumo']
    #                                                                  ↑ campo nuevo
    search_fields = ['nombre_insumo']
    list_filter = ['unidad_medida']   # ← ahora filtra por unidad, más útil
    ordering = ['nombre_insumo']


# ====================== PRODUCTO ======================
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['id_producto', 'nombre_producto', 'categoria', 'precio_producto']
    search_fields = ['nombre_producto']
    list_filter = ['categoria']
    ordering = ['nombre_producto']


# ====================== BEBIDA ======================
@admin.register(Bebida)
class BebidaAdmin(admin.ModelAdmin):
    list_display = ['id_bebida', 'nombre_bebida', 'categoria', 'precio_venta', 'tipo_bebida', 'tamaño_bebida']
    search_fields = ['nombre_bebida']
    list_filter = ['categoria', 'tipo_bebida', 'tamaño_bebida']
    ordering = ['nombre_bebida']


# ====================== DETALLE DE RECETA (inline) ======================
class DetalleRecetaInline(admin.TabularInline):
    """
    Esto permite agregar los insumos de la receta
    directamente desde la pantalla de la RecetaProducto.
    Sin necesidad de ir a otra pantalla.
    """
    model = DetalleReceta
    extra = 3          # Muestra 3 filas vacías listas para llenar
    fields = ['insumo', 'cantidad_requerida']   # unidad ya no se pide aquí


# ====================== RECETA PRODUCTO ======================
@admin.register(RecetaProducto)
class RecetaProductoAdmin(admin.ModelAdmin):
    list_display = ['producto', 'activa', 'unidades_posibles']
    list_filter = ['activa']
    search_fields = ['producto__nombre_producto']
    inlines = [DetalleRecetaInline]   # ← muestra los ingredientes dentro de la receta

    def unidades_posibles(self, obj):
        """Columna que muestra cuántas unidades se pueden hacer hoy"""
        return f"{obj.cuantas_unidades_posibles()} unidades"
    unidades_posibles.short_description = "Puede preparar"