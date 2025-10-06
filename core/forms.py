from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Div, HTML, Fieldset
from core.models import Movimiento, CategoriaIngreso, CategoriaEgreso, Usuario, Iglesia
from decimal import Decimal


class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['tipo', 'fecha', 'categoria_ingreso', 'categoria_egreso', 'concepto', 'monto']
        widgets = {
            'fecha': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'tipo': forms.RadioSelect(
                attrs={'class': 'form-check-input'}
            ),
            'concepto': forms.Textarea(
                attrs={'rows': 3, 'class': 'form-control'}
            ),
            'monto': forms.NumberInput(
                attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}
            ),
        }
        labels = {
            'tipo': 'Tipo de Movimiento',
            'fecha': 'Fecha',
            'categoria_ingreso': 'Categoría de Ingreso',
            'categoria_egreso': 'Categoría de Egreso',
            'concepto': 'Concepto/Descripción',
            'monto': 'Monto ($)',
        }

    def __init__(self, *args, **kwargs):
        self.iglesia = kwargs.pop('iglesia', None)
        super().__init__(*args, **kwargs)

        # Filtrar categorías por iglesia y remover opción vacía
        if self.iglesia:
            self.fields['categoria_ingreso'].queryset = CategoriaIngreso.objects.filter(
                iglesia=self.iglesia,
                activa=True
            )
            self.fields['categoria_egreso'].queryset = CategoriaEgreso.objects.filter(
                iglesia=self.iglesia,
                activa=True
            )
            # Remover la opción "--------"
            self.fields['categoria_ingreso'].empty_label = None
            self.fields['categoria_egreso'].empty_label = None

        # Hacer campos opcionales inicialmente
        self.fields['categoria_ingreso'].required = False
        self.fields['categoria_egreso'].required = False

        # Remover opción vacía del tipo (no hay opción ---------)
        self.fields['tipo'].choices = Movimiento.TIPOS

        # Configurar Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Row(
                Column('tipo', css_class='form-group col-md-12 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('fecha', css_class='form-group col-md-6 mb-0'),
                Column('monto', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Div(
                'categoria_ingreso',
                css_class='categoria-ingreso-field',
                css_id='categoria-ingreso-div'
            ),
            Div(
                'categoria_egreso',
                css_class='categoria-egreso-field',
                css_id='categoria-egreso-div'
            ),
            'concepto',
            HTML('<div id="confirmacion-monto" class="alert alert-warning d-none" role="alert">'
                 'El monto ingresado es mayor a $1.000.000. ¿Está seguro de continuar?'
                 '</div>'),
            Submit('submit', 'Guardar Movimiento', css_class='btn btn-primary')
        )

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        categoria_ingreso = cleaned_data.get('categoria_ingreso')
        categoria_egreso = cleaned_data.get('categoria_egreso')
        monto = cleaned_data.get('monto')

        # Validar categoría según tipo
        if tipo == 'INGRESO':
            if not categoria_ingreso:
                raise ValidationError({
                    'categoria_ingreso': 'Debe seleccionar una categoría de ingreso'
                })
            cleaned_data['categoria_egreso'] = None

        elif tipo == 'EGRESO':
            if not categoria_egreso:
                raise ValidationError({
                    'categoria_egreso': 'Debe seleccionar una categoría de egreso'
                })
            cleaned_data['categoria_ingreso'] = None

        # Validar monto
        if monto and monto <= 0:
            raise ValidationError({
                'monto': 'El monto debe ser mayor a cero'
            })

        return cleaned_data


class FiltroMovimientosForm(forms.Form):
    mes = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={'type': 'month', 'class': 'form-control'}
        ),
        label='Mes'
    )
    tipo = forms.ChoiceField(
        required=False,
        choices=[('', 'Todos')] + list(Movimiento.TIPOS),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Tipo'
    )
    categoria = forms.ChoiceField(
        required=False,
        choices=[('', 'Todas')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Categoría'
    )
    buscar = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={'class': 'form-control', 'placeholder': 'Buscar por concepto...'}
        ),
        label='Buscar'
    )

    def __init__(self, *args, **kwargs):
        self.iglesia = kwargs.pop('iglesia', None)
        super().__init__(*args, **kwargs)

        # Agregar categorías al filtro
        if self.iglesia:
            categorias = []
            for cat in CategoriaIngreso.objects.filter(iglesia=self.iglesia, activa=True):
                categorias.append((f'ingreso_{cat.id}', f'[Ingreso] {cat.nombre}'))
            for cat in CategoriaEgreso.objects.filter(iglesia=self.iglesia, activa=True):
                categorias.append((f'egreso_{cat.id}', f'[Egreso] {cat.nombre}'))

            self.fields['categoria'].choices = [('', 'Todas')] + categorias


class RegistroForm(UserCreationForm):
    # Campos de la iglesia
    nombre_iglesia = forms.CharField(
        max_length=200,
        required=True,
        label='Nombre de la Iglesia',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Iglesia Bautista Central'})
    )
    direccion_iglesia = forms.CharField(
        max_length=300,
        required=False,
        label='Dirección',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle y número'})
    )
    telefono_iglesia = forms.CharField(
        max_length=50,
        required=False,
        label='Teléfono de la Iglesia',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '011-1234-5678'})
    )
    email_iglesia = forms.EmailField(
        required=False,
        label='Email de la Iglesia',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contacto@iglesia.org'})
    )

    # Campos del usuario
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label='Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'})
    )
    email = forms.EmailField(
        required=True,
        label='Email Personal',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'})
    )
    celular = forms.CharField(
        max_length=50,
        required=False,
        label='Celular',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '11-1234-5678'})
    )

    class Meta:
        model = Usuario
        fields = ['username', 'first_name', 'last_name', 'email', 'celular', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario'}),
        }
        labels = {
            'username': 'Nombre de Usuario',
            'password1': 'Contraseña',
            'password2': 'Confirmar Contraseña',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Actualizar widgets para password fields
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Mínimo 8 caracteres'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Repite la contraseña'})

        # Configurar Crispy Forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                'Datos de la Iglesia',
                Row(
                    Column('nombre_iglesia', css_class='form-group col-md-12 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('direccion_iglesia', css_class='form-group col-md-8 mb-0'),
                    Column('telefono_iglesia', css_class='form-group col-md-4 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('email_iglesia', css_class='form-group col-md-12 mb-0'),
                    css_class='form-row'
                ),
                css_class='border p-3 mb-3 rounded bg-light'
            ),
            Fieldset(
                'Tus Datos (Tesorero)',
                Row(
                    Column('first_name', css_class='form-group col-md-6 mb-0'),
                    Column('last_name', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('username', css_class='form-group col-md-6 mb-0'),
                    Column('celular', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('email', css_class='form-group col-md-12 mb-0'),
                    css_class='form-row'
                ),
                Row(
                    Column('password1', css_class='form-group col-md-6 mb-0'),
                    Column('password2', css_class='form-group col-md-6 mb-0'),
                    css_class='form-row'
                ),
                css_class='border p-3 mb-3 rounded bg-light'
            ),
            Submit('submit', 'Registrar Iglesia', css_class='btn btn-primary btn-lg w-100')
        )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Usuario.objects.filter(username=username).exists():
            raise ValidationError('Este nombre de usuario ya está en uso')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if Usuario.objects.filter(email=email).exists():
            raise ValidationError('Este email ya está registrado')
        return email

    def save(self, commit=True):
        # Crear la iglesia primero
        iglesia = Iglesia.objects.create(
            nombre=self.cleaned_data['nombre_iglesia'],
            direccion=self.cleaned_data.get('direccion_iglesia', ''),
            telefono=self.cleaned_data.get('telefono_iglesia', ''),
            email=self.cleaned_data.get('email_iglesia', ''),
            activa=True
        )

        # Crear el usuario
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.celular = self.cleaned_data.get('celular', '')
        user.iglesia = iglesia
        user.rol = 'TESORERO'
        user.puede_aprobar = True

        if commit:
            user.save()

        return user
