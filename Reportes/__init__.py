"""
App de reportes: dashboards, agregados y exportables en PDF.

Es una app de solo lectura: no crea ni modifica datos, solo consulta
los modelos de Inventario y Gestion_Pedidos para construir reportes
consolidados. Está restringida al rol de administrador.

Prefijo de URL: /reportes/    (namespace: reportes)

Qué cubre
---------
- Dashboard: KPIs generales del rango seleccionado (ventas, mermas,
  estado de inventario y top productos).
- Ventas: resumen del rango, top productos, top bebidas y pedidos
  pagados/finalizados por día.
- Mermas: agregado por motivo y por insumo, con costo total.
- Inventario: clasificación de insumos en ok, stock bajo y sin turno.
- Descarga PDF: reporte A4 de pedidos del rango con marca de agua,
  encabezado, tabla detallada y totales.

Rango por defecto: los últimos 7 días (hoy incluido). Puede ajustarse
con el formulario de fechas en cada vista.

Estructura interna
------------------
- services.py  : Agregaciones sobre pedidos, mermas e inventario.
                 Funciones puras que reciben rango y devuelven diccionarios
                 o querysets listos para renderizar.
- views.py     : Capa HTTP: interpreta el rango de la request, llama a
                 services y renderiza el template. También aloja la
                 vista descargar_reporte_pedidos que genera el PDF con
                 reportlab.
- forms.py     : Formulario RangoFechasForm.
- urls.py      : Rutas del módulo.
- migrations/  : Aunque no define modelos propios, mantiene el paquete
                 de migraciones estándar de Django.
- admin.py     : Sin registros (la app no tiene modelos).

Templates asociados
-------------------
- templates/reportes/  : dashboard, ventas, mermas, inventario y el
                        partial _filtro.html reutilizado.

Nota sobre la marca de agua
---------------------------
El PDF descargable usa un logo con opacidad reducida como marca de agua
(_logo_marca_agua en views.py). El resultado se cachea en memoria del
proceso para no repetir el procesamiento PIL en cada request.
"""
