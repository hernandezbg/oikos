# Configuración de Google OAuth para OIKOS

Este documento explica cómo configurar Google OAuth para permitir que los usuarios ingresen con su cuenta de Google.

## Pasos para obtener las credenciales de Google

### 1. Acceder a Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Inicia sesión con tu cuenta de Google
3. Crea un nuevo proyecto o selecciona uno existente

### 2. Habilitar la API de Google+

1. En el menú lateral, ve a **APIs y servicios** > **Biblioteca**
2. Busca "Google+ API" o "Google Identity"
3. Haz clic en **Habilitar**

### 3. Configurar la pantalla de consentimiento OAuth

1. Ve a **APIs y servicios** > **Pantalla de consentimiento de OAuth**
2. Selecciona **Externo** (para usuarios fuera de tu organización) o **Interno**
3. Completa la información requerida:
   - **Nombre de la aplicación**: OIKOS
   - **Correo del usuario de asistencia**: tu email
   - **Dominios autorizados**: tu dominio (ej: `oikos.up.railway.app`)
   - **Información del desarrollador**: tu email
4. Haz clic en **Guardar y continuar**
5. En **Ámbitos**, agrega los siguientes scopes:
   - `../auth/userinfo.email`
   - `../auth/userinfo.profile`
6. Haz clic en **Guardar y continuar**

### 4. Crear credenciales OAuth 2.0

1. Ve a **APIs y servicios** > **Credenciales**
2. Haz clic en **Crear credenciales** > **ID de cliente de OAuth 2.0**
3. Selecciona **Aplicación web**
4. Configura lo siguiente:
   - **Nombre**: OIKOS Web Client
   - **Orígenes de JavaScript autorizados**:
     - `http://localhost:8000` (para desarrollo)
     - `https://tu-dominio.up.railway.app` (para producción)
   - **URI de redireccionamiento autorizados**:
     - `http://localhost:8000/accounts/google/login/callback/` (desarrollo)
     - `https://tu-dominio.up.railway.app/accounts/google/login/callback/` (producción)
5. Haz clic en **Crear**
6. **Guarda el Client ID y Client Secret** que aparecen

### 5. Configurar las variables de entorno

Agrega las siguientes variables a tu archivo `.env`:

```bash
GOOGLE_CLIENT_ID=tu-client-id-aqui.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret-aqui
```

### 6. Configurar el Social App en Django Admin (Desarrollo)

Para desarrollo local, necesitas configurar la aplicación social en el admin de Django:

1. Inicia el servidor: `python manage.py runserver`
2. Accede al admin: `http://localhost:8000/admin/`
3. Ve a **Sites** > **example.com** y edítalo:
   - **Domain name**: `localhost:8000`
   - **Display name**: `OIKOS Local`
4. Ve a **Social applications** > **Add social application**
5. Configura:
   - **Provider**: Google
   - **Name**: Google OAuth
   - **Client id**: tu Client ID de Google
   - **Secret key**: tu Client Secret de Google
   - **Sites**: Selecciona `localhost:8000` (o el site que creaste)
6. Haz clic en **Save**

### 7. Configurar para producción en Railway

En Railway, agrega las variables de entorno:

1. Ve a tu proyecto en Railway
2. Haz clic en **Variables**
3. Agrega:
   ```
   GOOGLE_CLIENT_ID=tu-client-id-aqui.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=tu-client-secret-aqui
   ```

Luego, en el admin de producción:

1. Accede a `https://tu-dominio.up.railway.app/admin/`
2. Ve a **Sites** y edita el site:
   - **Domain name**: `tu-dominio.up.railway.app`
   - **Display name**: `OIKOS`
3. Ve a **Social applications** y crea una nueva:
   - **Provider**: Google
   - **Name**: Google OAuth
   - **Client id**: tu Client ID
   - **Secret key**: tu Client Secret
   - **Sites**: Selecciona tu dominio

## Flujo de autenticación

1. El usuario hace clic en "Ingresar con Google" en la página de login
2. Es redirigido a Google para autenticarse
3. Después de autenticarse, Google redirige de vuelta a la aplicación
4. Si es la primera vez:
   - Se crea un nuevo usuario con los datos de Google (email, nombre, apellido)
   - El usuario es redirigido a `/registro-iglesia/` para registrar su iglesia
   - Se le asigna el rol de TESORERO
5. Si ya tiene iglesia:
   - Es redirigido directamente al dashboard

## Permisos

- **Administradores de Django**: Pueden usar login tradicional (usuario/contraseña)
- **Usuarios regulares**: Deben usar Google OAuth
- **Tesoreros**: Se crean automáticamente al registrar una iglesia con Google

## Solución de problemas

### Error: "redirect_uri_mismatch"

Verifica que las URIs de redirección en Google Cloud Console coincidan exactamente con:
- `http://localhost:8000/accounts/google/login/callback/` (desarrollo)
- `https://tu-dominio.up.railway.app/accounts/google/login/callback/` (producción)

### Error: "Social application not found"

Asegúrate de haber configurado la Social Application en el admin de Django.

### El usuario no puede acceder al dashboard

Verifica que el usuario haya completado el registro de la iglesia en `/registro-iglesia/`.

## Seguridad

- Nunca compartas tus credenciales de Google (Client ID y Secret)
- Usa variables de entorno para almacenar las credenciales
- No subas el archivo `.env` a Git
- En producción, asegúrate de usar HTTPS

## Referencias

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Django-allauth Documentation](https://django-allauth.readthedocs.io/)
- [Django-allauth Google Provider](https://django-allauth.readthedocs.io/en/latest/providers.html#google)
