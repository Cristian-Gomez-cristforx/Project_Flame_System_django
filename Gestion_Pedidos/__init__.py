"""
App de pedidos: creación, flujo por cocina, cobro y facturación.

Es el corazón operativo del sistema. Toma los productos y bebidas del
catálogo (app Inventario), los combina en pedidos, los mueve por sus
estados, descuenta stock cuando corresponde y emite la factura.

Prefijo de URL: /pedidos/    (namespace: pedidos)

Qué cubre
---------
- Mesas: alta, edición, eliminación y estado ocupada/libre.
- Pedidos: tipo mesa o para llevar; líneas de productos y bebidas.
- Flujo por estados:
      PENDIENTE -> COCINA -> COCINADO -> PAGADO -> FINALIZADO
                                             |
                                             +---> CANCELADO (desde varios estados)
  La transición a COCINA valida stock y descuenta insumos y bebidas.
  La cancelación restaura el stock si ya se había descontado.
- Cocina: tablero con los pedidos PENDIENTE y COCINA para el cocinero.
- Cobro: registra tipo de pago y marca el pedido como PAGADO.
- Factura: PDF tipo ticket (80mm) con reportlab, generado bajo demanda
  cuando el pedido ya está COCINADO.

Estructura interna
------------------
- models.py    : Mesa, Pedido, DetallePedidoProducto, DetallePedidoBebida,
                 DetallePedidoInsumo (receta congelada al agregar producto).
- forms.py     : Formularios de crear pedido, agregar producto/bebida,
                 mesa, pago y filtros del listado.
- views.py     : Capa HTTP: recibe requests, valida forms, renderiza
                 templates y genera el PDF de factura.
- services.py  : Reglas de negocio: crear_pedido, agregar_producto/bebida,
                 cambiar_estado (con validación y descuento de stock),
                 registrar_pago, eliminar_item, calcular_totales.
- urls.py      : Rutas del módulo.
- migrations/  : Migraciones de la base de datos.
- admin.py     : Registro de modelos en el admin de Django.

Templates asociados
-------------------
- templates/pedidos/  : lista, crear, detalle, cocina, cobrar, mesas y
                       formularios de mesa.

Separación views / services
---------------------------
Las vistas se mantienen delgadas: leen la request, invocan a services
y renderizan. Toda la lógica de estados, transacciones y cálculos vive
en services.py, para poder reutilizarla y testearla sin HTTP.
"""
