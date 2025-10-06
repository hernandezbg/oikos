# OIKOS - Sistema de Gestión Financiera para Iglesias

Sistema multi-iglesia para gestión financiera optimizado para deployment en Railway.

## Características

- 💰 Sistema multi-iglesia (cada iglesia ve solo sus datos)
- 📊 Dashboard con métricas financieras y gráficos interactivos
- ✅ CRUD completo de ingresos/egresos con categorías
- 📄 Reportes mensuales automáticos en PDF
- 🔐 Login requerido en todas las vistas
- 📱 Diseño responsive con Bootstrap 5
- 🐘 PostgreSQL y Redis en Railway

## Tecnologías

- Django 5.0.1
- PostgreSQL (via Railway)
- Bootstrap 5
- Chart.js
- WhiteNoise
- ReportLab

## Instalación Local

### 1. Clonar el repositorio

```bash
git clone <tu-repo>
cd oikos
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copiar `.env.example` a `.env` y configurar:

```bash
cp .env.example .env
```

Editar `.env` con tus credenciales de Railway:

```
SECRET_KEY=tu-secret-key
DEBUG=True
DATABASE_URL=postgresql://user:password@host:port/database
REDIS_URL=redis://localhost:6379
APP_NAME=OIKOS
```

### 4. Ejecutar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Cargar datos iniciales

```bash
python manage.py setup_inicial
```

Esto creará:
- Usuario admin (usuario: `admin`, contraseña: `admin`)
- Iglesia de ejemplo
- Categorías por defecto
- Movimientos de ejemplo (últimos 3 meses)

### 6. Ejecutar servidor de desarrollo

```bash
python manage.py runserver
```

Acceder a:
- **Sistema**: http://localhost:8000
- **Admin**: http://localhost:8000/admin/

## Deployment en Railway

### Opción 1: Deploy desde GitHub

1. Pushear código a GitHub
2. Conectar repositorio en Railway
3. Railway detectará automáticamente Django
4. Agregar servicio PostgreSQL
5. Configurar variables de entorno en Railway:
   - `SECRET_KEY`
   - `DATABASE_URL` (auto-configurada)
   - `APP_NAME=OIKOS`
   - `ALLOWED_HOSTS` con tu dominio

### Opción 2: Railway CLI

```bash
railway login
railway init
railway add postgresql
railway up
```

## Estructura del Proyecto

```
oikos/
├── oikos/              # Configuración del proyecto
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/               # App principal
│   ├── models.py       # Modelos (Iglesia, Usuario, Movimiento, etc.)
│   ├── views.py        # Vistas (Dashboard, CRUD, Reportes)
│   ├── forms.py        # Formularios
│   ├── admin.py        # Configuración del admin
│   ├── urls.py
│   ├── utils.py        # Utilidades (formato_pesos, PDFs, etc.)
│   ├── signals.py      # Señales para automatización
│   ├── templates/      # Templates HTML
│   └── templatetags/   # Filtros personalizados
├── static/             # CSS, JS, imágenes
├── templates/          # Templates base
├── requirements.txt
├── Procfile           # Para Railway
├── railway.json       # Configuración Railway
└── .env.example       # Ejemplo de variables de entorno
```

## Modelos

- **Iglesia**: Información de la iglesia
- **Usuario**: Usuarios del sistema (extends AbstractUser)
- **CategoriaIngreso**: Categorías de ingresos
- **CategoriaEgreso**: Categorías de egresos
- **Movimiento**: Ingresos y egresos
- **SaldoMensual**: Resumen mensual automático

## Funcionalidades Principales

### Dashboard
- Saldo actual con alertas
- Total de ingresos/egresos del mes
- Gráfico de evolución de saldos (6 meses)
- Gráfico de distribución de gastos
- Últimos 5 movimientos

### Movimientos
- Crear ingreso/egreso con categoría
- Filtrar por mes, tipo, categoría
- Búsqueda por concepto
- Exportar a Excel
- Validación de montos > $1.000.000

### Reportes
- PDF mensual con resumen
- Detalle de todos los movimientos
- Logo OIKOS en header

### Admin
- Gestión completa de iglesias
- Administración de usuarios por iglesia
- Configuración de categorías
- Visualización de saldos mensuales

## Credenciales por Defecto

Después de ejecutar `setup_inicial`:

- **Usuario**: admin
- **Contraseña**: admin

⚠️ **IMPORTANTE**: Cambiar estas credenciales en producción.

## Comandos Útiles

```bash
# Crear superusuario
python manage.py createsuperuser

# Ejecutar setup inicial
python manage.py setup_inicial

# Colectar archivos estáticos
python manage.py collectstatic

# Hacer backup de la base de datos
python manage.py dumpdata > backup.json
```

## Licencia

Este proyecto ha sido creado para uso educativo y de gestión eclesiástica.

---

**OIKOS** © 2025 - Sistema de Gestión Financiera
