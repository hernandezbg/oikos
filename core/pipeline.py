"""
Custom pipeline para Python Social Auth.
Maneja la asignación de iglesia después del login con Google.
"""
from django.shortcuts import redirect
from core.models import Usuario


def assign_iglesia(backend, user, response, *args, **kwargs):
    """
    Pipeline personalizado para verificar si el usuario tiene iglesia asignada.
    Si no tiene iglesia, redirige al formulario de registro de iglesia.
    """
    # Si es staff o superuser, no necesita iglesia
    if user.is_staff or user.is_superuser:
        return

    # Verificar si el usuario tiene iglesia
    if not hasattr(user, 'iglesia') or user.iglesia is None:
        # Guardar en la sesión que necesita registrar iglesia
        backend.strategy.session_set('needs_iglesia_registration', True)
        backend.strategy.session_set('partial_pipeline_token', kwargs.get('partial_token'))

        # El redirect se manejará en el adapter/middleware
        return

    # Si ya tiene iglesia, continuar normalmente
    return
