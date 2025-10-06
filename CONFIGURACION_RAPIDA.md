# Configuración Rápida de Google OAuth

## IMPORTANTE: Configuración Local (Sin credenciales de Google)

Si quieres probar el sistema SIN configurar Google OAuth todavía, puedes usar el login tradicional:

1. Ve a `http://localhost:8000/login/` (no `/accounts/login/`)
2. Usa el usuario administrador que creaste anteriormente

## Para configurar Google OAuth (Producción):

### 1. Obtener credenciales de Google

1. Ve a https://console.cloud.google.com/
2. Crea un proyecto nuevo o selecciona uno existente
3. Ve a **APIs y servicios** > **Credenciales**
4. Haz clic en **Crear credenciales** > **ID de cliente de OAuth 2.0**
5. Configura:
   - Tipo: Aplicación web
   - Orígenes autorizados: `http://localhost:8000`
   - URIs de redirección: `http://localhost:8000/accounts/google/login/callback/`
6. Guarda el **Client ID** y **Client Secret**

### 2. Configurar en Django Admin

1. Inicia sesión en el admin: `http://localhost:8000/admin/`
2. Ve a **Sites** > **example.com** y cámbialo:
   - Domain name: `localhost:8000`
   - Display name: `OIKOS Local`
   - Guardar

3. Ve a **Social applications** > **Add social application**
4. Configura:
   - Provider: Google
   - Name: Google OAuth
   - Client id: (el que obtuviste de Google)
   - Secret key: (el que obtuviste de Google)
   - Sites: Selecciona `localhost:8000`
   - Guardar

### 3. Reiniciar el servidor

```bash
python manage.py runserver
```

Ahora el botón "Ingresar con Google" debería funcionar correctamente.

## Solución Temporal

Mientras tanto, puedes usar el login tradicional en:
- `http://localhost:8000/login/` (usuarios admin)

O deshabilitar temporalmente el botón de Google editando el template.
