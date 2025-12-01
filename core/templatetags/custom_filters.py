from django import template
from django.utils.safestring import mark_safe
from django.http import QueryDict
from core.utils import formato_pesos as formato_pesos_util, formato_moneda as formato_moneda_util

register = template.Library()


@register.filter(name='formato_pesos')
def formato_pesos(value):
    """
    Filtro de template para formatear montos en pesos argentinos
    """
    return formato_pesos_util(value)


@register.filter(name='formato_moneda')
def formato_moneda(value, moneda='ARS'):
    """
    Filtro de template para formatear montos según la moneda especificada
    Uso: {{ monto|formato_moneda:"USD" }}
    """
    return formato_moneda_util(value, moneda)


@register.filter(name='formato_monto_movimiento')
def formato_monto_movimiento(movimiento):
    """
    Filtro para formatear el monto de un movimiento con color según el tipo
    """
    monto_formateado = formato_pesos_util(movimiento.monto)

    if movimiento.tipo == 'EGRESO':
        # Mostrar en negativo y rojo
        return mark_safe(f'<span class="text-danger fw-bold">-{monto_formateado}</span>')
    else:
        # Mostrar en verde
        return mark_safe(f'<span class="text-success fw-bold">{monto_formateado}</span>')


@register.simple_tag
def url_replace(request, **kwargs):
    """
    Template tag para construir URLs reemplazando parámetros GET.
    Útil para paginación manteniendo filtros actuales.

    Uso: {% url_replace request page=2 %}
    """
    query = request.GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()
