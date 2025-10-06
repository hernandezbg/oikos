from django import forms
from django.core.exceptions import ValidationError
from core.models import Iglesia


class RegistroIglesiaGoogleForm(forms.ModelForm):
    """
    Formulario para registrar la iglesia después de autenticarse con Google.
    El usuario ya está autenticado, solo falta asignarle una iglesia.
    """

    class Meta:
        model = Iglesia
        fields = ['nombre', 'direccion', 'telefono', 'email']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Iglesia Bautista Central'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Calle y número'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '011-1234-5678'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contacto@iglesia.org'
            }),
        }
        labels = {
            'nombre': 'Nombre de la Iglesia',
            'direccion': 'Dirección',
            'telefono': 'Teléfono de la Iglesia',
            'email': 'Email de la Iglesia',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo el nombre es obligatorio
        self.fields['nombre'].required = True
        self.fields['direccion'].required = False
        self.fields['telefono'].required = False
        self.fields['email'].required = False

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if not nombre or len(nombre.strip()) < 3:
            raise ValidationError('El nombre de la iglesia debe tener al menos 3 caracteres')
        return nombre
