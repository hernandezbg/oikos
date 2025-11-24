from django import forms
from core.models import CajaChica, MovimientoCajaChica, TransferenciaCajaChica, CodigoInvitacion
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, Field
from datetime import date


class CajaChicaForm(forms.ModelForm):
    """Formulario para crear y editar cajas chicas"""

    class Meta:
        model = CajaChica
        fields = ['nombre', 'descripcion', 'saldo_inicial']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Caja Jóvenes, Caja Ministerio Mujeres'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción opcional de la caja'
            }),
            'saldo_inicial': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0'
            }),
        }
        labels = {
            'nombre': 'Nombre de la Caja',
            'descripcion': 'Descripción',
            'saldo_inicial': 'Saldo Inicial ($)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Caja', css_class='btn btn-primary'))


class MovimientoCajaChicaForm(forms.ModelForm):
    """Formulario para crear movimientos en cajas chicas"""

    class Meta:
        model = MovimientoCajaChica
        fields = ['tipo', 'fecha', 'concepto', 'monto', 'categoria_ingreso', 'categoria_egreso']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'concepto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del movimiento'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01'
            }),
            'categoria_ingreso': forms.Select(attrs={'class': 'form-control'}),
            'categoria_egreso': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'tipo': 'Tipo de Movimiento',
            'fecha': 'Fecha',
            'concepto': 'Concepto',
            'monto': 'Monto ($)',
            'categoria_ingreso': 'Categoría de Ingreso',
            'categoria_egreso': 'Categoría de Egreso',
        }

    def __init__(self, iglesia=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Fecha por defecto: hoy
        if not self.instance.pk:
            self.fields['fecha'].initial = date.today()

        # Filtrar categorías por iglesia
        if iglesia:
            self.fields['categoria_ingreso'].queryset = iglesia.categorias_ingreso.filter(activa=True)
            self.fields['categoria_egreso'].queryset = iglesia.categorias_egreso.filter(activa=True)

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Guardar Movimiento', css_class='btn btn-primary'))


class TransferenciaCajaChicaForm(forms.ModelForm):
    """Formulario para crear transferencias entre cajas chicas"""

    class Meta:
        model = TransferenciaCajaChica
        fields = ['caja_origen', 'caja_destino', 'monto', 'concepto', 'fecha']
        widgets = {
            'caja_origen': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_caja_origen'
            }),
            'caja_destino': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_caja_destino'
            }),
            'monto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0.01'
            }),
            'concepto': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Motivo de la transferencia'
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
        labels = {
            'caja_origen': 'Caja Origen (de donde sale el dinero)',
            'caja_destino': 'Caja Destino (a donde va el dinero)',
            'monto': 'Monto a Transferir ($)',
            'concepto': 'Concepto / Motivo',
            'fecha': 'Fecha de Transferencia',
        }

    def __init__(self, iglesia=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Fecha por defecto: hoy
        if not self.instance.pk:
            self.fields['fecha'].initial = date.today()

        # Filtrar solo cajas activas de la iglesia
        if iglesia:
            self.fields['caja_origen'].queryset = CajaChica.objects.filter(
                iglesia=iglesia,
                activa=True
            )
            self.fields['caja_destino'].queryset = CajaChica.objects.filter(
                iglesia=iglesia,
                activa=True
            )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Realizar Transferencia', css_class='btn btn-primary'))

    def clean(self):
        cleaned_data = super().clean()
        caja_origen = cleaned_data.get('caja_origen')
        caja_destino = cleaned_data.get('caja_destino')
        monto = cleaned_data.get('monto')

        # Validar que no sean la misma caja
        if caja_origen and caja_destino and caja_origen == caja_destino:
            raise forms.ValidationError('No puedes transferir dinero a la misma caja')

        # Validar saldo suficiente
        if caja_origen and monto:
            saldo_origen = caja_origen.calcular_saldo_actual()
            if saldo_origen < monto:
                raise forms.ValidationError(
                    f'Saldo insuficiente en {caja_origen.nombre}. '
                    f'Saldo disponible: ${saldo_origen}, Monto a transferir: ${monto}'
                )

        return cleaned_data


class GenerarCodigoCajaForm(forms.Form):
    """Formulario para generar códigos de invitación para cajas chicas"""

    caja_chica = forms.ModelChoiceField(
        queryset=CajaChica.objects.none(),
        label='Caja Chica',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Selecciona la caja para la que deseas generar el código'
    )

    rol = forms.ChoiceField(
        choices=[
            ('TESORERO_CAJA', 'Tesorero de Caja'),
            ('COLABORADOR_CAJA', 'Colaborador de Caja'),
        ],
        label='Rol en la Caja',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text='Tesorero puede crear movimientos, Colaborador solo puede ver'
    )

    dias_expiracion = forms.IntegerField(
        initial=30,
        min_value=1,
        max_value=365,
        label='Días de Expiración',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'value': 30
        }),
        help_text='El código expirará después de estos días'
    )

    def __init__(self, iglesia=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrar solo cajas activas de la iglesia
        if iglesia:
            self.fields['caja_chica'].queryset = CajaChica.objects.filter(
                iglesia=iglesia,
                activa=True
            )

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Generar Código', css_class='btn btn-success'))


class FiltroCajaChicaForm(forms.Form):
    """Formulario para filtrar movimientos de caja chica"""

    mes = forms.CharField(
        required=False,
        label='Mes',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    tipo = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('INGRESO', 'Ingresos'),
            ('EGRESO', 'Egresos'),
        ],
        required=False,
        label='Tipo',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    buscar = forms.CharField(
        required=False,
        label='Buscar',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar en concepto...'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'form-inline'
        self.helper.add_input(Submit('submit', 'Filtrar', css_class='btn btn-primary'))
