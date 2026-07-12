from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout as django_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import admin_requerido
from .forms import (
    LoginForm,
    NuevaContrasenaForm,
    SolicitudRecuperacionForm,
    UsuarioCreateForm,
    UsuarioEditForm,
    VerificarPinForm,
)
from .models import Perfil, RecuperacionContrasena


_SIGNER_SALT = 'flamesystem.recuperacion'
_TOKEN_MAX_AGE_SEG = 15 * 60


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
    es_admin = request.user.is_superuser or (perfil and perfil.es_admin)
    es_mesero = perfil and perfil.es_mesero
    es_cocinero = perfil and perfil.es_cocinero

    from Gestion_Pedidos.models import Mesa, Pedido
    from Reportes import services as reportes_services

    hoy = timezone.localdate()

    estados_activos = [
        Pedido.EstadoPedido.PENDIENTE,
        Pedido.EstadoPedido.COCINA,
        Pedido.EstadoPedido.COCINADO,
        Pedido.EstadoPedido.PAGADO,
    ]

    kpis = {}
    ultimos_pedidos = []
    alertas_stock = []

    if es_admin:
        from Gestion_Pedidos.models import DetallePedidoBebida, DetallePedidoProducto

        estado_inv = reportes_services.estado_inventario()
        mesas_total = Mesa.objects.filter(activa=True).count()
        mesas_ocupadas = Mesa.objects.filter(activa=True, ocupada=True).count()

        finalizados_hoy = Pedido.objects.filter(
            estado=Pedido.EstadoPedido.FINALIZADO,
            fecha_actualizacion__date=hoy,
        )
        total_productos = DetallePedidoProducto.objects.filter(
            pedido__in=finalizados_hoy
        ).aggregate(total=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()))['total']
        total_bebidas = DetallePedidoBebida.objects.filter(
            pedido__in=finalizados_hoy
        ).aggregate(total=Coalesce(Sum('subtotal'), Value(Decimal('0')), output_field=DecimalField()))['total']

        kpis = {
            'ventas_hoy': total_productos + total_bebidas,
            'pedidos_hoy': finalizados_hoy.count(),
            'mesas_ocupadas': mesas_ocupadas,
            'mesas_total': mesas_total,
            'stock_bajo_count': len(estado_inv['stock_bajo']),
        }
        ultimos_pedidos = (
            Pedido.objects
            .select_related('mesa', 'mesero')
            .order_by('-fecha_creacion')[:6]
        )
        alertas_stock = estado_inv['stock_bajo'][:5]

    elif es_mesero:
        mesas_total = Mesa.objects.filter(activa=True).count()
        mesas_ocupadas = Mesa.objects.filter(activa=True, ocupada=True).count()
        mis_activos = Pedido.objects.filter(
            mesero=request.user, estado__in=estados_activos
        ).count()
        pedidos_hoy = Pedido.objects.filter(
            mesero=request.user, fecha_creacion__date=hoy
        ).count()

        kpis = {
            'mis_activos': mis_activos,
            'mesas_ocupadas': mesas_ocupadas,
            'mesas_total': mesas_total,
            'pedidos_hoy': pedidos_hoy,
        }
        ultimos_pedidos = (
            Pedido.objects
            .filter(mesero=request.user)
            .select_related('mesa')
            .order_by('-fecha_creacion')[:6]
        )

    elif es_cocinero:
        pendientes = Pedido.objects.filter(estado=Pedido.EstadoPedido.PENDIENTE).count()
        en_cocina = Pedido.objects.filter(estado=Pedido.EstadoPedido.COCINA).count()
        cocinados_hoy = Pedido.objects.filter(
            estado__in=[Pedido.EstadoPedido.COCINADO, Pedido.EstadoPedido.PAGADO, Pedido.EstadoPedido.FINALIZADO],
            fecha_actualizacion__date=hoy,
        ).count()

        kpis = {
            'pendientes': pendientes,
            'en_cocina': en_cocina,
            'cocinados_hoy': cocinados_hoy,
        }

    context = {
        'perfil': perfil,
        'rol': rol,
        'es_admin': es_admin,
        'es_mesero': es_mesero,
        'es_cocinero': es_cocinero,
        'hoy': hoy,
        'kpis': kpis,
        'ultimos_pedidos': ultimos_pedidos,
        'alertas_stock': alertas_stock,
    }
    return render(request, 'auth/dashboard.html', context)


def _buscar_usuario(identificador):
    return (
        User.objects
        .filter(Q(username__iexact=identificador) | Q(email__iexact=identificador))
        .first()
    )


def _enviar_pin_email(usuario, pin):
    asunto = 'Flame System · Código para recuperar tu contraseña'
    nombre = usuario.get_full_name() or usuario.get_username()
    contexto = {
        'username': nombre,
        'pin': pin,
        'pin_minutos': RecuperacionContrasena.PIN_VIGENCIA_MIN,
        'year': timezone.now().year,
    }
    cuerpo_texto = (
        f'Hola {nombre},\n\n'
        f'Recibimos una solicitud para restablecer la contraseña de tu cuenta.\n\n'
        f'Tu código de verificación es:  {pin}\n\n'
        f'Este código expira en {RecuperacionContrasena.PIN_VIGENCIA_MIN} minutos. '
        f'Si tú no solicitaste este cambio, ignora este correo.\n\n'
        f'— Flame System'
    )
    cuerpo_html = render_to_string('emails/recuperacion_pin.html', contexto)
    remitente = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or settings.EMAIL_HOST_USER
    mensaje = EmailMultiAlternatives(asunto, cuerpo_texto, remitente, [usuario.email])
    mensaje.attach_alternative(cuerpo_html, 'text/html')
    mensaje.send(fail_silently=False)


def recuperar_solicitar(request):
    if request.user.is_authenticated:
        return redirect('login_modify:dashboard')

    if request.method == 'POST':
        form = SolicitudRecuperacionForm(request.POST)
        if form.is_valid():
            identificador = form.cleaned_data['identificador']
            usuario = _buscar_usuario(identificador)
            if not usuario:
                messages.error(request, 'No encontramos ningún usuario con ese usuario o correo.')
            elif not usuario.is_active:
                messages.error(request, 'La cuenta está inactiva. Contacta al administrador.')
            elif not usuario.email:
                messages.error(request, 'Este usuario no tiene un correo asociado. Contacta al administrador.')
            else:
                recup, pin = RecuperacionContrasena.generar_para(usuario)
                try:
                    _enviar_pin_email(usuario, pin)
                except Exception:
                    messages.error(request, 'No fue posible enviar el correo. Intenta de nuevo más tarde.')
                    return render(request, 'auth/recuperar_solicitar.html', {'form': form})
                request.session['recup_id'] = recup.pk
                email = usuario.email
                arroba = email.find('@')
                messages.info(request, f'Enviamos un código al correo {email[:2]}***{email[arroba:]}.')
                return redirect('login_modify:recuperar_verificar')
    else:
        form = SolicitudRecuperacionForm()

    return render(request, 'auth/recuperar_solicitar.html', {'form': form})


def recuperar_verificar(request):
    if request.user.is_authenticated:
        return redirect('login_modify:dashboard')

    recup_id = request.session.get('recup_id')
    if not recup_id:
        return redirect('login_modify:recuperar_solicitar')

    recup = RecuperacionContrasena.objects.filter(pk=recup_id).select_related('usuario').first()
    if not recup:
        request.session.pop('recup_id', None)
        return redirect('login_modify:recuperar_solicitar')

    if request.method == 'POST':
        form = VerificarPinForm(request.POST)
        if form.is_valid():
            if not recup.esta_vigente():
                messages.error(request, 'El código expiró o se superaron los intentos. Solicita uno nuevo.')
                request.session.pop('recup_id', None)
                return redirect('login_modify:recuperar_solicitar')
            if recup.verificar(form.cleaned_data['pin']):
                token = TimestampSigner(salt=_SIGNER_SALT).sign(str(recup.pk))
                request.session['recup_token'] = token
                request.session.pop('recup_id', None)
                return redirect('login_modify:recuperar_cambiar')
            restantes = max(0, RecuperacionContrasena.MAX_INTENTOS - recup.intentos)
            messages.error(request, f'Código incorrecto. Te quedan {restantes} intento(s).')
    else:
        form = VerificarPinForm()

    return render(request, 'auth/recuperar_verificar.html', {
        'form': form,
        'email_destino': recup.usuario.email,
    })


def recuperar_cambiar(request):
    if request.user.is_authenticated:
        return redirect('login_modify:dashboard')

    token = request.session.get('recup_token')
    if not token:
        return redirect('login_modify:recuperar_solicitar')

    try:
        recup_id = TimestampSigner(salt=_SIGNER_SALT).unsign(token, max_age=_TOKEN_MAX_AGE_SEG)
    except SignatureExpired:
        request.session.pop('recup_token', None)
        messages.error(request, 'La sesión de recuperación expiró. Solicita un nuevo código.')
        return redirect('login_modify:recuperar_solicitar')
    except BadSignature:
        request.session.pop('recup_token', None)
        return redirect('login_modify:recuperar_solicitar')

    recup = RecuperacionContrasena.objects.filter(pk=recup_id, verificado=True, usado=False).select_related('usuario').first()
    if not recup:
        request.session.pop('recup_token', None)
        return redirect('login_modify:recuperar_solicitar')

    if request.method == 'POST':
        form = NuevaContrasenaForm(request.POST)
        if form.is_valid():
            usuario = User.objects.get(pk=recup.usuario_id)
            usuario.set_password(form.cleaned_data['password1'])
            usuario.save()
            recup.usado = True
            recup.save(update_fields=['usado'])
            request.session.pop('recup_token', None)
            messages.success(request, 'Contraseña actualizada. Inicia sesión con tu nueva contraseña.')
            return redirect('login_modify:login')
    else:
        form = NuevaContrasenaForm()

    return render(request, 'auth/recuperar_cambiar.html', {'form': form})


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
