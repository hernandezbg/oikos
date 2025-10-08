from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal

class Iglesia(models.Model):
    nombre = models.CharField(max_length=200)
    direccion = models.CharField(max_length=300, blank=True, null=True)
    localidad = models.CharField(max_length=100, blank=True, null=True)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    celular = models.CharField(max_length=50, blank=True, null=True, help_text="Celular con WhatsApp")
    email = models.EmailField(blank=True, null=True)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Iglesia'
        verbose_name_plural = 'Iglesias'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    ROLES = (
        ('ADMIN', 'Administrador'),
        ('TESORERO', 'Tesorero'),
        ('PASTOR', 'Pastor'),
        ('COLABORADOR', 'Colaborador'),
    )

    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='usuarios', null=True, blank=True)
    celular = models.CharField(max_length=50, blank=True, null=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='COLABORADOR')
    puede_aprobar = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['iglesia', 'username']

    def __str__(self):
        iglesia_nombre = self.iglesia.nombre if self.iglesia else 'Sin iglesia'
        return f"{self.get_full_name() or self.username} ({iglesia_nombre})"

    # Métodos de permisos
    @property
    def puede_gestionar_usuarios(self):
        """Solo ADMIN puede gestionar usuarios de su iglesia"""
        return self.rol == 'ADMIN'

    @property
    def puede_crear_movimientos(self):
        """ADMIN y TESORERO pueden crear movimientos"""
        return self.rol in ['ADMIN', 'TESORERO']

    @property
    def puede_anular_movimientos(self):
        """ADMIN y TESORERO con permiso pueden anular"""
        return self.puede_aprobar and self.rol in ['ADMIN', 'TESORERO']

    @property
    def puede_eliminar_movimientos(self):
        """Solo ADMIN puede eliminar movimientos"""
        return self.rol == 'ADMIN'

    @property
    def puede_generar_reportes(self):
        """ADMIN, TESORERO y PASTOR pueden generar reportes"""
        return self.rol in ['ADMIN', 'TESORERO', 'PASTOR']

    @property
    def puede_ver_detalles_completos(self):
        """ADMIN, TESORERO y PASTOR ven detalles completos"""
        return self.rol in ['ADMIN', 'TESORERO', 'PASTOR']


class CodigoInvitacion(models.Model):
    """
    Código de invitación para unirse a una iglesia con un rol específico.
    Formato: T4K8M9 (6 caracteres: Rol + 5 alfanuméricos)
    """
    ROLES_INVITACION = (
        ('TESORERO', 'Tesorero'),
        ('PASTOR', 'Pastor'),
        ('COLABORADOR', 'Colaborador'),
    )

    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='codigos_invitacion')
    codigo = models.CharField(max_length=10, unique=True, db_index=True)
    rol = models.CharField(max_length=20, choices=ROLES_INVITACION)

    creado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='codigos_generados'
    )
    usado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='codigo_usado'
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    fecha_uso = models.DateTimeField(null=True, blank=True)

    activo = models.BooleanField(default=True)
    usos_maximos = models.IntegerField(default=1)
    usos_actuales = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Código de Invitación'
        verbose_name_plural = 'Códigos de Invitación'
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.codigo} - {self.get_rol_display()} ({self.iglesia.nombre})"

    @property
    def esta_vigente(self):
        """Verifica si el código está activo y no expiró"""
        from django.utils import timezone
        return (
            self.activo and
            self.usos_actuales < self.usos_maximos and
            self.fecha_expiracion > timezone.now()
        )

    def usar_codigo(self, usuario):
        """Marca el código como usado por un usuario"""
        from django.utils import timezone

        if not self.esta_vigente:
            raise ValueError("Código no válido o expirado")

        self.usado_por = usuario
        self.fecha_uso = timezone.now()
        self.usos_actuales += 1

        if self.usos_actuales >= self.usos_maximos:
            self.activo = False

        self.save()

    @staticmethod
    def generar_codigo_unico():
        """
        Genera un código corto y único de 6 caracteres: T4K8M9
        Usa solo caracteres no ambiguos (sin 0, O, 1, I, L)
        """
        import secrets
        import string

        # Caracteres sin ambigüedad: sin 0/O, 1/I/L
        chars = '23456789ABCDEFGHJKMNPQRSTUVWXYZ'

        while True:
            # Generar 5 caracteres aleatorios
            codigo_base = ''.join(secrets.choice(chars) for _ in range(5))

            # El prefijo de rol se agregará después
            # Por ahora solo verificamos que el formato base no exista
            if not CodigoInvitacion.objects.filter(codigo__endswith=codigo_base).exists():
                return codigo_base

    @staticmethod
    def crear(iglesia, rol, creado_por, dias_expiracion=30):
        """Crea un nuevo código de invitación"""
        from django.utils import timezone
        from datetime import timedelta

        # Prefijo según rol
        prefijos = {
            'TESORERO': 'T',
            'PASTOR': 'P',
            'COLABORADOR': 'C',
        }

        # Generar código único: T4K8M9
        codigo_base = CodigoInvitacion.generar_codigo_unico()
        codigo_completo = f"{prefijos[rol]}{codigo_base}"

        return CodigoInvitacion.objects.create(
            iglesia=iglesia,
            codigo=codigo_completo,
            rol=rol,
            creado_por=creado_por,
            fecha_expiracion=timezone.now() + timedelta(days=dias_expiracion),
            activo=True,
            usos_maximos=1
        )


class CategoriaIngreso(models.Model):
    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='categorias_ingreso')
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoría de Ingreso'
        verbose_name_plural = 'Categorías de Ingreso'
        ordering = ['iglesia', 'codigo']
        unique_together = ['iglesia', 'codigo']

    def __str__(self):
        return self.nombre


class CategoriaEgreso(models.Model):
    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='categorias_egreso')
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=100)
    presupuesto_mensual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Presupuesto mensual asignado para esta categoría"
    )
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoría de Egreso'
        verbose_name_plural = 'Categorías de Egreso'
        ordering = ['iglesia', 'codigo']
        unique_together = ['iglesia', 'codigo']

    def __str__(self):
        return self.nombre


class Movimiento(models.Model):
    TIPOS = (
        ('INGRESO', 'Ingreso'),
        ('EGRESO', 'Egreso'),
    )

    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    fecha = models.DateField()
    categoria_ingreso = models.ForeignKey(
        CategoriaIngreso,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos'
    )
    categoria_egreso = models.ForeignKey(
        CategoriaEgreso,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos'
    )
    concepto = models.TextField()
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    comprobante_nro = models.CharField(max_length=50, blank=True, null=True)
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='movimientos_creados'
    )
    aprobado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_aprobados'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    # Campos para anulación
    anulado = models.BooleanField(default=False)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)
    anulado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_anulados'
    )

    class Meta:
        verbose_name = 'Movimiento'
        verbose_name_plural = 'Movimientos'
        ordering = ['-fecha', '-fecha_creacion']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.concepto[:50]} - ${self.monto}"

    def generar_numero_comprobante(self):
        """
        Genera el número de comprobante automáticamente.
        Formato: I-0001 para ingresos, E-0001 para egresos
        """
        if not self.iglesia:
            return None

        # Obtener el último movimiento del mismo tipo de esta iglesia
        prefijo = 'I' if self.tipo == 'INGRESO' else 'E'

        ultimo_movimiento = Movimiento.objects.filter(
            iglesia=self.iglesia,
            tipo=self.tipo,
            comprobante_nro__startswith=prefijo
        ).order_by('-comprobante_nro').first()

        if ultimo_movimiento and ultimo_movimiento.comprobante_nro:
            # Extraer el número del último comprobante
            try:
                ultimo_numero = int(ultimo_movimiento.comprobante_nro.split('-')[1])
                nuevo_numero = ultimo_numero + 1
            except (IndexError, ValueError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1

        return f"{prefijo}-{nuevo_numero:04d}"

    def save(self, *args, **kwargs):
        # Generar número de comprobante si no existe
        if not self.comprobante_nro and self.iglesia:
            self.comprobante_nro = self.generar_numero_comprobante()
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError

        # Validar que tenga la categoría correcta según el tipo
        if self.tipo == 'INGRESO' and not self.categoria_ingreso:
            raise ValidationError('Debe seleccionar una categoría de ingreso')
        if self.tipo == 'EGRESO' and not self.categoria_egreso:
            raise ValidationError('Debe seleccionar una categoría de egreso')

        # Validar que las categorías sean de la misma iglesia (solo si iglesia ya está asignada)
        if self.iglesia_id:
            if self.categoria_ingreso and self.categoria_ingreso.iglesia_id != self.iglesia_id:
                raise ValidationError('La categoría de ingreso debe pertenecer a la misma iglesia')
            if self.categoria_egreso and self.categoria_egreso.iglesia_id != self.iglesia_id:
                raise ValidationError('La categoría de egreso debe pertenecer a la misma iglesia')


class SaldoMensual(models.Model):
    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='saldos_mensuales')
    año_mes = models.CharField(max_length=7, help_text="Formato: YYYY-MM")  # Ejemplo: 2024-01
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_ingresos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_egresos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Saldo Mensual'
        verbose_name_plural = 'Saldos Mensuales'
        ordering = ['-año_mes']
        unique_together = ['iglesia', 'año_mes']

    def __str__(self):
        return f"{self.iglesia.nombre} - {self.año_mes} - Saldo: ${self.saldo_final}"

    def calcular_saldo_final(self):
        self.saldo_final = self.saldo_inicial + self.total_ingresos - self.total_egresos
        return self.saldo_final
