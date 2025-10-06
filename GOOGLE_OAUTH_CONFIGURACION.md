# Configuración de Google OAuth para OIKOS

## URI de Redirección Correcta

Para que funcione el login con Google, necesitas configurar la **URI de redirección** exacta en Google Cloud Console.

### La URI de redirección debe ser:

**Para desarrollo local:**
```
http://localhost:8000/oauth/complete/google-oauth2/
```

**Para producción:**
```
https://tu-dominio.up.railway.app/oauth/complete/google-oauth2/
```

## Pasos para configurar en Google Cloud Console:

### 1. Acceder a Google Cloud Console

1. Ve a https://console.cloud.google.com/
2. Selecciona tu proyecto o crea uno nuevo

### 2. Habilitar Google+ API

1. Ve a **APIs y servicios** > **Biblioteca**
2. Busca "Google+ API"
3. Haz clic en **Habilitar**

### 3. Configurar pantalla de consentimiento OAuth

1. Ve a **APIs y servicios** > **Pantalla de consentimiento de OAuth**
2. Selecciona **Externo**
3. Completa:
   - **Nombre de la aplicación**: OIKOS
   - **Correo del usuario de asistencia**: tu email
   - **Dominios autorizados**: `localhost` (para desarrollo)
4. Ámbitos: No es necesario agregar ninguno adicional
5. Guardar y continuar

### 4. Crear credenciales OAuth 2.0

1. Ve a **APIs y servicios** > **Credenciales**
2. Haz clic en **Crear credenciales** > **ID de cliente de OAuth 2.0**
3. Tipo de aplicación: **Aplicación web**
4. Nombre: **OIKOS Web Client**
5. **Orígenes de JavaScript autorizados**:
   ```
   http://localhost:8000
   ```

6. **URIs de redirección autorizadas** (¡MUY IMPORTANTE!):
   ```
   http://localhost:8000/oauth/complete/google-oauth2/
   ```

7. Haz clic en **Crear**
8. **Copia el Client ID y Client Secret**

### 5. Configurar en tu aplicación

Agrega al archivo `.env`:

```bash
GOOGLE_CLIENT_ID=tu-client-id-aqui.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret-aqui
```

### 6. Reiniciar el servidor

```bash
python manage.py runserver
```

## Verificación

1. Ve a `http://localhost:8000/login/`
2. Haz clic en "Ingresar con Google"
3. Deberías ser redirigido a Google para autenticarte
4. Después de autenticarte, serás redirigido de vuelta a tu aplicación

## Solución de problemas

### Error: redirect_uri_mismatch

**Problema**: La URI de redirección no coincide

**Solución**: Verifica que en Google Cloud Console, la URI de redirección sea EXACTAMENTE:
```
http://localhost:8000/oauth/complete/google-oauth2/
```

Nota: NO debe tener barra al final después de `oauth2`

### Error: invalid_client

**Problema**: Las credenciales no son correctas

**Solución**: Verifica que `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` en `.env` sean correctos

### El botón no hace nada

**Problema**: Puede que el servidor no esté corriendo o las credenciales estén vacías

**Solución**:
1. Verifica que el servidor esté corriendo: `python manage.py runserver`
2. Verifica que el archivo `.env` tenga las credenciales de Google

## Producción (Railway)

Para producción, necesitas:

1. Agregar la URI de producción en Google Cloud Console:
   ```
   https://tu-app.up.railway.app/oauth/complete/google-oauth2/
   ```

2. Agregar las variables de entorno en Railway:
   ```
   GOOGLE_CLIENT_ID=tu-client-id
   GOOGLE_CLIENT_SECRET=tu-client-secret
   ```

3. Agregar el dominio en "Orígenes de JavaScript autorizados":
   ```
   https://tu-app.up.railway.app
   ```
