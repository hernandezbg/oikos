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
            {'codigo': 'DIEZMO', 'nombre': 'Diezmos', 'es_recurrente': True},
            {'codigo': 'OFRENDA', 'nombre': 'Ofrendas', 'es_recurrente': True},
            {'codigo': 'DONACION', 'nombre': 'Donaciones', 'es_recurrente': False},
            {'codigo': 'EVENTO', 'nombre': 'Eventos Especiales', 'es_recurrente': False},
            {'codigo': 'OTRO_ING', 'nombre': 'Otros Ingresos', 'es_recurrente': False},
        ]

        for cat in categorias_ingreso:
            CategoriaIngreso.objects.create(
                iglesia=instance,
                **cat
            )

        # Categorías de egreso por defecto
        categorias_egreso = [
            {'codigo': 'ALQUILER', 'nombre': 'Alquiler Local', 'es_fijo_mensual': True},
            {'codigo': 'SERVICIOS', 'nombre': 'Servicios (Luz, Gas, Agua)', 'es_fijo_mensual': True},
            {'codigo': 'SUELDOS', 'nombre': 'Sueldos Personal', 'es_fijo_mensual': True},
            {'codigo': 'MISIONES', 'nombre': 'Misiones', 'es_fijo_mensual': False},
            {'codigo': 'MANTENIMIENTO', 'nombre': 'Mantenimiento', 'es_fijo_mensual': False},
            {'codigo': 'EVENTOS', 'nombre': 'Eventos y Actividades', 'es_fijo_mensual': False},
            {'codigo': 'AYUDA_SOCIAL', 'nombre': 'Ayuda Social', 'es_fijo_mensual': False},
            {'codigo': 'OTRO_EGR', 'nombre': 'Otros Egresos', 'es_fijo_mensual': False},
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
