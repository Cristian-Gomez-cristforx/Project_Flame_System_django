"""
App de cuentas: autenticación, perfiles y gestión de usuarios.

Es la única app que toca el modelo User y sus datos asociados. Por eso
concentra en un solo módulo todo lo relacionado con identidad, evitando
que la lógica de cuentas quede dispersa entre varias apps.

Prefijo de URL: /cuentas/    (namespace: login_modify)

Qué cubre
---------
- Autenticación: login, logout, dashboard de entrada según rol.
- Recuperación de contraseña en 3 pasos:
      1) Solicitar código  -> envía un PIN al correo del usuario.
      2) Verificar código  -> valida el PIN y emite un token firmado.
      3) Cambiar contraseña -> aplica la nueva contraseña.
- CRUD de usuarios: listar, crear, editar y activar/desactivar.
- Modelo Perfil: extiende User con rol (Admin/Mesero/Cocinero),
  teléfono, documento y estado activo.

Estructura interna
------------------
- models.py       : Perfil (1-1 con User) y RecuperacionContrasena (PIN + vigencia).
- forms.py        : Formularios de login, recuperación y CRUD de usuarios.
- views.py        : Vistas HTTP de login, dashboard, recuperación y usuarios.
- decorators.py   : @admin_requerido y @rol_requerido para proteger vistas.
- urls.py         : Rutas de la app.
- migrations/     : Migraciones de la base de datos.
- admin.py        : Registro de modelos en el admin de Django.

Templates asociados
-------------------
- templates/auth/          : login, recuperación, CRUD de usuarios, dashboard.
- templates/emails/        : plantilla HTML del correo con el PIN.

Nota: aunque el nombre del paquete es `login_modify_django`, la app
cubre la gestión completa de cuentas, no solo el login.
"""
