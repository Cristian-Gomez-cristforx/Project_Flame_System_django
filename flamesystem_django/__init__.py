"""
Paquete raíz del proyecto Flame System.

Este paquete NO es una app de Django; es el proyecto en sí. Aquí vive la
configuración global y el router principal que monta todas las apps.

Estructura interna
------------------
- settings.py  : Configuración global (INSTALLED_APPS, base de datos, email,
                 rutas de templates y static, MEDIA_ROOT, etc.).
- urls.py      : Router raíz. Monta cada app bajo un prefijo:
                     /cuentas/    -> login_modify_django
                     /inventario/ -> Inventario
                     /pedidos/    -> Gestion_Pedidos
                     /reportes/   -> Reportes
                 y redirige "/" al dashboard.
- wsgi.py      : Entrypoint para servidores WSGI (gunicorn, uWSGI).
- asgi.py      : Entrypoint para servidores ASGI (uvicorn, daphne).

Nada de lógica de negocio vive aquí; solo la configuración y el cableado
de rutas entre apps.
"""
