from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.validators import RegexValidator

from .models import Perfil


solo_numeros = RegexValidator(
    regex=r'^\d+$',
    message='Este campo debe contener solo números.',
)

NUMERIC_ATTRS = {
    'class': 'form-control',
    'inputmode': 'numeric',
    'pattern': r'\d*',
}


User = get_user_model()

BOOTSTRAP_INPUT = {'class': 'form-control'}
BOOTSTRAP_SELECT = {'class': 'form-select'}


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
        validators=[solo_numeros],
        widget=forms.TextInput(attrs=NUMERIC_ATTRS),
        label='Teléfono',
    )
    documento = forms.CharField(
        required=False,
        validators=[solo_numeros],
        widget=forms.TextInput(attrs=NUMERIC_ATTRS),
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
        validators=[solo_numeros],
        widget=forms.TextInput(attrs=NUMERIC_ATTRS),
        label='Teléfono',
    )
    documento = forms.CharField(
        required=False,
        validators=[solo_numeros],
        widget=forms.TextInput(attrs=NUMERIC_ATTRS),
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
        if self.instance and self.instance.pk:
            perfil = getattr(self.instance, 'perfil', None)
            if perfil:
                self.fields['rol'].initial = perfil.rol
                self.fields['telefono'].initial = perfil.telefono
                self.fields['documento'].initial = perfil.documento
                self.fields['activo'].initial = perfil.activo

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
