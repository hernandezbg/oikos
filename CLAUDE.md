# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OIKOS is a multi-tenant financial management system designed for churches. It provides isolated data per church (multi-tenancy at database level), role-based access control (ADMIN, TESORERO, PASTOR, COLABORADOR), and comprehensive financial tracking with PDF reports.

**Tech Stack**: Django 5.0.1, PostgreSQL, Redis, Bootstrap 5, Chart.js, ReportLab
**Deployment**: Railway (with WhiteNoise for static files)

## Essential Commands

### Development Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Setup initial data (creates admin/admin user and sample church data)
python manage.py setup_inicial

# Run development server
python manage.py runserver
```

### Database Operations

```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser (if not using setup_inicial)
python manage.py createsuperuser

# Collect static files (required before deployment)
python manage.py collectstatic --noinput
```

### Testing

There is no test suite configured. When adding tests, use Django's testing framework:

```bash
python manage.py test core
python manage.py test core.tests.TestMovimiento  # Run specific test
```

## Architecture

### Multi-Tenancy Model

The system uses **row-level multi-tenancy** where all data is filtered by `iglesia` (church):

- Every user belongs to one `Iglesia` (via `Usuario.iglesia` ForeignKey)
- All financial models (`Movimiento`, `CategoriaIngreso`, `CategoriaEgreso`, `SaldoMensual`) are linked to an `Iglesia`
- **CRITICAL**: All queries must filter by `request.user.iglesia` to maintain data isolation
- Signals in `core/signals.py:validar_permisos_iglesia` enforce that users can only create/modify data for their own church

### Key Models (core/models.py)

**Main Church Models:**
- **Iglesia**: Church entity - the core tenant model
- **Usuario**: Custom user model extending AbstractUser with `iglesia`, `rol` (ADMIN/TESORERO/PASTOR/COLABORADOR), and permission properties
- **CodigoInvitacion**: Invitation codes for users to join churches OR specific cash boxes (format: T4K8M9 for church, TC/CC for boxes)
- **CategoriaIngreso/CategoriaEgreso**: Income/expense categories (church-specific)
- **Movimiento**: Financial transactions with automatic receipt number generation (I-0001, E-0001) - main church cash register
- **SaldoMensual**: Monthly balance summaries (automatically updated via signals)

**Petty Cash Box Models (Cajas Chicas):**
- **CajaChica**: Individual cash box (e.g., "Caja Jóvenes", "Caja Mujeres") with saldo_inicial and activa status
- **MovimientoCajaChica**: Transactions within a specific cash box (separate from main Movimiento)
- **UsuarioCajaChica**: Many-to-many relationship between users and boxes with roles (TESORERO_CAJA, COLABORADOR_CAJA)
- **TransferenciaCajaChica**: Transfers between cash boxes - automatically creates dual movements (egreso + ingreso)

### Permission System

Users have role-based permissions defined as `@property` methods in `Usuario` model:

**Main Church Permissions:**
- `puede_gestionar_usuarios`: Only ADMIN
- `puede_crear_movimientos`: ADMIN and TESORERO
- `puede_anular_movimientos`: ADMIN and TESORERO with `puede_aprobar=True`
- `puede_eliminar_movimientos`: Only ADMIN
- `puede_generar_reportes`: ADMIN, TESORERO, and PASTOR

**Cash Box Permissions:**
- `tiene_acceso_cajas_chicas`: User has access to at least one cash box
- `tiene_acceso_movimientos`: User can access main church Movimientos (roles: ADMIN, TESORERO, PASTOR, COLABORADOR)
- `es_usuario_solo_caja`: User ONLY has access to cash boxes, not main church Movimientos
- `puede_gestionar_caja_chica(caja)`: Only ADMIN can create/edit/delete cash boxes
- `puede_crear_movimiento_caja(caja)`: ADMIN or TESORERO_CAJA of that specific box

**Always check these properties in views**, not just `user.rol`.

### Signals (core/signals.py)

**Main Church Signals:**
- `post_save(Movimiento)` → Updates `SaldoMensual` automatically via `calcular_saldo_mes()`
- `post_save(Iglesia)` → Creates default categories (ofrendas, diezmos, alquiler, etc.)
- `pre_save(Movimiento)` → Validates that user can only create movements for their own church

**Cash Box Signals:**
- `pre_save(MovimientoCajaChica)` → Validates that user has permissions to create movements in that box
- `post_save(TransferenciaCajaChica)` → Automatically creates dual movements (egreso in origin + ingreso in destination)

### Authentication

Supports two authentication methods:

1. **Traditional**: Username/password with manual church registration
2. **Google OAuth**: Via `social-auth-app-django` with custom pipeline (`core/pipeline.py:assign_iglesia`) that redirects to church registration if user has no church assigned

After Google login without church, users see `seleccionar_tipo_registro` view to either:
- Create a new church (becomes ADMIN)
- Join existing church via invitation code

### Core Utilities (core/utils.py)

- `formato_pesos(monto)`: Formats numbers as Argentine pesos ($1.234.567,89)
- `formato_mes(fecha, corto=False)`: Returns month names in Spanish (Enero 2025, Ene 2025)
- `calcular_saldo_mes(iglesia, año_mes)`: Recalculates monthly balance based on all movements
- `generar_reporte_pdf(iglesia, año_mes)`: Generates PDF reports with ReportLab
- `get_dashboard_data(iglesia)`: Aggregates data for dashboard charts

### Automatic Receipt Numbers

`Movimiento.generar_numero_comprobante()` generates sequential receipt numbers:
- Ingresos: I-0001, I-0002, ...
- Egresos: E-0001, E-0002, ...

**Important**: Numbers are per-church, per-type. Called automatically in `Movimiento.save()` if `comprobante_nro` is empty.

**Cash Boxes**: `MovimientoCajaChica.generar_numero_comprobante()` generates per-box receipt numbers:
- Format: CC-I-0001, CC-E-0001
- Separate numbering per box

## Cajas Chicas (Petty Cash Boxes)

### Overview

The Cajas Chicas system runs **parallel to the main church Movimientos** system. It allows ADMIN users to create multiple cash boxes with independent balances, movements, and users.

**Key Features:**
- ADMIN creates named cash boxes (e.g., "Caja Jóvenes", "Caja Ministerio Mujeres")
- Each box has its own users with box-specific roles (TESORERO_CAJA, COLABORADOR_CAJA)
- Users assigned ONLY to boxes do NOT have access to main church Movimientos
- ADMIN has full access to both main Movimientos and all boxes
- Transfers between boxes create atomic dual movements

### Architecture

**Separation of Concerns:**
- Main church finances → `Movimiento` model
- Cash box finances → `MovimientoCajaChica` model
- Completely independent data models
- No cross-contamination of permissions or data

**Files:**
- `core/views_caja_chica.py` - 13 views for cash box management
- `core/forms_caja_chica.py` - 5 forms for cash boxes
- 10 templates in `core/templates/core/` for cash box UI

### User Roles in Cash Boxes

**TESORERO_CAJA (Box Treasurer):**
- Create, edit, and annul movements in assigned box
- View box dashboard with statistics
- NO access to main Movimientos
- Cannot create transfers (only ADMIN)

**COLABORADOR_CAJA (Box Collaborator):**
- View assigned box (read-only)
- View movements and dashboard
- Cannot create/edit/annul movements
- NO access to main Movimientos

**ADMIN:**
- Full access to all boxes in their church
- Create, edit, deactivate boxes
- Generate invitation codes for boxes
- Create transfers between boxes
- View and annul transfers
- Access to both Movimientos and all boxes

### Invitation Codes for Boxes

Codes are generated with specific prefixes:
- **TC-XXXXXX**: TESORERO_CAJA (box treasurer)
- **CC-XXXXXX**: COLABORADOR_CAJA (box collaborator)

When a user uses a box invitation code:
1. If user has no `iglesia`, they are assigned to the box's church
2. A `UsuarioCajaChica` record is created linking user to box
3. User gets no church-level role (unless they also use a church code)

### Transfers Between Boxes

`TransferenciaCajaChica` model handles transfers:
1. ADMIN creates transfer with origin, destination, amount, and concept
2. System validates:
   - Origin ≠ destination
   - Both boxes belong to same church
   - Sufficient balance in origin box
3. Signal automatically creates two movements:
   - Egreso in origin box: "Transferencia a [destino]: [concepto]"
   - Ingreso in destination box: "Transferencia desde [origen]: [concepto]"
4. Movements are linked to transfer via OneToOne fields
5. Annulling transfer also annuls both movements

### Important Patterns for Cash Boxes

**Filtering by box access:**
```python
# Check if user has access to a specific box
if user.rol == 'ADMIN' and user.iglesia == caja.iglesia:
    # ADMIN has access
    pass
elif user.cajas_asignadas.filter(caja_chica=caja).exists():
    # User is assigned to this box
    pass
else:
    # No access
    return redirect('dashboard')
```

**Creating cash box movements:**
```python
movimiento = form.save(commit=False)
movimiento.caja_chica = caja
movimiento.creado_por = request.user
# Signal validates permissions automatically
movimiento.save()
```

**Calculating box balance:**
```python
saldo_actual = caja.calcular_saldo_actual()
# Returns: saldo_inicial + sum(ingresos) - sum(egresos) where anulado=False
```

### UI Navigation

**Sidebar (base.html):**
- Main Movimientos section hidden if `user.es_usuario_solo_caja`
- "Gestionar Cajas" link for ADMIN
- "Transferencias" link for ADMIN
- Individual box links for users with box assignments

**Dashboard:**
- ADMIN sees both Movimientos and Cajas Chicas sections
- Box-only users see only their assigned boxes
- Each box card shows current balance with color-coded status

### Environment Configuration

Uses `django-environ` for settings. Key environment variables:

- `DATABASE_URL`: PostgreSQL connection (auto-set by Railway)
- `SECRET_KEY`: Django secret key
- `DEBUG`: Boolean, default=True
- `ALLOWED_HOSTS`: Comma-separated list
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`: For OAuth
- `APP_NAME`: Displayed in templates (default: OIKOS)

**Fallback**: If no `DATABASE_URL`, uses SQLite3 at `db.sqlite3`

## Important Patterns

### Filtering by Church

Always filter querysets by user's church:

```python
# Correct
movimientos = Movimiento.objects.filter(iglesia=request.user.iglesia)

# Wrong - exposes data from all churches
movimientos = Movimiento.objects.all()
```

### Creating Movements

Always set the `iglesia` and `creado_por` fields:

```python
movimiento = form.save(commit=False)
movimiento.iglesia = request.user.iglesia
movimiento.creado_por = request.user
movimiento.save()
```

### Permission Checks in Views

```python
if not request.user.puede_crear_movimientos:
    messages.error(request, 'No tienes permisos para crear movimientos')
    return redirect('dashboard')
```

### Category Validation

Movements must have the correct category type:
- INGRESO movements require `categoria_ingreso` (not `categoria_egreso`)
- EGRESO movements require `categoria_egreso` (not `categoria_ingreso`)

This is enforced in `Movimiento.clean()`.

## Deployment

### Railway Configuration

- **Procfile**: Runs migrations, collectstatic, and gunicorn
- **railway.json**: Configures nixpacks builder, healthcheck at `/admin/`, and restart policy
- **Static files**: Served by WhiteNoise (no S3/CDN needed)
- **Database**: PostgreSQL service connected via `DATABASE_URL`
- **CSRF**: `CSRF_TRUSTED_ORIGINS` includes Railway domains

### Pre-deployment Checklist

1. Set `DEBUG=False` in production
2. Configure `SECRET_KEY` (never use default)
3. Set `ALLOWED_HOSTS` to actual domain
4. Verify `DATABASE_URL` is set
5. Run `python manage.py collectstatic` (done automatically by Procfile)

## Common Tasks

### Adding a New Role

1. Add role to `Usuario.ROLES` tuple in `core/models.py`
2. Add permission properties to `Usuario` model as needed
3. Update views to check new permissions
4. Add role to `CodigoInvitacion.ROLES_INVITACION` if users should be able to invite this role

### Adding a New Category Type

1. Add to default categories in `core/signals.py:crear_categorias_default`
2. Categories are created automatically when a new `Iglesia` is saved

### Generating Reports

Reports are generated in `core/utils.py:generar_reporte_pdf()` using ReportLab. The view is in `core/views.py:reporte_mensual_view()`. PDFs include:
- Church header info
- Monthly summary (ingresos, egresos, saldo)
- Detailed movement list
- OIKOS logo

### Localization

System is configured for Argentine Spanish:
- `LANGUAGE_CODE = 'es-ar'`
- `TIME_ZONE = 'America/Argentina/Buenos_Aires'`
- Month names use custom `MESES_ES` constants in `utils.py`
- Currency formatting uses Argentine peso format ($1.234.567,89)

## File Organization

```
oikos/
├── oikos/              # Project settings
│   ├── settings.py     # Django config with environ
│   ├── urls.py         # Root URL routing
│   └── wsgi.py         # WSGI entry point
├── core/               # Main application
│   ├── models.py       # All data models (church + cash boxes)
│   ├── views.py        # Main church views
│   ├── views_caja_chica.py # Cash box views (13 views)
│   ├── forms.py        # Main church forms
│   ├── forms_caja_chica.py # Cash box forms (5 forms)
│   ├── forms_google.py # Google OAuth registration forms
│   ├── forms_invitacion.py # Invitation code forms
│   ├── urls.py         # Core URL patterns (includes 13 cash box URLs)
│   ├── admin.py        # Django admin configuration
│   ├── signals.py      # Model signals for automation
│   ├── pipeline.py     # Social auth custom pipeline
│   ├── utils.py        # Utilities (format, PDF, calculations)
│   ├── templates/core/ # HTML templates (includes 10 cash box templates)
│   └── management/commands/
│       └── setup_inicial.py  # Initial data setup command
├── static/             # CSS, JS, images (collected to staticfiles/)
├── templates/          # Base templates (base.html with cash box navbar)
├── requirements.txt    # Python dependencies
├── Procfile            # Railway deployment config
├── railway.json        # Railway build/deploy settings
├── CLAUDE.md           # This file - project documentation
└── ANALISIS_CAJAS_CHICAS.md # Cash boxes implementation analysis
```

## Notes for Future Development

- The system has Google OAuth configured but requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to be set
- Invitation code system (`CodigoInvitacion`) allows ADMIN users to generate time-limited codes for new users to join their church OR specific cash boxes
- Monthly balances (`SaldoMensual`) are recalculated on every movement save - consider optimization for high-volume churches
- There is a "Contadora de Billetes" (bill counter) feature for counting physical cash
- All permissions are role-based; there is no object-level permission system
- Admin interface allows superusers to manage all churches; regular users cannot access `/admin/`
- **Cajas Chicas (NEW)**: Fully implemented petty cash box system with transfers, see `ANALISIS_CAJAS_CHICAS.md` for details
- Cash boxes run completely parallel to main Movimientos - no interference between systems
- Future enhancements: Transfers between main cash and boxes, box budgets, consolidated reports
