from django.conf import settings

def app_name(request):
    """
    Context processor para hacer disponible el nombre de la aplicación en todas las templates
    """
    return {
        'APP_NAME': settings.APP_NAME
    }
