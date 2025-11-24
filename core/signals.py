from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from core.models import Movimiento, Iglesia, SaldoMensual
from core.utils import calcular_saldo_mes
from django.core.exceptions import PermissionDenied
from django.utils import timezone


@receiver(post_save, sender=Movimiento)
def actualizar_saldo_mensual(sender, instance, created, **kwargs):
    """
    Actualiza el saldo mensual cuando se crea o modifica un movimiento
    """
    año_mes = instance.fecha.strftime('%Y-%m')
    calcular_saldo_mes(instance.iglesia, año_mes)


@receiver(post_save, sender=Iglesia)
def crear_categorias_default(sender, instance, created, **kwargs):
    """
    Crea categorías por defecto cuando se crea una nueva iglesia
    """
    if created:
        from core.models import CategoriaIngreso, CategoriaEgreso

        # Categorías de ingreso por defecto
        categorias_ingreso = [
            {'codigo': 'OFRENDA', 'nombre': 'Ofrendas'},
            {'codigo': 'DONACION', 'nombre': 'Donaciones'},
            {'codigo': 'EVENTO', 'nombre': 'Eventos Especiales'},
            {'codigo': 'OTRO_ING', 'nombre': 'Otros Ingresos'},
        ]

        for cat in categorias_ingreso:
            CategoriaIngreso.objects.create(
                iglesia=instance,
                **cat
            )

        # Categorías de egreso por defecto
        categorias_egreso = [
            {'codigo': 'OFRENDA', 'nombre': 'Ofrendas'},
            {'codigo': 'ALQUILER', 'nombre': 'Alquiler'},
            {'codigo': 'SERVICIOS', 'nombre': 'Servicios (Luz, Gas, Agua)'},
            {'codigo': 'IMPUESTO', 'nombre': 'Impuestos'},
            {'codigo': 'SUELDOS', 'nombre': 'Sueldos'},
            {'codigo': 'MISIONES', 'nombre': 'Misiones'},
            {'codigo': 'MANTENIMIENTO', 'nombre': 'Mantenimiento'},
            {'codigo': 'EVENTOS', 'nombre': 'Eventos y Actividades'},
            {'codigo': 'AYUDA_MUTUA', 'nombre': 'Ayuda Mutua'},
            {'codigo': 'OTRO_EGR', 'nombre': 'Otros Egresos'},
        ]

        for cat in categorias_egreso:
            CategoriaEgreso.objects.create(
                iglesia=instance,
                **cat
            )


@receiver(pre_save, sender=Movimiento)
def validar_permisos_iglesia(sender, instance, **kwargs):
    """
    Valida que el usuario solo pueda crear movimientos para su propia iglesia
    """
    if instance.creado_por and instance.creado_por.iglesia != instance.iglesia:
        raise PermissionDenied('No tienes permisos para crear movimientos en esta iglesia')

    # Si hay aprobador, validar iglesia
    if instance.aprobado_por and instance.aprobado_por.iglesia != instance.iglesia:
        raise PermissionDenied('El aprobador debe pertenecer a la misma iglesia')

    # Si se está aprobando, establecer fecha de aprobación
    if instance.aprobado_por and not instance.fecha_aprobacion:
        instance.fecha_aprobacion = timezone.now()


# ============================================
# SIGNALS PARA CAJAS CHICAS
# ============================================

@receiver(pre_save, sender='core.MovimientoCajaChica')
def validar_permisos_caja_chica(sender, instance, **kwargs):
    """
    Valida que el usuario tenga permisos para crear movimientos en esta caja
    """
    from core.models import MovimientoCajaChica, UsuarioCajaChica

    usuario = instance.creado_por
    caja = instance.caja_chica

    # Si es ADMIN de la iglesia, OK
    if usuario.rol == 'ADMIN' and usuario.iglesia == caja.iglesia:
        # Si se está aprobando, establecer fecha de aprobación
        if instance.aprobado_por and not instance.fecha_aprobacion:
            instance.fecha_aprobacion = timezone.now()
        return

    # Verificar que esté asignado a la caja
    asignacion = UsuarioCajaChica.objects.filter(
        usuario=usuario,
        caja_chica=caja
    ).first()

    if not asignacion:
        raise PermissionDenied('No tienes permisos para crear movimientos en esta caja')

    # Si es colaborador, no puede crear movimientos
    if asignacion.rol_caja == 'COLABORADOR_CAJA':
        raise PermissionDenied('Los colaboradores no pueden crear movimientos')

    # Si se está aprobando, establecer fecha de aprobación
    if instance.aprobado_por and not instance.fecha_aprobacion:
        instance.fecha_aprobacion = timezone.now()


@receiver(post_save, sender='core.TransferenciaCajaChica')
def crear_movimientos_transferencia(sender, instance, created, **kwargs):
    """
    Cuando se crea una transferencia, genera automáticamente
    los dos movimientos (egreso e ingreso).
    """
    from core.models import TransferenciaCajaChica

    if created and not instance.movimiento_egreso and not instance.movimiento_ingreso:
        instance.crear_movimientos()
