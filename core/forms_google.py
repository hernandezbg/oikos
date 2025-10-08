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
        fields = ['nombre', 'direccion', 'localidad', 'provincia', 'celular', 'email']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Iglesia Cristiana Evangélica'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Calle y número'
            }),
            'localidad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: San Martín, CABA, etc.'
            }),
            'provincia': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Buenos Aires, Córdoba, etc.'
            }),
            'celular': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '11-1234-5678'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contacto@iglesia.org'
            }),
        }
        labels = {
            'nombre': 'Nombre de la Iglesia',
            'direccion': 'Dirección',
            'localidad': 'Localidad',
            'provincia': 'Provincia',
            'celular': 'Celular (WhatsApp)',
            'email': 'Email de la Iglesia',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo el nombre es obligatorio
        self.fields['nombre'].required = True
        self.fields['direccion'].required = False
        self.fields['localidad'].required = False
        self.fields['provincia'].required = False
        self.fields['celular'].required = False
        self.fields['email'].required = False

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if not nombre or len(nombre.strip()) < 3:
            raise ValidationError('El nombre de la iglesia debe tener al menos 3 caracteres')
        return nombre
