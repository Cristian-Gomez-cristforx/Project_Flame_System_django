from django import forms

from Inventario.models import Bebida, Producto

from .models import (
    DetallePedidoBebida,
    DetallePedidoInsumo,
    DetallePedidoProducto,
    Mesa,
    Pedido,
)


BOOTSTRAP_INPUT = {'class': 'form-control'}
BOOTSTRAP_SELECT = {'class': 'form-select'}
BOOTSTRAP_CHECK = {'class': 'form-check-input'}


class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero_mesa', 'activa', 'ocupada']
        widgets = {
            'numero_mesa': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1}),
            'activa': forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
            'ocupada': forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
        }


class PedidoCrearForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = [
            'tipo',
            'mesa',
            'nombre_cliente',
            'telefono_cliente',
            'direccion_pedi',
        ]
        widgets = {
            'tipo': forms.Select(attrs=BOOTSTRAP_SELECT),
            'mesa': forms.Select(attrs=BOOTSTRAP_SELECT),
            'nombre_cliente': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'telefono_cliente': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'direccion_pedi': forms.TextInput(attrs=BOOTSTRAP_INPUT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mesa'].queryset = Mesa.objects.filter(activa=True, ocupada=False).order_by('numero_mesa')
        self.fields['mesa'].required = False
        self.fields['nombre_cliente'].required = False
        self.fields['telefono_cliente'].required = False
        self.fields['direccion_pedi'].required = False

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        mesa = cleaned.get('mesa')
        direccion = (cleaned.get('direccion_pedi') or '').strip()
        nombre = (cleaned.get('nombre_cliente') or '').strip()
        telefono = (cleaned.get('telefono_cliente') or '').strip()

        if tipo == Pedido.TipoPedido.MESA and not mesa:
            self.add_error('mesa', 'Debe seleccionar una mesa libre.')

        if tipo == Pedido.TipoPedido.DOMICILIO:
            if not direccion:
                self.add_error('direccion_pedi', 'La dirección es obligatoria para domicilio.')
            if not telefono:
                self.add_error('telefono_cliente', 'El teléfono es obligatorio para domicilio.')

        if tipo == Pedido.TipoPedido.RECOGIDA and not nombre:
            self.add_error('nombre_cliente', 'El nombre del cliente es obligatorio para recoger.')

        if tipo == Pedido.TipoPedido.RECOGIDA and mesa:
            self.add_error('mesa', 'Los pedidos para recoger no usan mesa.')

        return cleaned


class AgregarProductoForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.none(),
        widget=forms.Select(attrs=BOOTSTRAP_SELECT),
        label='Producto',
    )
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(activo=True).order_by('nombre_producto')


class AgregarBebidaForm(forms.Form):
    bebida = forms.ModelChoiceField(
        queryset=Bebida.objects.none(),
        widget=forms.Select(attrs=BOOTSTRAP_SELECT),
        label='Bebida',
    )
    cantidad = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bebida'].queryset = Bebida.objects.filter(cantidad_bebida__gt=0).order_by('nombre_bebida')


class PagoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['tipo_pago']
        widgets = {
            'tipo_pago': forms.Select(attrs=BOOTSTRAP_SELECT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_pago'].required = True


class FiltroPedidosForm(forms.Form):
    estado = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + list(Pedido.EstadoPedido.choices),
        widget=forms.Select(attrs=BOOTSTRAP_SELECT),
    )
    tipo = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + list(Pedido.TipoPedido.choices),
        widget=forms.Select(attrs=BOOTSTRAP_SELECT),
    )
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Cliente, factura, teléfono...',
        }),
    )
