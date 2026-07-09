from django.contrib import messages
from django.contrib.auth import get_user_model, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST

from .decorators import admin_requerido
from .forms import LoginForm, UsuarioCreateForm, UsuarioEditForm
from .models import Perfil


User = get_user_model()


class FlameLoginView(LoginView):
    template_name = 'auth/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('login_modify:dashboard')

    def form_invalid(self, form):
        messages.error(self.request, 'Usuario o contraseña incorrectos.')
        return super().form_invalid(form)


def logout_view(request):
    django_logout(request)
    messages.info(request, 'Sesión cerrada.')
    return redirect('login_modify:login')


@login_required(login_url='login_modify:login')
def dashboard(request):
    perfil = getattr(request.user, 'perfil', None)

    if perfil and not perfil.activo and not request.user.is_superuser:
        django_logout(request)
        messages.error(request, 'Tu cuenta está inactiva. Contacta al administrador.')
        return redirect('login_modify:login')

    rol = perfil.rol if perfil else Perfil.Rol.ADMIN

    context = {
        'perfil': perfil,
        'rol': rol,
    }
    return render(request, 'auth/dashboard.html', context)


@admin_requerido
def usuarios_lista(request):
    q = (request.GET.get('q') or '').strip()
    rol = (request.GET.get('rol') or '').strip()

    usuarios = (
        User.objects
        .select_related('perfil')
        .exclude(is_superuser=True)
        .order_by('-date_joined')
    )

    if q:
        usuarios = usuarios.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q) |
            Q(perfil__documento__icontains=q)
        )
    if rol:
        usuarios = usuarios.filter(perfil__rol=rol)

    return render(request, 'auth/usuarios_lista.html', {
        'usuarios': usuarios,
        'q': q,
        'rol_filtro': rol,
        'roles': Perfil.Rol.choices,
    })


@admin_requerido
def usuario_crear(request):
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuario "{user.username}" creado correctamente.')
            return redirect('login_modify:usuarios_lista')
    else:
        form = UsuarioCreateForm()

    return render(request, 'auth/usuario_form.html', {
        'form': form,
        'modo': 'crear',
    })


@admin_requerido
def usuario_editar(request, user_id):
    usuario = get_object_or_404(
        User.objects.select_related('perfil').exclude(is_superuser=True),
        pk=user_id,
    )
    if request.method == 'POST':
        form = UsuarioEditForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario "{usuario.username}" actualizado.')
            return redirect('login_modify:usuarios_lista')
    else:
        form = UsuarioEditForm(instance=usuario)

    return render(request, 'auth/usuario_form.html', {
        'form': form,
        'modo': 'editar',
        'usuario': usuario,
    })


@admin_requerido
@require_POST
def usuario_toggle_activo(request, user_id):
    usuario = get_object_or_404(
        User.objects.select_related('perfil').exclude(is_superuser=True),
        pk=user_id,
    )
    perfil = usuario.perfil
    perfil.activo = not perfil.activo
    perfil.save()
    estado = 'activado' if perfil.activo else 'desactivado'
    messages.success(request, f'Usuario "{usuario.username}" {estado}.')
    return redirect('login_modify:usuarios_lista')
