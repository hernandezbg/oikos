from django import forms
from django.core.exceptions import ValidationError
from core.models import CodigoInvitacion


class GenerarCodigoInvitacionForm(forms.Form):
    """Formulario para que el ADMIN genere códigos de invitación"""

    rol = forms.ChoiceField(
        choices=CodigoInvitacion.ROLES_INVITACION,
        label='Rol del Usuario',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    dias_expiracion = forms.IntegerField(
        initial=30,
        min_value=1,
        max_value=365,
        label='Días de vigencia',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='El código expirará después de estos días (máx. 365)'
    )

    usos_maximos = forms.IntegerField(
        initial=1,
        min_value=1,
        max_value=100,
        label='Usos permitidos',
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text='Cuántas personas pueden usar este código (típicamente 1)'
    )


class ValidarCodigoInvitacionForm(forms.Form):
    """Formulario para validar código de invitación al registrarse"""

    codigo = forms.CharField(
        max_length=10,
        label='Código de Invitación',
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg text-uppercase text-center',
            'style': 'letter-spacing: 0.5rem; font-weight: bold; font-size: 1.5rem;',
            'autocomplete': 'off',
            'pattern': '[TCPtcp][2-9A-HJ-NP-Za-hj-np-z]{5}',
        })
    )

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo', '').strip().upper()

        if not codigo:
            raise ValidationError('Debes ingresar un código de invitación')

        # Buscar el código
        try:
            codigo_obj = CodigoInvitacion.objects.get(codigo=codigo)
        except CodigoInvitacion.DoesNotExist:
            raise ValidationError('Código no válido. Verifica que esté bien escrito.')

        # Validar que esté vigente
        if not codigo_obj.esta_vigente:
            if codigo_obj.usos_actuales >= codigo_obj.usos_maximos:
                raise ValidationError('Este código ya fue utilizado.')
            elif not codigo_obj.activo:
                raise ValidationError('Este código ha sido revocado.')
            else:
                raise ValidationError('Este código ha expirado.')

        # Guardar el objeto código para usarlo después
        self.codigo_obj = codigo_obj

        return codigo


class SeleccionTipoRegistroForm(forms.Form):
    """Formulario para seleccionar si crear iglesia o usar código"""

    tipo = forms.ChoiceField(
        choices=[
            ('crear_iglesia', 'Registrarme por primera vez'),
            ('usar_codigo', 'Ya tengo un código de invitación'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='¿Cómo deseas continuar?'
    )
