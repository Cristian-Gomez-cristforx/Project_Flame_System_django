"""
Sincronización de grupos y permisos nativos de Django a partir de Perfil.rol.

La fuente de verdad sigue siendo Perfil.rol. Este módulo espeja esa
información en las tablas nativas de Django (auth_group, auth_permission,
auth_user_groups) para que también estén disponibles las herramientas
estándar: user.has_perm, permission_required, filtros del admin, etc.
"""
from django.apps import apps as global_apps
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


ROL_GRUPO = {
    'ADMIN':    'Administradores',
    'MESERO':   'Meseros',
    'COCINERO': 'Cocineros',
}

CRUD = ('add', 'change', 'delete', 'view')
V    = ('view',)
VC   = ('view', 'change')
VA   = ('view', 'add')


def _modelos_admin():
    """Todos los modelos de nuestras apps (a los que el ADMIN tiene CRUD completo)."""
    return [
        *global_apps.get_app_config('login_modify_django').get_models(),
        *global_apps.get_app_config('Inventario').get_models(),
        *global_apps.get_app_config('Gestion_Pedidos').get_models(),
    ]


def _perms_por_rol():
    """Devuelve el mapeo rol -> [(modelo, acciones), ...] con los permisos deseados."""
    Insumo         = global_apps.get_model('Inventario', 'Insumo')
    Producto       = global_apps.get_model('Inventario', 'Producto')
    Bebida         = global_apps.get_model('Inventario', 'Bebida')

    Mesa           = global_apps.get_model('Gestion_Pedidos', 'Mesa')
    Pedido         = global_apps.get_model('Gestion_Pedidos', 'Pedido')
    DPP            = global_apps.get_model('Gestion_Pedidos', 'DetallePedidoProducto')
    DPB            = global_apps.get_model('Gestion_Pedidos', 'DetallePedidoBebida')
    DPI            = global_apps.get_model('Gestion_Pedidos', 'DetallePedidoInsumo')

    return {
        'ADMIN': [(m, CRUD) for m in _modelos_admin()],
        'MESERO': [
            (Pedido,   ('add', 'change', 'view')),
            (DPP,      CRUD),
            (DPB,      CRUD),
            (DPI,      VC),
            (Mesa,     VA),
            (Producto, V),
            (Bebida,   V),
        ],
        'COCINERO': [
            (Pedido,   VC),
            (DPP,      V),
            (DPB,      V),
            (Mesa,     V),
            (Producto, V),
            (Insumo,   V),
        ],
    }


def _asegurar_permisos_existentes():
    """Fuerza la creación de los Permission de todos los modelos aunque auth aún no haya migrado."""
    from django.contrib.auth.management import create_permissions
    for config in global_apps.get_app_configs():
        create_permissions(config, verbosity=0, apps=global_apps)


def sincronizar_grupos():
    """Crea (o actualiza) los 3 grupos con el conjunto de permisos correspondiente a cada rol."""
    _asegurar_permisos_existentes()
    for rol, entradas in _perms_por_rol().items():
        nombre = ROL_GRUPO[rol]
        grupo, _ = Group.objects.get_or_create(name=nombre)
        perms = []
        for modelo, acciones in entradas:
            ct = ContentType.objects.get_for_model(modelo)
            for accion in acciones:
                codename = f'{accion}_{ct.model}'
                perm = Permission.objects.filter(content_type=ct, codename=codename).first()
                if perm:
                    perms.append(perm)
        grupo.permissions.set(perms)


def sincronizar_grupo_usuario(usuario, rol):
    """Deja al usuario solo en el grupo que corresponde a su rol actual."""
    nombres = list(ROL_GRUPO.values())
    esperado_nombre = ROL_GRUPO.get(rol)
    if not esperado_nombre:
        return
    grupo, _ = Group.objects.get_or_create(name=esperado_nombre)
    otros = usuario.groups.filter(name__in=nombres).exclude(pk=grupo.pk)
    if otros.exists():
        usuario.groups.remove(*otros)
    if not usuario.groups.filter(pk=grupo.pk).exists():
        usuario.groups.add(grupo)


def sincronizar_todos_los_usuarios():
    """Recorre todos los Perfiles y sincroniza el grupo de cada usuario."""
    Perfil = global_apps.get_model('login_modify_django', 'Perfil')
    from django.contrib.auth import get_user_model
    User = get_user_model()
    for perfil in Perfil.objects.all():
        try:
            user = User.objects.get(pk=perfil.usuario_id)
        except User.DoesNotExist:
            continue
        sincronizar_grupo_usuario(user, perfil.rol)
