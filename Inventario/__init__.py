"""
App de inventario: insumos, productos, bebidas, categorías, mermas y turnos.

Es el catálogo maestro del sistema. Define QUÉ se vende (productos y
bebidas), CON QUÉ se prepara (insumos y recetas), y CÓMO se controla
el stock (turnos y mermas). Las demás apps consumen estos datos.

Prefijo de URL: /inventario/    (namespace: inventario)

Qué cubre
---------
- Insumos: materias primas con unidad de medida (gramos o unidades),
  precio, stock actual y stock_maximo (referencia del turno).
- Productos: platos que se venden. Tienen una receta (RecetaProducto)
  que lista los insumos y cantidades necesarios por unidad preparada.
- Bebidas: se venden como producto terminado, con tamaño y precios
  de compra/venta.
- Categorías: agrupación de insumos, productos o bebidas por tipo.
- Mermas: registro de pérdidas de insumo con motivo; descuenta stock
  automáticamente vía el modelo.
- Turnos: abrir/cerrar el ciclo operativo. Al abrir se fija stock_maximo
  como referencia para calcular "stock bajo"; al cerrar se limpia.
- Reposición: agregar stock a un insumo existente.

Estructura interna
------------------
- models.py    : Insumo, Producto, RecetaProducto (+ detalles), Bebida,
                 Categoria, Merma, Turno.
- forms.py     : Formularios y formsets (la receta se maneja como formset).
- views.py     : Vistas CRUD por entidad + endpoints de turno y stock.
- urls.py      : Rutas del módulo.
- migrations/  : Migraciones de la base de datos.
- admin.py     : Registro de modelos en el admin de Django.

Templates asociados
-------------------
- templates/temp_inventario/  : listar/crear/editar de cada entidad y
                                el partial _categoria_field.html reutilizado.

No hay services.py: la lógica del módulo es principalmente CRUD directo,
y las pocas reglas de negocio (descuento de merma, cálculo de stock bajo)
viven en los propios modelos.
"""
