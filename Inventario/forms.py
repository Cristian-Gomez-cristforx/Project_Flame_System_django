from django import forms

from .models import (
    Bebida,
    Categoria,
    DetalleReceta,
    Insumo,
    Merma,
    Producto,
    RecetaProducto,
)


BOOTSTRAP_INPUT = {'class': 'form-control'}
BOOTSTRAP_SELECT = {'class': 'form-select'}
BOOTSTRAP_CHECK = {'class': 'form-check-input'}


def _normalizar_categoria(valor):
    return ' '.join((valor or '').split())


def _validar_nueva_categoria(nombre):
    nombre = _normalizar_categoria(nombre)
    if nombre and Categoria.objects.filter(nombre_categoria__iexact=nombre).exists():
        raise forms.ValidationError(
            f'La categoría "{nombre}" ya existe. Selecciónala en el listado.'
        )
    return nombre


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre_categoria', 'tipo']
        widgets = {
            'nombre_categoria': forms.TextInput(attrs={**BOOTSTRAP_INPUT, 'maxlength': '100'}),
            'tipo': forms.Select(attrs=BOOTSTRAP_SELECT),
        }


class InsumoForm(forms.ModelForm):
    nueva_categoria = forms.CharField(
        required=False,
        label='Nueva categoría (opcional)',
        widget=forms.TextInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Escriba una nueva categoría',
            'maxlength': '100',
        }),
    )

    class Meta:
        model = Insumo
        fields = [
            'nombre_insumo',
            'cantidad_insumo',
            'unidad_medida',
            'precio_insumo',
            'categoria',
            'cantidad_a_agregar',
        ]
        widgets = {
            'nombre_insumo': forms.TextInput(attrs={**BOOTSTRAP_INPUT, 'maxlength': '100'}),
            'cantidad_insumo': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 0}),
            'unidad_medida': forms.Select(attrs=BOOTSTRAP_SELECT),
            'precio_insumo': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1, 'max': 10000000}),
            'categoria': forms.Select(attrs=BOOTSTRAP_SELECT),
            'cantidad_a_agregar': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 0, 'step': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        self.fields['categoria'].queryset = Categoria.objects.filter(
            tipo=Categoria.Tipo.INSUMO
        )
        self.fields['categoria'].empty_label = '-- Seleccionar categoría --'

    def clean_nueva_categoria(self):
        return _validar_nueva_categoria(self.cleaned_data.get('nueva_categoria'))

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get('categoria')
        nueva = cleaned.get('nueva_categoria') or ''

        if not categoria and not nueva:
            raise forms.ValidationError(
                'Debe seleccionar una categoría existente o escribir una nueva.'
            )
        return cleaned

    def save(self, commit=True):
        nueva = self.cleaned_data.get('nueva_categoria') or ''
        if nueva:
            existente = Categoria.objects.filter(nombre_categoria__iexact=nueva).first()
            self.instance.categoria = existente or Categoria.objects.create(
                nombre_categoria=nueva, tipo=Categoria.Tipo.INSUMO,
            )
        return super().save(commit=commit)


class InsumoAgregarStockForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['cantidad_a_agregar']
        widgets = {
            'cantidad_a_agregar': forms.NumberInput(attrs={
                **BOOTSTRAP_INPUT,
                'min': 0,
                'step': '0.01',
            }),
        }


class ProductoForm(forms.ModelForm):
    nueva_categoria = forms.CharField(
        required=False,
        label='Nueva categoría',
        widget=forms.TextInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Nombre de la nueva categoría',
            'maxlength': '100',
        }),
    )

    class Meta:
        model = Producto
        fields = [
            'nombre_producto',
            'precio_producto',
            'categoria',
            'activo',
        ]
        widgets = {
            'nombre_producto': forms.TextInput(attrs={**BOOTSTRAP_INPUT, 'maxlength': '100'}),
            'precio_producto': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1, 'max': 10000000}),
            'categoria': forms.Select(attrs=BOOTSTRAP_SELECT),
            'activo': forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        self.fields['categoria'].queryset = Categoria.objects.filter(
            tipo=Categoria.Tipo.PRODUCTO
        )
        self.fields['categoria'].empty_label = '-- Seleccionar categoría --'

    def clean_nueva_categoria(self):
        return _validar_nueva_categoria(self.cleaned_data.get('nueva_categoria'))

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get('categoria')
        nueva = cleaned.get('nueva_categoria') or ''

        if not categoria and not nueva:
            raise forms.ValidationError(
                'Debe seleccionar una categoría existente o escribir una nueva.'
            )
        return cleaned

    def save(self, commit=True):
        nueva = self.cleaned_data.get('nueva_categoria') or ''
        if nueva:
            existente = Categoria.objects.filter(nombre_categoria__iexact=nueva).first()
            self.instance.categoria = existente or Categoria.objects.create(
                nombre_categoria=nueva, tipo=Categoria.Tipo.PRODUCTO,
            )
        return super().save(commit=commit)


class BebidaForm(forms.ModelForm):
    nueva_categoria = forms.CharField(
        required=False,
        label='Nueva categoría',
        widget=forms.TextInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Nombre de la nueva categoría',
            'maxlength': '100',
        }),
    )

    class Meta:
        model = Bebida
        fields = [
            'nombre_bebida',
            'tamaño_bebida',
            'cantidad_bebida',
            'precio_compra',
            'precio_unitario_venta',
            'categoria',
            'cantidad_a_agregar',
        ]
        widgets = {
            'nombre_bebida': forms.TextInput(attrs={**BOOTSTRAP_INPUT, 'maxlength': '100'}),
            'tamaño_bebida': forms.Select(attrs=BOOTSTRAP_SELECT),
            'cantidad_bebida': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1}),
            'precio_compra': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1, 'max': 10000000}),
            'precio_unitario_venta': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1, 'max': 10000000}),
            'categoria': forms.Select(attrs=BOOTSTRAP_SELECT),
            'cantidad_a_agregar': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 0, 'step': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoria'].required = False
        self.fields['categoria'].queryset = Categoria.objects.filter(
            tipo=Categoria.Tipo.BEBIDA
        )
        self.fields['categoria'].empty_label = '-- Seleccionar categoría --'

    def clean_nueva_categoria(self):
        return _validar_nueva_categoria(self.cleaned_data.get('nueva_categoria'))

    def clean(self):
        cleaned = super().clean()
        categoria = cleaned.get('categoria')
        nueva = cleaned.get('nueva_categoria') or ''

        if not categoria and not nueva:
            raise forms.ValidationError(
                'Debe seleccionar una categoría existente o escribir una nueva.'
            )
        return cleaned

    def save(self, commit=True):
        nueva = self.cleaned_data.get('nueva_categoria') or ''
        if nueva:
            existente = Categoria.objects.filter(nombre_categoria__iexact=nueva).first()
            self.instance.categoria = existente or Categoria.objects.create(
                nombre_categoria=nueva, tipo=Categoria.Tipo.BEBIDA,
            )
        return super().save(commit=commit)


class MermaForm(forms.ModelForm):
    class Meta:
        model = Merma
        fields = [
            'insumo',
            'cantidad_mermada',
            'motivo',
            'descripcion',
            'responsable',
        ]
        widgets = {
            'insumo': forms.Select(attrs=BOOTSTRAP_SELECT),
            'cantidad_mermada': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1}),
            'motivo': forms.Select(attrs=BOOTSTRAP_SELECT),
            'descripcion': forms.Textarea(attrs={**BOOTSTRAP_INPUT, 'rows': 3}),
            'responsable': forms.TextInput(attrs=BOOTSTRAP_INPUT),
        }


class DetalleRecetaForm(forms.ModelForm):
    class Meta:
        model = DetalleReceta
        fields = ['insumo', 'cantidad_requerida']
        widgets = {
            'insumo': forms.Select(attrs=BOOTSTRAP_SELECT),
            'cantidad_requerida': forms.NumberInput(attrs={
                'class': 'form-control solo-enteros',
                'min': 1, 'max': 5000, 'step': 1,
                'inputmode': 'numeric', 'pattern': r'\d*',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['insumo'].queryset = Insumo.objects.order_by('nombre_insumo')
        self.fields['insumo'].empty_label = '-- Seleccionar insumo --'


DetalleRecetaFormSet = forms.inlineformset_factory(
    RecetaProducto,
    DetalleReceta,
    form=DetalleRecetaForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
