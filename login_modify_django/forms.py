from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.validators import MaxLengthValidator, MinLengthValidator, RegexValidator

from .models import Perfil


solo_numeros = RegexValidator(
    regex=r'^\d+$',
    message='Este campo debe contener solo números.',
)

solo_letras = RegexValidator(
    regex=r'^[A-Za-zÁÉÍÓÚÜáéíóúüÑñ\s]+$',
    message='Este campo solo debe contener letras.',
)

TELEFONO_LEN = 10
DOCUMENTO_MIN = 8
DOCUMENTO_MAX = 10

NUMERIC_ATTRS = {
    'class': 'form-control',
    'inputmode': 'numeric',
    'pattern': r'\d*',
}


User = get_user_model()

BOOTSTRAP_INPUT = {'class': 'form-control'}
BOOTSTRAP_SELECT = {'class': 'form-select'}


def _validar_email_unico(email, instance=None):
    email = (email or '').strip()
    if not email:
        return email
    qs = User.objects.filter(email__iexact=email)
    if instance and instance.pk:
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise forms.ValidationError('Ya existe un usuario con este correo.')
    return email


def _validar_documento_unico(documento, instance=None):
    documento = (documento or '').strip()
    if not documento:
        return documento
    qs = Perfil.objects.filter(documento=documento)
    if instance and instance.pk:
        qs = qs.exclude(usuario__pk=instance.pk)
    if qs.exists():
        raise forms.ValidationError('Ya existe un usuario con este documento.')
    return documento


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuario',
        widget=forms.TextInput(attrs={
            **BOOTSTRAP_INPUT,
            'autofocus': True,
            'placeholder': 'Usuario',
            'autocomplete': 'username',
        }),
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
        }),
    )


class UsuarioCreateForm(UserCreationForm):
    rol = forms.ChoiceField(
        choices=Perfil.Rol.choices,
        widget=forms.Select(attrs=BOOTSTRAP_SELECT),
        label='Rol',
    )
    telefono = forms.CharField(
        required=False,
        validators=[
            solo_numeros,
            MinLengthValidator(TELEFONO_LEN, f'El teléfono debe tener exactamente {TELEFONO_LEN} dígitos.'),
            MaxLengthValidator(TELEFONO_LEN, f'El teléfono debe tener exactamente {TELEFONO_LEN} dígitos.'),
        ],
        widget=forms.TextInput(attrs={**NUMERIC_ATTRS, 'maxlength': str(TELEFONO_LEN)}),
        label='Teléfono',
    )
    documento = forms.CharField(
        required=False,
        validators=[
            solo_numeros,
            MinLengthValidator(DOCUMENTO_MIN, f'El documento debe tener entre {DOCUMENTO_MIN} y {DOCUMENTO_MAX} dígitos.'),
            MaxLengthValidator(DOCUMENTO_MAX, f'El documento debe tener entre {DOCUMENTO_MIN} y {DOCUMENTO_MAX} dígitos.'),
        ],
        widget=forms.TextInput(attrs={**NUMERIC_ATTRS, 'maxlength': str(DOCUMENTO_MAX)}),
        label='Documento',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('username', 'first_name', 'last_name', 'email', 'password1', 'password2'):
            if name in self.fields:
                self.fields[name].widget.attrs.setdefault('class', 'form-control')
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['first_name'].validators.append(solo_letras)
        self.fields['last_name'].validators.append(solo_letras)

    def clean_email(self):
        return _validar_email_unico(self.cleaned_data.get('email'), self.instance)

    def clean_documento(self):
        return _validar_documento_unico(self.cleaned_data.get('documento'), self.instance)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            perfil = user.perfil
            perfil.rol = self.cleaned_data['rol']
            perfil.telefono = self.cleaned_data.get('telefono', '')
            perfil.documento = self.cleaned_data.get('documento', '')
            perfil.save()
        return user


class UsuarioEditForm(forms.ModelForm):
    rol = forms.ChoiceField(
        choices=Perfil.Rol.choices,
        widget=forms.Select(attrs=BOOTSTRAP_SELECT),
        label='Rol',
    )
    telefono = forms.CharField(
        required=False,
        validators=[
            solo_numeros,
            MinLengthValidator(TELEFONO_LEN, f'El teléfono debe tener exactamente {TELEFONO_LEN} dígitos.'),
            MaxLengthValidator(TELEFONO_LEN, f'El teléfono debe tener exactamente {TELEFONO_LEN} dígitos.'),
        ],
        widget=forms.TextInput(attrs={**NUMERIC_ATTRS, 'maxlength': str(TELEFONO_LEN)}),
        label='Teléfono',
    )
    documento = forms.CharField(
        required=False,
        validators=[
            solo_numeros,
            MinLengthValidator(DOCUMENTO_MIN, f'El documento debe tener entre {DOCUMENTO_MIN} y {DOCUMENTO_MAX} dígitos.'),
            MaxLengthValidator(DOCUMENTO_MAX, f'El documento debe tener entre {DOCUMENTO_MIN} y {DOCUMENTO_MAX} dígitos.'),
        ],
        widget=forms.TextInput(attrs={**NUMERIC_ATTRS, 'maxlength': str(DOCUMENTO_MAX)}),
        label='Documento',
    )
    activo = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Activo',
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombres',
            'last_name': 'Apellidos',
            'email': 'Correo electrónico',
        }
        widgets = {
            'username': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'first_name': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'last_name': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'email': forms.EmailInput(attrs=BOOTSTRAP_INPUT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['first_name'].validators.append(solo_letras)
        self.fields['last_name'].validators.append(solo_letras)
        if self.instance and self.instance.pk:
            perfil = getattr(self.instance, 'perfil', None)
            if perfil:
                self.fields['rol'].initial = perfil.rol
                self.fields['telefono'].initial = perfil.telefono
                self.fields['documento'].initial = perfil.documento
                self.fields['activo'].initial = perfil.activo

    def clean_email(self):
        return _validar_email_unico(self.cleaned_data.get('email'), self.instance)

    def clean_documento(self):
        return _validar_documento_unico(self.cleaned_data.get('documento'), self.instance)

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            perfil = user.perfil
            perfil.rol = self.cleaned_data['rol']
            perfil.telefono = self.cleaned_data.get('telefono', '')
            perfil.documento = self.cleaned_data.get('documento', '')
            perfil.activo = self.cleaned_data.get('activo', False)
            perfil.save()
        return user


class SolicitudRecuperacionForm(forms.Form):
    identificador = forms.CharField(
        label='Usuario o correo',
        widget=forms.TextInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Usuario o correo electrónico',
            'autocomplete': 'username',
            'autofocus': True,
        }),
    )

    def clean_identificador(self):
        valor = (self.cleaned_data.get('identificador') or '').strip()
        if not valor:
            raise forms.ValidationError('Ingresa tu usuario o correo.')
        return valor


class VerificarPinForm(forms.Form):
    pin = forms.CharField(
        label='Código de verificación',
        min_length=6, max_length=6,
        widget=forms.TextInput(attrs={
            **NUMERIC_ATTRS,
            'placeholder': '••••••',
            'maxlength': '6',
            'autocomplete': 'one-time-code',
            'autofocus': True,
        }),
        validators=[solo_numeros],
    )


class NuevaContrasenaForm(forms.Form):
    password1 = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Nueva contraseña',
            'autocomplete': 'new-password',
            'autofocus': True,
        }),
        min_length=8,
        help_text=password_validation.password_validators_help_text_html(),
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Confirmar contraseña',
            'autocomplete': 'new-password',
        }),
        min_length=8,
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if p2:
            password_validation.validate_password(p2, self.usuario)
        return p2


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ('rol', 'telefono', 'documento', 'activo')
        widgets = {
            'rol': forms.Select(attrs=BOOTSTRAP_SELECT),
            'telefono': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'documento': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
