from datetime import date

from django import forms
from django.utils import timezone

from Gestion_Pedidos.models import Pedido


class RangoFechasForm(forms.Form):
    desde = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Desde',
    )
    hasta = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Hasta',
    )

    def clean(self):
        cleaned = super().clean()
        desde = cleaned.get('desde')
        hasta = cleaned.get('hasta')
        if desde and hasta and desde > hasta:
            raise forms.ValidationError('La fecha "desde" no puede ser posterior a "hasta".')
        return cleaned


def _parsear_mes(valor):
    try:
        anio, mes = valor.split('-')
        return date(int(anio), int(mes), 1)
    except (ValueError, AttributeError):
        raise forms.ValidationError('Formato de mes inválido.')


class RangoMesesForm(forms.Form):
    desde_mes = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'month', 'class': 'form-control'}),
        label='Mes inicial',
    )
    hasta_mes = forms.CharField(
        widget=forms.TextInput(attrs={'type': 'month', 'class': 'form-control'}),
        label='Mes final',
    )

    def clean_desde_mes(self):
        return _parsear_mes(self.cleaned_data['desde_mes'])

    def clean_hasta_mes(self):
        return _parsear_mes(self.cleaned_data['hasta_mes'])

    def clean(self):
        cleaned = super().clean()
        desde = cleaned.get('desde_mes')
        hasta = cleaned.get('hasta_mes')
        mes_actual = timezone.localdate().replace(day=1)

        if desde and desde > mes_actual:
            raise forms.ValidationError('El mes inicial no puede ser posterior al mes actual.')
        if hasta and hasta > mes_actual:
            raise forms.ValidationError('El mes final no puede ser posterior al mes actual.')
        if desde and hasta and desde > hasta:
            raise forms.ValidationError('El mes inicial no puede ser posterior al mes final.')
        return cleaned


class FiltroPedidosReporteForm(forms.Form):
    desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Desde',
    )
    hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label='Hasta',
    )
    estado = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Todos los estados'),
            (Pedido.EstadoPedido.CANCELADO, 'Cancelado'),
            (Pedido.EstadoPedido.FINALIZADO, 'Finalizado'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    tipo = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos los tipos')] + list(Pedido.TipoPedido.choices),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cliente, factura, mesero...'}),
        label='Búsqueda',
    )

    def clean(self):
        cleaned = super().clean()
        desde = cleaned.get('desde')
        hasta = cleaned.get('hasta')
        hoy = timezone.localdate()
        if desde and desde > hoy:
            self.add_error('desde', 'La fecha no puede ser posterior a hoy.')
        if hasta and hasta > hoy:
            self.add_error('hasta', 'La fecha no puede ser posterior a hoy.')
        if desde and hasta and desde > hasta:
            self.add_error('desde', 'La fecha "Desde" no puede ser posterior a "Hasta".')
        return cleaned
