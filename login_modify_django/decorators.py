from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .models import Perfil


def _tiene_rol(user, roles_permitidos):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        perfil = user.perfil
    except Perfil.DoesNotExist:
        return False
    if not perfil.activo:
        return False
    return perfil.rol in roles_permitidos


def rol_requerido(*roles):
    roles_permitidos = set(roles)

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            if _tiene_rol(request.user, roles_permitidos):
                return view_func(request, *args, **kwargs)
            messages.error(request, 'No tienes permiso para acceder a esta sección.')
            return redirect('login_modify:dashboard')
        return _wrapped
    return decorator


def admin_requerido(view_func):
    return rol_requerido(Perfil.Rol.ADMIN)(view_func)


class RolRequeridoMixin:
    roles_permitidos = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_modify:login')
        if not _tiene_rol(request.user, set(self.roles_permitidos)):
            raise PermissionDenied('No tienes permiso para acceder a esta sección.')
        return super().dispatch(request, *args, **kwargs)
