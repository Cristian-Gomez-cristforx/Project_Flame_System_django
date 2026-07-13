from collections import defaultdict
from decimal import Decimal

from django import forms
from django.core.validators import MaxLengthValidator, MinLengthValidator

from Inventario.models import Bebida, Producto, RecetaProducto
from login_modify_django.forms import (
    NUMERIC_ATTRS,
    TELEFONO_LEN,
    solo_letras,
    solo_numeros,
)

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
        fields = ['numero_mesa', 'activa']
        widgets = {
            'numero_mesa': forms.NumberInput(attrs={**BOOTSTRAP_INPUT, 'min': 1}),
            'activa': forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
        }

    def clean_numero_mesa(self):
        numero = self.cleaned_data.get('numero_mesa')
        if numero is None:
            return numero
        if numero < 1:
            raise forms.ValidationError('El número de mesa debe ser mayor a 0.')
        qs = Mesa.objects.filter(numero_mesa=numero)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'Ya existe la mesa {numero}.')
        return numero


class PedidoCrearForm(forms.ModelForm):
    nueva_mesa = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            **BOOTSTRAP_INPUT,
            'placeholder': 'Número de la nueva mesa',
            'autocomplete': 'off',
        }),
        label='Nueva mesa',
    )

    class Meta:
        model = Pedido
        fields = [
            'tipo',
            'mesa',
            'nombre_cliente',
            'telefono_cliente',
            'direccion_pedi',
            'minutos_recogida',
        ]
        widgets = {
            'tipo': forms.Select(attrs=BOOTSTRAP_SELECT),
            'mesa': forms.Select(attrs=BOOTSTRAP_SELECT),
            'nombre_cliente': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'telefono_cliente': forms.TextInput(attrs={**NUMERIC_ATTRS, 'maxlength': str(TELEFONO_LEN)}),
            'direccion_pedi': forms.TextInput(attrs=BOOTSTRAP_INPUT),
            'minutos_recogida': forms.NumberInput(attrs={
                **BOOTSTRAP_INPUT,
                'min': 1,
                'placeholder': 'Ej: 30',
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['mesa'].queryset = Mesa.objects.filter(activa=True, ocupada=False).order_by('numero_mesa')
        self.fields['mesa'].required = False
        self.fields['nombre_cliente'].required = False
        self.fields['telefono_cliente'].required = False
        self.fields['direccion_pedi'].required = False
        self.fields['minutos_recogida'].required = False

    def _puede_crear_mesa(self):
        if not self.user or not self.user.is_authenticated:
            return False
        if self.user.is_superuser:
            return True
        perfil = getattr(self.user, 'perfil', None)
        return bool(perfil and perfil.es_admin)
        self.fields['nombre_cliente'].validators.append(solo_letras)
        self.fields['telefono_cliente'].validators.extend([
            solo_numeros,
            MinLengthValidator(TELEFONO_LEN, f'El teléfono debe tener exactamente {TELEFONO_LEN} dígitos.'),
            MaxLengthValidator(TELEFONO_LEN, f'El teléfono debe tener exactamente {TELEFONO_LEN} dígitos.'),
        ])

    def clean_nueva_mesa(self):
        numero = self.cleaned_data.get('nueva_mesa')
        if numero in (None, ''):
            return None
        if not self._puede_crear_mesa():
            raise forms.ValidationError(
                'Solo el administrador puede crear nuevas mesas.'
            )
        if Mesa.objects.filter(numero_mesa=numero).exists():
            raise forms.ValidationError(
                f'La mesa {numero} ya existe. Selecciónala en el listado.'
            )
        return numero

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        mesa = cleaned.get('mesa')
        nueva_mesa = cleaned.get('nueva_mesa')
        direccion = (cleaned.get('direccion_pedi') or '').strip()
        nombre = (cleaned.get('nombre_cliente') or '').strip()
        telefono = (cleaned.get('telefono_cliente') or '').strip()

        if tipo == Pedido.TipoPedido.MESA:
            if not mesa and not nueva_mesa:
                self.add_error('mesa', 'Debe seleccionar una mesa libre o crear una nueva.')
            elif mesa and nueva_mesa:
                self.add_error('nueva_mesa', 'Selecciona una mesa existente o crea una nueva, no ambas.')
            elif mesa and mesa.ocupada:
                self.add_error('mesa', f'La mesa {mesa.numero_mesa} está ocupada.')
            elif mesa and not mesa.activa:
                self.add_error('mesa', f'La mesa {mesa.numero_mesa} está inactiva.')

        if tipo == Pedido.TipoPedido.DOMICILIO:
            if not direccion:
                self.add_error('direccion_pedi', 'La dirección es obligatoria para domicilio.')
            if not telefono:
                self.add_error('telefono_cliente', 'El teléfono es obligatorio para domicilio.')

        if tipo == Pedido.TipoPedido.RECOGIDA and not nombre:
            self.add_error('nombre_cliente', 'El nombre del cliente es obligatorio para recoger.')

        if tipo == Pedido.TipoPedido.RECOGIDA and (mesa or nueva_mesa):
            self.add_error('mesa', 'Los pedidos para recoger no usan mesa.')

        minutos = cleaned.get('minutos_recogida')
        if tipo == Pedido.TipoPedido.RECOGIDA and not minutos:
            self.add_error('minutos_recogida', 'Indica el tiempo pactado de recogida en minutos.')

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

    def __init__(self, *args, pedido=None, **kwargs):
        super().__init__(*args, **kwargs)
        productos = (
            Producto.objects.filter(activo=True)
            .select_related('receta')
            .prefetch_related('receta__detalles__insumo')
            .order_by('nombre_producto')
        )

        ya_en_pedido = {}
        consumo_pedido = defaultdict(lambda: Decimal('0'))
        if pedido is not None:
            detalles_pedido = (
                pedido.productos
                .prefetch_related('insumos__insumo')
                .all()
            )
            for d in detalles_pedido:
                ya_en_pedido[d.producto_id] = ya_en_pedido.get(d.producto_id, 0) + d.cantidad
                for di in d.insumos.all():
                    if di.usar:
                        consumo_pedido[di.insumo_id] += Decimal(di.cantidad_requerida) * d.cantidad

        stock_por_producto = {}
        for prod in productos:
            try:
                receta = prod.receta
            except RecetaProducto.DoesNotExist:
                stock_por_producto[prod.pk] = 0
                continue
            detalles_receta = list(receta.detalles.all())
            if not detalles_receta:
                stock_por_producto[prod.pk] = 0
                continue
            posibles_min = None
            for detalle in detalles_receta:
                if detalle.cantidad_requerida <= 0:
                    continue
                disponible = Decimal(detalle.insumo.cantidad_insumo) - consumo_pedido.get(detalle.insumo_id, Decimal('0'))
                posibles = int(disponible // Decimal(detalle.cantidad_requerida))
                if posibles < 0:
                    posibles = 0
                if posibles_min is None or posibles < posibles_min:
                    posibles_min = posibles
            stock_por_producto[prod.pk] = max(0, posibles_min or 0)

        self.fields['producto'].queryset = productos
        self.fields['producto'].label_from_instance = (
            lambda obj: f'{obj.nombre_producto} | Stock: {stock_por_producto.get(obj.pk, 0)} | ${obj.precio_producto:,.0f}'.replace(',', '.')
        )
        self._stock_por_producto = stock_por_producto
        self._ya_en_pedido = ya_en_pedido

    def clean(self):
        cleaned = super().clean()
        producto = cleaned.get('producto')
        cantidad = cleaned.get('cantidad')
        if producto and producto.pk in self._ya_en_pedido:
            self.add_error(
                'producto',
                f'"{producto.nombre_producto}" ya está en el pedido. Añade más unidades editando su fila o elimínalo primero.',
            )
            return cleaned
        if producto and cantidad:
            disponible = self._stock_por_producto.get(producto.pk, 0)
            if disponible <= 0:
                self.add_error(
                    'producto',
                    f'El producto "{producto.nombre_producto}" no tiene unidades.',
                )
            elif cantidad > disponible:
                self.add_error(
                    'cantidad',
                    f'No hay suficientes insumos para "{producto.nombre_producto}".',
                )
        return cleaned


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

    def __init__(self, *args, pedido=None, **kwargs):
        super().__init__(*args, **kwargs)
        bebidas = Bebida.objects.order_by('nombre_bebida')

        ya_en_pedido = {}
        if pedido is not None:
            for d in pedido.bebidas.all():
                ya_en_pedido[d.bebida_id] = ya_en_pedido.get(d.bebida_id, 0) + d.cantidad

        stock_por_bebida = {
            b.pk: max(0, b.cantidad_bebida - ya_en_pedido.get(b.pk, 0))
            for b in bebidas
        }

        self.fields['bebida'].queryset = bebidas
        self.fields['bebida'].label_from_instance = (
            lambda obj: f'{obj.nombre_bebida} ({obj.tamaño_bebida}) | Stock: {stock_por_bebida.get(obj.pk, 0)} | ${obj.precio_venta:,.0f}'.replace(',', '.')
        )
        self._stock_por_bebida = stock_por_bebida
        self._ya_en_pedido = ya_en_pedido

    def clean(self):
        cleaned = super().clean()
        bebida = cleaned.get('bebida')
        cantidad = cleaned.get('cantidad')
        if bebida and bebida.pk in self._ya_en_pedido:
            self.add_error(
                'bebida',
                f'"{bebida.nombre_bebida}" ya está en el pedido. Añade más unidades editando su fila o elimínalo primero.',
            )
            return cleaned
        if bebida and cantidad:
            disponible = self._stock_por_bebida.get(bebida.pk, 0)
            if disponible <= 0:
                self.add_error(
                    'bebida',
                    f'La bebida "{bebida.nombre_bebida}" no tiene unidades.',
                )
            elif cantidad > disponible:
                self.add_error(
                    'cantidad',
                    f'No hay suficientes unidades de "{bebida.nombre_bebida}".',
                )
        return cleaned


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
