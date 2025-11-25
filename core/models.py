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

    # Términos y Condiciones
    terminos_aceptados = models.BooleanField(default=False, help_text="Indica si el usuario aceptó los términos y condiciones")
    fecha_aceptacion_terminos = models.DateTimeField(null=True, blank=True, help_text="Fecha y hora en que aceptó los términos")

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

    # ============================================
    # MÉTODOS DE PERMISOS PARA CAJAS CHICAS
    # ============================================

    @property
    def tiene_acceso_cajas_chicas(self):
        """Verifica si el usuario tiene acceso a alguna caja chica"""
        return self.cajas_asignadas.exists()

    @property
    def tiene_acceso_movimientos(self):
        """
        Solo usuarios con rol de iglesia (no solo de caja) pueden ver Movimientos.
        """
        # Si es usuario solo de caja, NO tiene acceso a movimientos
        if self.es_usuario_solo_caja:
            return False
        # Si es ADMIN, TESORERO, PASTOR o COLABORADOR de la iglesia → Sí
        return self.rol in ['ADMIN', 'TESORERO', 'PASTOR', 'COLABORADOR']

    @property
    def es_usuario_solo_caja(self):
        """
        Verifica si el usuario SOLO tiene acceso a cajas, no a la iglesia principal.
        Un usuario es "solo caja" si:
        - Tiene cajas asignadas Y
        - Su rol es COLABORADOR (el rol por defecto cuando se une con código de caja)
          y no tiene permisos reales de iglesia
        """
        # Verificar si tiene cajas y si su rol es el default sin permisos de iglesia
        # Los roles ADMIN, TESORERO, y PASTOR tienen acceso a la iglesia
        # COLABORADOR sin otros indicadores = solo acceso a caja
        return (
            self.tiene_acceso_cajas_chicas and
            self.rol == 'COLABORADOR' and
            not self.is_staff  # Staff siempre tiene acceso completo
        )

    def puede_gestionar_caja_chica(self, caja_chica):
        """Verifica si puede gestionar (crear/editar/eliminar) una caja chica específica"""
        # Solo ADMIN puede crear/eliminar cajas
        if self.rol == 'ADMIN' and self.iglesia == caja_chica.iglesia:
            return True
        return False

    def puede_crear_movimiento_caja(self, caja_chica):
        """Verifica si puede crear movimientos en una caja específica"""
        if self.rol == 'ADMIN' and self.iglesia == caja_chica.iglesia:
            return True

        # Verificar si es tesorero de esta caja específica
        asignacion = self.cajas_asignadas.filter(
            caja_chica=caja_chica,
            rol_caja='TESORERO_CAJA'
        ).first()

        return asignacion is not None

    def puede_ver_caja(self, caja_chica):
        """Verifica si puede ver una caja específica"""
        # ADMIN puede ver todas las cajas de su iglesia
        if self.rol == 'ADMIN' and self.iglesia == caja_chica.iglesia:
            return True

        # Verificar si está asignado a esta caja
        return self.cajas_asignadas.filter(caja_chica=caja_chica).exists()


class CodigoInvitacion(models.Model):
    """
    Código de invitación para unirse a una iglesia con un rol específico
    o para unirse a una caja chica específica.
    Formato: T4K8M9 (Rol + 5 alfanuméricos) para iglesia
    Formato: TC-ABC123 o CC-XYZ789 para cajas chicas
    """
    ROLES_INVITACION = (
        ('TESORERO', 'Tesorero'),
        ('PASTOR', 'Pastor'),
        ('COLABORADOR', 'Colaborador'),
        ('TESORERO_CAJA', 'Tesorero de Caja Chica'),
        ('COLABORADOR_CAJA', 'Colaborador de Caja Chica'),
    )

    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='codigos_invitacion')
    codigo = models.CharField(max_length=10, unique=True, db_index=True)
    rol = models.CharField(max_length=20, choices=ROLES_INVITACION)

    # NUEVO: Soporte para códigos de caja chica
    caja_chica = models.ForeignKey(
        'CajaChica',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='codigos_invitacion',
        help_text='Si está asignado, el código es para unirse a esta caja chica específica'
    )

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
    def crear(iglesia, rol, creado_por, dias_expiracion=30, usos_maximos=1, caja_chica=None):
        """
        Crea un nuevo código de invitación.
        Si caja_chica es None, es para la iglesia.
        Si caja_chica está definido, es para esa caja específica.
        """
        from django.utils import timezone
        from datetime import timedelta

        # Prefijo según rol
        prefijos = {
            'TESORERO': 'T',
            'PASTOR': 'P',
            'COLABORADOR': 'C',
            'TESORERO_CAJA': 'TC',
            'COLABORADOR_CAJA': 'CC',
        }

        # Generar código único: T4K8M9 o TC-ABC123
        codigo_base = CodigoInvitacion.generar_codigo_unico()
        codigo_completo = f"{prefijos[rol]}{codigo_base}"

        return CodigoInvitacion.objects.create(
            iglesia=iglesia,
            caja_chica=caja_chica,
            codigo=codigo_completo,
            rol=rol,
            creado_por=creado_por,
            fecha_expiracion=timezone.now() + timedelta(days=dias_expiracion),
            activo=True,
            usos_maximos=usos_maximos
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


# ============================================
# MODELOS DE CAJAS CHICAS
# ============================================

class CajaChica(models.Model):
    """
    Representa una caja chica dentro de una iglesia.
    Ejemplo: "Caja Jóvenes", "Caja Ministerio Mujeres"
    """
    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='cajas_chicas')
    nombre = models.CharField(max_length=100, help_text="Ej: Caja Jóvenes, Caja Ministerio Mujeres")
    descripcion = models.TextField(blank=True, null=True)
    saldo_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Saldo inicial con el que se crea la caja"
    )

    # Control
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creada_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='cajas_creadas')

    class Meta:
        verbose_name = 'Caja Chica'
        verbose_name_plural = 'Cajas Chicas'
        ordering = ['iglesia', 'nombre']
        unique_together = ['iglesia', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.iglesia.nombre})"

    def calcular_saldo_actual(self):
        """Calcula el saldo actual de la caja"""
        from django.db.models import Sum

        ingresos = MovimientoCajaChica.objects.filter(
            caja_chica=self,
            tipo='INGRESO',
            anulado=False
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        egresos = MovimientoCajaChica.objects.filter(
            caja_chica=self,
            tipo='EGRESO',
            anulado=False
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        return self.saldo_inicial + ingresos - egresos


class MovimientoCajaChica(models.Model):
    """
    Movimientos específicos de una caja chica.
    Similar a Movimiento pero para cajas chicas.
    """
    TIPOS = (
        ('INGRESO', 'Ingreso'),
        ('EGRESO', 'Egreso'),
    )

    caja_chica = models.ForeignKey(CajaChica, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    fecha = models.DateField()
    concepto = models.TextField()
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    comprobante_nro = models.CharField(max_length=50, blank=True, null=True)

    # Categorías (igual que en Movimiento)
    categoria_ingreso = models.ForeignKey(
        'CategoriaIngreso',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_caja_chica'
    )
    categoria_egreso = models.ForeignKey(
        'CategoriaEgreso',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movimientos_caja_chica'
    )

    # Usuarios
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='movimientos_caja_chica_creados'
    )
    aprobado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_caja_chica_aprobados'
    )

    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    # Anulación
    anulado = models.BooleanField(default=False)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)
    anulado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_caja_chica_anulados'
    )

    class Meta:
        verbose_name = 'Movimiento de Caja Chica'
        verbose_name_plural = 'Movimientos de Caja Chica'
        ordering = ['-fecha', '-fecha_creacion']

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.caja_chica.nombre} - {self.concepto[:50]} - ${self.monto}"

    def generar_numero_comprobante(self):
        """
        Genera número de comprobante por caja chica.
        Formato: CC-I-0001, CC-E-0001
        """
        prefijo = 'CC-I' if self.tipo == 'INGRESO' else 'CC-E'

        ultimo = MovimientoCajaChica.objects.filter(
            caja_chica=self.caja_chica,
            tipo=self.tipo,
            comprobante_nro__startswith=prefijo
        ).order_by('-comprobante_nro').first()

        if ultimo and ultimo.comprobante_nro:
            try:
                ultimo_numero = int(ultimo.comprobante_nro.split('-')[2])
                nuevo_numero = ultimo_numero + 1
            except (IndexError, ValueError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1

        return f"{prefijo}-{nuevo_numero:04d}"

    def save(self, *args, **kwargs):
        # Generar número de comprobante si no existe
        if not self.comprobante_nro and self.caja_chica:
            self.comprobante_nro = self.generar_numero_comprobante()
        super().save(*args, **kwargs)


class UsuarioCajaChica(models.Model):
    """
    Relación muchos-a-muchos entre usuarios y cajas chicas.
    Define qué usuarios pueden acceder a qué cajas.
    """
    ROLES_CAJA = (
        ('TESORERO_CAJA', 'Tesorero de Caja'),
        ('COLABORADOR_CAJA', 'Colaborador de Caja'),
    )

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='cajas_asignadas')
    caja_chica = models.ForeignKey(CajaChica, on_delete=models.CASCADE, related_name='usuarios_asignados')
    rol_caja = models.CharField(max_length=20, choices=ROLES_CAJA)
    puede_aprobar = models.BooleanField(default=False)

    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    asignado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='asignaciones_caja_realizadas'
    )

    class Meta:
        verbose_name = 'Usuario de Caja Chica'
        verbose_name_plural = 'Usuarios de Cajas Chicas'
        unique_together = ['usuario', 'caja_chica']

    def __str__(self):
        return f"{self.usuario.username} - {self.caja_chica.nombre} ({self.get_rol_caja_display()})"


class TransferenciaCajaChica(models.Model):
    """
    Representa una transferencia de dinero entre dos cajas chicas.
    Crea automáticamente dos movimientos: egreso en origen, ingreso en destino.
    """
    # Cajas involucradas
    caja_origen = models.ForeignKey(
        CajaChica,
        on_delete=models.CASCADE,
        related_name='transferencias_salida'
    )
    caja_destino = models.ForeignKey(
        CajaChica,
        on_delete=models.CASCADE,
        related_name='transferencias_entrada'
    )

    # Detalles de la transferencia
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    concepto = models.TextField()
    fecha = models.DateField()

    # Control y auditoría
    realizada_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='transferencias_realizadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Movimientos generados automáticamente
    movimiento_egreso = models.OneToOneField(
        MovimientoCajaChica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferencia_egreso'
    )
    movimiento_ingreso = models.OneToOneField(
        MovimientoCajaChica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferencia_ingreso'
    )

    # Anulación
    anulada = models.BooleanField(default=False)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)
    anulada_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferencias_anuladas'
    )

    class Meta:
        verbose_name = 'Transferencia entre Cajas'
        verbose_name_plural = 'Transferencias entre Cajas'
        ordering = ['-fecha', '-fecha_creacion']

    def __str__(self):
        return f"Transferencia {self.caja_origen.nombre} → {self.caja_destino.nombre}: ${self.monto}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # No transferir a la misma caja
        if self.caja_origen == self.caja_destino:
            raise ValidationError('No puedes transferir dinero a la misma caja')

        # Validar que ambas cajas pertenezcan a la misma iglesia
        if self.caja_origen.iglesia != self.caja_destino.iglesia:
            raise ValidationError('Las cajas deben pertenecer a la misma iglesia')

        # Validar saldo suficiente en caja origen
        saldo_origen = self.caja_origen.calcular_saldo_actual()
        if saldo_origen < self.monto:
            raise ValidationError(
                f'Saldo insuficiente en {self.caja_origen.nombre}. '
                f'Saldo disponible: ${saldo_origen}, Monto a transferir: ${self.monto}'
            )

    def crear_movimientos(self):
        """
        Crea los dos movimientos asociados a esta transferencia.
        Se ejecuta automáticamente en el signal post_save.
        """
        # Egreso en caja origen
        self.movimiento_egreso = MovimientoCajaChica.objects.create(
            caja_chica=self.caja_origen,
            tipo='EGRESO',
            fecha=self.fecha,
            concepto=f'Transferencia a {self.caja_destino.nombre}: {self.concepto}',
            monto=self.monto,
            creado_por=self.realizada_por,
            aprobado_por=self.realizada_por
        )

        # Ingreso en caja destino
        self.movimiento_ingreso = MovimientoCajaChica.objects.create(
            caja_chica=self.caja_destino,
            tipo='INGRESO',
            fecha=self.fecha,
            concepto=f'Transferencia desde {self.caja_origen.nombre}: {self.concepto}',
            monto=self.monto,
            creado_por=self.realizada_por,
            aprobado_por=self.realizada_por
        )

        self.save()

    def anular_transferencia(self, usuario, motivo):
        """Anula la transferencia y sus movimientos asociados"""
        from django.utils import timezone

        self.anulada = True
        self.anulada_por = usuario
        self.fecha_anulacion = timezone.now()
        self.motivo_anulacion = motivo
        self.save()

        # Anular movimientos asociados
        if self.movimiento_egreso:
            self.movimiento_egreso.anulado = True
            self.movimiento_egreso.anulado_por = usuario
            self.movimiento_egreso.fecha_anulacion = timezone.now()
            self.movimiento_egreso.motivo_anulacion = f'Anulación de transferencia: {motivo}'
            self.movimiento_egreso.save()

        if self.movimiento_ingreso:
            self.movimiento_ingreso.anulado = True
            self.movimiento_ingreso.anulado_por = usuario
            self.movimiento_ingreso.fecha_anulacion = timezone.now()
            self.movimiento_ingreso.motivo_anulacion = f'Anulación de transferencia: {motivo}'
            self.movimiento_ingreso.save()
