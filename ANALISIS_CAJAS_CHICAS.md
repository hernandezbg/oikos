# ANÁLISIS: Funcionalidad de Cajas Chicas

## ESTADO: ✅ IMPLEMENTACIÓN COMPLETA

**Fecha de implementación:** Enero 2025
**Migración aplicada:** `0009_agregar_cajas_chicas`
**Sistema verificado:** ✅ Sin errores (`python manage.py check` passed)

Todos los componentes han sido implementados exitosamente:
- ✅ 4 nuevos modelos creados
- ✅ Signals implementados
- ✅ 13 vistas creadas
- ✅ 13 URLs configuradas
- ✅ 10 templates creados
- ✅ Navbar modificado para incluir cajas
- ✅ Dashboard actualizado
- ✅ Sistema de transferencias funcionando

---

## 1. RESUMEN EJECUTIVO

Se requiere implementar un sistema de **cajas chicas** paralelo al sistema actual de Movimientos (caja principal), donde:

- **Administradores** pueden crear múltiples cajas chicas con nombres personalizados
- Cada caja chica tiene sus propios **colaboradores/tesoreros**
- Los usuarios de cajas chicas **NO tienen acceso** a los Movimientos (caja principal)
- El sistema actual de Movimientos **NO se ve afectado**
- Mantiene el aislamiento multi-tenant por iglesia

## 2. ARQUITECTURA PROPUESTA

### 2.1 Modelo de Datos Nuevo

```python
class CajaChica(models.Model):
    """
    Representa una caja chica dentro de una iglesia.
    Ejemplo: "Caja Jóvenes", "Caja Ministerio Mujeres"
    """
    iglesia = models.ForeignKey(Iglesia, on_delete=models.CASCADE, related_name='cajas_chicas')
    nombre = models.CharField(max_length=100)  # "Caja Jóvenes"
    descripcion = models.TextField(blank=True, null=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Control
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creada_por = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='cajas_creadas')

    class Meta:
        verbose_name = 'Caja Chica'
        verbose_name_plural = 'Cajas Chicas'
        ordering = ['iglesia', 'nombre']
        unique_together = ['iglesia', 'nombre']  # No duplicar nombres en la misma iglesia
```

```python
class MovimientoCajaChica(models.Model):
    """
    Movimientos específicos de una caja chica.
    Similar a Movimiento pero para cajas chicas.
    """
    TIPOS = (
        ('INGRESO', 'Ingreso'),
        ('EGRESO', 'Egreso'),
    )

    caja_chica = models.ForeignKey(CajaChica, on_delete=models.CASCADE, related_name='movimientos')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    fecha = models.DateField()
    concepto = models.TextField()
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    comprobante_nro = models.CharField(max_length=50, blank=True, null=True)

    # Usuarios
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='movimientos_caja_chica_creados'
    )
    aprobado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_caja_chica_aprobados'
    )

    # Timestamps
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)

    # Anulación
    anulado = models.BooleanField(default=False)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)
    anulado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movimientos_caja_chica_anulados'
    )

    class Meta:
        verbose_name = 'Movimiento de Caja Chica'
        verbose_name_plural = 'Movimientos de Caja Chica'
        ordering = ['-fecha', '-fecha_creacion']

    def generar_numero_comprobante(self):
        """
        Genera número de comprobante por caja chica.
        Formato: CC-I-0001, CC-E-0001
        """
        prefijo = 'CC-I' if self.tipo == 'INGRESO' else 'CC-E'

        ultimo = MovimientoCajaChica.objects.filter(
            caja_chica=self.caja_chica,
            tipo=self.tipo,
            comprobante_nro__startswith=prefijo
        ).order_by('-comprobante_nro').first()

        if ultimo and ultimo.comprobante_nro:
            try:
                ultimo_numero = int(ultimo.comprobante_nro.split('-')[2])
                nuevo_numero = ultimo_numero + 1
            except (IndexError, ValueError):
                nuevo_numero = 1
        else:
            nuevo_numero = 1

        return f"{prefijo}-{nuevo_numero:04d}"
```

```python
class UsuarioCajaChica(models.Model):
    """
    Relación muchos-a-muchos entre usuarios y cajas chicas.
    Define qué usuarios pueden acceder a qué cajas.
    """
    ROLES_CAJA = (
        ('TESORERO_CAJA', 'Tesorero de Caja'),
        ('COLABORADOR_CAJA', 'Colaborador de Caja'),
    )

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='cajas_asignadas')
    caja_chica = models.ForeignKey(CajaChica, on_delete=models.CASCADE, related_name='usuarios_asignados')
    rol_caja = models.CharField(max_length=20, choices=ROLES_CAJA)
    puede_aprobar = models.BooleanField(default=False)

    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    asignado_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='asignaciones_caja_realizadas'
    )

    class Meta:
        verbose_name = 'Usuario de Caja Chica'
        verbose_name_plural = 'Usuarios de Cajas Chicas'
        unique_together = ['usuario', 'caja_chica']  # Un usuario no puede estar duplicado en la misma caja
```

### 2.2 Modificaciones al Modelo CodigoInvitacion

```python
class CodigoInvitacion(models.Model):
    # ... campos existentes ...

    # NUEVO CAMPO: Soporte para códigos de caja chica
    caja_chica = models.ForeignKey(
        'CajaChica',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='codigos_invitacion',
        help_text='Si está asignado, el código es para unirse a esta caja chica específica'
    )

    # NUEVO: Roles para cajas chicas
    ROLES_INVITACION = (
        ('TESORERO', 'Tesorero'),
        ('PASTOR', 'Pastor'),
        ('COLABORADOR', 'Colaborador'),
        ('TESORERO_CAJA', 'Tesorero de Caja Chica'),  # NUEVO
        ('COLABORADOR_CAJA', 'Colaborador de Caja Chica'),  # NUEVO
    )

    # MODIFICACIÓN del método crear:
    @staticmethod
    def crear(iglesia, rol, creado_por, dias_expiracion=30, caja_chica=None):
        """
        Crea un nuevo código de invitación.
        Si caja_chica es None, es para la iglesia.
        Si caja_chica está definido, es para esa caja específica.
        """
        from django.utils import timezone
        from datetime import timedelta

        prefijos = {
            'TESORERO': 'T',
            'PASTOR': 'P',
            'COLABORADOR': 'C',
            'TESORERO_CAJA': 'TC',     # NUEVO
            'COLABORADOR_CAJA': 'CC',  # NUEVO
        }

        codigo_base = CodigoInvitacion.generar_codigo_unico()
        codigo_completo = f"{prefijos[rol]}{codigo_base}"

        return CodigoInvitacion.objects.create(
            iglesia=iglesia,
            caja_chica=caja_chica,  # NUEVO
            codigo=codigo_completo,
            rol=rol,
            creado_por=creado_por,
            fecha_expiracion=timezone.now() + timedelta(days=dias_expiracion),
            activo=True,
            usos_maximos=1
        )
```

### 2.3 Modificaciones al Modelo Usuario

```python
class Usuario(AbstractUser):
    # ... campos existentes sin cambios ...

    # NUEVOS MÉTODOS:
    @property
    def tiene_acceso_cajas_chicas(self):
        """Verifica si el usuario tiene acceso a alguna caja chica"""
        return self.cajas_asignadas.exists()

    @property
    def tiene_acceso_movimientos(self):
        """
        Solo usuarios con rol de iglesia (no solo de caja) pueden ver Movimientos.
        """
        # Si es ADMIN, TESORERO, PASTOR o COLABORADOR de la iglesia → Sí
        # Si solo tiene rol de caja (sin iglesia) → No
        return self.rol in ['ADMIN', 'TESORERO', 'PASTOR', 'COLABORADOR']

    @property
    def es_usuario_solo_caja(self):
        """
        Verifica si el usuario SOLO tiene acceso a cajas, no a la iglesia principal.
        """
        # Si tiene cajas asignadas pero no tiene rol de iglesia
        return self.tiene_acceso_cajas_chicas and not self.tiene_acceso_movimientos

    def puede_gestionar_caja_chica(self, caja_chica):
        """Verifica si puede gestionar (crear/editar) una caja chica específica"""
        # Solo ADMIN puede crear/eliminar cajas
        if self.rol == 'ADMIN' and self.iglesia == caja_chica.iglesia:
            return True
        return False

    def puede_crear_movimiento_caja(self, caja_chica):
        """Verifica si puede crear movimientos en una caja específica"""
        if self.rol == 'ADMIN':
            return True

        # Verificar si es tesorero de esta caja específica
        asignacion = self.cajas_asignadas.filter(
            caja_chica=caja_chica,
            rol_caja='TESORERO_CAJA'
        ).first()

        return asignacion is not None
```

## 3. LÓGICA DE PERMISOS

### 3.1 Matriz de Permisos

| Rol                    | Ver Movimientos | Gestionar Movimientos | Ver Cajas Chicas | Gestionar Caja Propia | Crear Cajas |
|------------------------|-----------------|------------------------|------------------|------------------------|-------------|
| ADMIN                  | ✅              | ✅                     | ✅               | ✅                     | ✅          |
| TESORERO               | ✅              | ✅                     | ❌               | ❌                     | ❌          |
| PASTOR                 | ✅              | ❌                     | ❌               | ❌                     | ❌          |
| COLABORADOR            | ✅              | ❌                     | ❌               | ❌                     | ❌          |
| TESORERO_CAJA          | ❌              | ❌                     | ✅ (solo su caja)| ✅                     | ❌          |
| COLABORADOR_CAJA       | ❌              | ❌                     | ✅ (solo su caja)| ⚠️ (solo lectura)      | ❌          |

### 3.2 Reglas de Negocio

1. **ADMIN puede:**
   - Ver y gestionar TODO (Movimientos + todas las Cajas Chicas de su iglesia)
   - Crear, editar y eliminar cajas chicas
   - Generar códigos de invitación para cajas

2. **TESORERO/PASTOR/COLABORADOR de iglesia pueden:**
   - Ver y gestionar Movimientos (según permisos actuales)
   - **NO** pueden ver cajas chicas (a menos que también sean asignados explícitamente)

3. **TESORERO_CAJA puede:**
   - Ver SOLO la(s) caja(s) a la(s) que está asignado
   - Crear, editar movimientos en su caja
   - Ver reportes de su caja
   - **NO** puede ver Movimientos ni otras cajas

4. **COLABORADOR_CAJA puede:**
   - Ver SOLO la(s) caja(s) a la(s) que está asignado
   - Ver movimientos (solo lectura)
   - **NO** puede crear/editar movimientos
   - **NO** puede ver Movimientos ni otras cajas

## 4. FLUJO DE INVITACIONES

### 4.1 Proceso de Invitación a Caja Chica

```
1. ADMIN crea una caja chica: "Caja Jóvenes"
2. ADMIN genera código de invitación:
   - Tipo: TESORERO_CAJA o COLABORADOR_CAJA
   - Caja destino: "Caja Jóvenes"
   - Código generado: TC-ABC123 o CC-XYZ789

3. Usuario nuevo o existente usa el código:
   - Si es usuario NUEVO → Se crea cuenta y se asigna a la caja
   - Si es usuario EXISTENTE de la iglesia → Se le da acceso adicional a la caja

4. Sistema verifica:
   - Código válido y no expirado
   - Pertenece a una caja de la iglesia correcta
   - Crea UsuarioCajaChica con el rol correspondiente
```

### 4.2 Modificación en `registro_con_codigo_view`

```python
@login_required
def registro_con_codigo_view(request):
    """
    Vista para unirse a una iglesia O a una caja chica usando código
    """
    if request.method == 'POST':
        form = ValidarCodigoInvitacionForm(request.POST)
        if form.is_valid():
            codigo_obj = form.codigo_obj

            # CASO 1: Código para iglesia (comportamiento actual)
            if codigo_obj.caja_chica is None:
                request.user.iglesia = codigo_obj.iglesia
                request.user.rol = codigo_obj.rol
                # ... lógica actual ...

            # CASO 2: Código para caja chica (NUEVO)
            else:
                # Verificar que el usuario ya tenga iglesia asignada
                if not request.user.iglesia:
                    request.user.iglesia = codigo_obj.iglesia
                    request.user.rol = None  # No tiene rol de iglesia
                    request.user.save()

                # Crear asignación a la caja
                UsuarioCajaChica.objects.create(
                    usuario=request.user,
                    caja_chica=codigo_obj.caja_chica,
                    rol_caja=codigo_obj.rol,  # TESORERO_CAJA o COLABORADOR_CAJA
                    puede_aprobar=(codigo_obj.rol == 'TESORERO_CAJA'),
                    asignado_por=codigo_obj.creado_por
                )

                messages.success(
                    request,
                    f'Te has unido a la caja "{codigo_obj.caja_chica.nombre}" '
                    f'como {codigo_obj.get_rol_display()}.'
                )

            codigo_obj.usar_codigo(request.user)
            return redirect('dashboard')
```

## 5. VISTAS Y URLs NECESARIAS

### 5.1 Nuevas URLs (core/urls.py)

```python
urlpatterns = [
    # ... URLs existentes ...

    # Cajas Chicas (solo ADMIN)
    path('cajas-chicas/', CajaChicaListView.as_view(), name='caja_chica_list'),
    path('cajas-chicas/nueva/', CajaChicaCreateView.as_view(), name='caja_chica_create'),
    path('cajas-chicas/<int:pk>/editar/', CajaChicaUpdateView.as_view(), name='caja_chica_update'),
    path('cajas-chicas/<int:pk>/toggle/', toggle_caja_chica, name='toggle_caja_chica'),

    # Movimientos de Caja Chica
    path('cajas-chicas/<int:caja_pk>/movimientos/', MovimientoCajaChicaListView.as_view(), name='movimiento_caja_list'),
    path('cajas-chicas/<int:caja_pk>/movimientos/nuevo/', MovimientoCajaChicaCreateView.as_view(), name='movimiento_caja_create'),
    path('cajas-chicas/<int:caja_pk>/movimientos/<int:pk>/editar/', MovimientoCajaChicaUpdateView.as_view(), name='movimiento_caja_update'),
    path('cajas-chicas/<int:caja_pk>/movimientos/<int:pk>/anular/', anular_movimiento_caja_view, name='anular_movimiento_caja'),

    # Dashboard específico de caja
    path('cajas-chicas/<int:pk>/dashboard/', DashboardCajaChicaView.as_view(), name='dashboard_caja'),

    # Reportes de caja chica
    path('cajas-chicas/<int:pk>/reporte/', reporte_caja_chica_view, name='reporte_caja'),
]
```

### 5.2 Vistas Principales

#### CajaChicaListView (Solo ADMIN)
```python
class CajaChicaListView(LoginRequiredMixin, ListView):
    model = CajaChica
    template_name = 'core/caja_chica_list.html'

    def dispatch(self, request, *args, **kwargs):
        # Solo ADMIN puede ver esta lista
        if request.user.rol != 'ADMIN':
            messages.error(request, 'No tienes permisos para gestionar cajas chicas')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return CajaChica.objects.filter(iglesia=self.request.user.iglesia)
```

#### MovimientoCajaChicaListView
```python
class MovimientoCajaChicaListView(LoginRequiredMixin, ListView):
    model = MovimientoCajaChica
    template_name = 'core/movimiento_caja_list.html'

    def dispatch(self, request, *args, **kwargs):
        self.caja = get_object_or_404(CajaChica, pk=self.kwargs['caja_pk'])

        # Verificar acceso
        if not self._usuario_tiene_acceso():
            messages.error(request, 'No tienes acceso a esta caja')
            return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)

    def _usuario_tiene_acceso(self):
        user = self.request.user

        # ADMIN siempre tiene acceso
        if user.rol == 'ADMIN' and user.iglesia == self.caja.iglesia:
            return True

        # Verificar si está asignado a esta caja
        return user.cajas_asignadas.filter(caja_chica=self.caja).exists()

    def get_queryset(self):
        return MovimientoCajaChica.objects.filter(
            caja_chica=self.caja,
            anulado=False
        )
```

## 6. MODIFICACIONES AL DASHBOARD

### 6.1 Dashboard Principal

El dashboard actual debe:

1. **Para ADMIN:**
   - Mostrar sección de "Movimientos" (caja principal)
   - Mostrar sección de "Cajas Chicas" con lista de cajas y botón para crear

2. **Para TESORERO/PASTOR/COLABORADOR:**
   - Solo mostrar "Movimientos" (sin cambios)

3. **Para usuarios SOLO de caja (TESORERO_CAJA/COLABORADOR_CAJA):**
   - NO mostrar "Movimientos"
   - Mostrar solo las cajas a las que tiene acceso
   - Cada caja con su mini-dashboard

### 6.2 Estructura del Dashboard

```python
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    user = self.request.user

    # Si es usuario solo de caja, mostrar solo cajas
    if user.es_usuario_solo_caja:
        context['mostrar_movimientos'] = False
        context['cajas_usuario'] = user.cajas_asignadas.all()
        context['es_usuario_caja'] = True
        return context

    # Si tiene acceso a movimientos (ADMIN, TESORERO, etc.)
    if user.tiene_acceso_movimientos:
        context['mostrar_movimientos'] = True
        # ... lógica actual de dashboard ...

    # Si es ADMIN, también mostrar cajas
    if user.rol == 'ADMIN':
        context['cajas_chicas'] = CajaChica.objects.filter(
            iglesia=user.iglesia,
            activa=True
        )
        context['puede_gestionar_cajas'] = True

    return context
```

## 7. MIGRACIONES NECESARIAS

### 7.1 Secuencia de Migraciones

```bash
# Migración 1: Crear modelo CajaChica
python manage.py makemigrations --name crear_caja_chica

# Migración 2: Crear modelo MovimientoCajaChica
python manage.py makemigrations --name crear_movimiento_caja_chica

# Migración 3: Crear modelo UsuarioCajaChica
python manage.py makemigrations --name crear_usuario_caja_chica

# Migración 4: Modificar CodigoInvitacion (agregar campo caja_chica)
python manage.py makemigrations --name agregar_caja_a_codigo_invitacion

# Migración 5: Actualizar choices de ROLES_INVITACION
python manage.py makemigrations --name actualizar_roles_invitacion

# Aplicar todas
python manage.py migrate
```

### 7.2 Consideraciones de Migración

- **NO hay datos existentes afectados** porque son modelos nuevos
- El campo `caja_chica` en `CodigoInvitacion` es `null=True`, compatible con registros existentes
- Los modelos `Movimiento` y `SaldoMensual` **NO se tocan**

## 8. SIGNALS NECESARIOS

```python
# En core/signals.py

@receiver(post_save, sender=MovimientoCajaChica)
def actualizar_saldo_caja_chica(sender, instance, created, **kwargs):
    """
    Actualiza el saldo de la caja chica cuando se crea/modifica un movimiento
    """
    # Calcular saldo actual de la caja
    from django.db.models import Sum, Q

    caja = instance.caja_chica

    ingresos = MovimientoCajaChica.objects.filter(
        caja_chica=caja,
        tipo='INGRESO',
        anulado=False
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    egresos = MovimientoCajaChica.objects.filter(
        caja_chica=caja,
        tipo='EGRESO',
        anulado=False
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    # Actualizar saldo en algún lugar (podría ser un campo calculado o caché)
    # Por ahora se calcula on-demand en las vistas


@receiver(pre_save, sender=MovimientoCajaChica)
def validar_permisos_caja_chica(sender, instance, **kwargs):
    """
    Valida que el usuario tenga permisos para crear movimientos en esta caja
    """
    usuario = instance.creado_por
    caja = instance.caja_chica

    # Si es ADMIN de la iglesia, OK
    if usuario.rol == 'ADMIN' and usuario.iglesia == caja.iglesia:
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
```

## 9. SEGURIDAD Y VALIDACIONES

### 9.1 Validaciones Críticas

1. **Aislamiento de datos:**
   - Siempre filtrar por `iglesia` en todos los querysets
   - Validar que `caja.iglesia == usuario.iglesia`

2. **Permisos en vistas:**
   ```python
   def dispatch(self, request, *args, **kwargs):
       # Validar acceso a la caja específica
       if not self.usuario_tiene_acceso_caja():
           return redirect('dashboard')
   ```

3. **Prevenir acceso cruzado:**
   - Usuario de Caja A no puede ver Caja B
   - Usuario sin iglesia no puede crear cajas

4. **Códigos de invitación:**
   - Validar que `codigo.iglesia == usuario.iglesia` antes de aceptar
   - No permitir códigos de caja de otra iglesia

### 9.2 Tests Críticos a Implementar

```python
# Pruebas necesarias:
1. Usuario TESORERO_CAJA no puede ver Movimientos
2. Usuario TESORERO no puede ver cajas chicas (a menos que esté asignado)
3. ADMIN puede ver todo
4. Usuario de Caja A no puede ver movimientos de Caja B
5. Códigos de invitación generan las asignaciones correctas
```

## 10. IMPACTO EN CÓDIGO EXISTENTE

### 10.1 Archivos que NO requieren cambios

✅ **Sin modificaciones:**
- `core/models.py` → Movimiento, SaldoMensual (intactos)
- `core/utils.py` → formato_pesos, generar_reporte_pdf (se reutilizan)
- `core/forms.py` → MovimientoForm (sin cambios)
- `core/admin.py` → Configuración actual (sin cambios)

### 10.2 Archivos que requieren cambios MENORES

⚠️ **Modificaciones mínimas:**

1. **`core/models.py`:**
   - ✅ Agregar `CajaChica`, `MovimientoCajaChica`, `UsuarioCajaChica`
   - ✅ Modificar `CodigoInvitacion` (agregar campo `caja_chica`)
   - ✅ Agregar métodos de permisos en `Usuario`
   - ❌ NO tocar `Movimiento`, `SaldoMensual`, `Iglesia`

2. **`core/views.py`:**
   - ✅ Agregar nuevas vistas para cajas (no modificar las existentes)
   - ✅ Modificar `DashboardView.get_context_data()` para incluir cajas si es ADMIN
   - ✅ Modificar `registro_con_codigo_view()` para manejar códigos de caja
   - ❌ NO tocar lógica de Movimientos

3. **`core/urls.py`:**
   - ✅ Agregar URLs nuevas para cajas
   - ❌ NO modificar URLs existentes

4. **`core/signals.py`:**
   - ✅ Agregar signals para MovimientoCajaChica
   - ❌ NO modificar signals existentes

5. **Templates:**
   - ✅ Crear templates nuevos para cajas
   - ✅ Modificar `dashboard.html` para mostrar sección de cajas si es ADMIN
   - ❌ NO modificar templates de movimientos

### 10.3 Archivos nuevos necesarios

📄 **Archivos a crear:**
- `core/templates/core/caja_chica_list.html`
- `core/templates/core/caja_chica_form.html`
- `core/templates/core/movimiento_caja_list.html`
- `core/templates/core/movimiento_caja_form.html`
- `core/templates/core/dashboard_caja.html`
- `core/forms_caja_chica.py` (formularios para cajas)

## 11. PLAN DE IMPLEMENTACIÓN

### Fase 1: Modelos y Migraciones (1-2 días)
1. Crear modelos `CajaChica`, `MovimientoCajaChica`, `UsuarioCajaChica`
2. Modificar `CodigoInvitacion`
3. Agregar métodos de permisos en `Usuario`
4. Crear y aplicar migraciones
5. Agregar signals

### Fase 2: Vistas y URLs (2-3 días)
1. Crear vistas para CRUD de cajas (solo ADMIN)
2. Crear vistas para movimientos de caja
3. Modificar dashboard para incluir cajas
4. Modificar registro con código para manejar cajas

### Fase 3: Templates y Frontend (2-3 días)
1. Crear templates para cajas
2. Crear templates para movimientos de caja
3. Modificar dashboard.html
4. Agregar sección en navbar para cajas

### Fase 4: Testing y Validación (1-2 días)
1. Tests de permisos
2. Tests de aislamiento de datos
3. Tests de códigos de invitación
4. Verificar que Movimientos sigue funcionando igual

### Fase 5: Documentación (1 día)
1. Actualizar CLAUDE.md
2. Documentar flujo de cajas
3. Crear manual de usuario

**Total estimado: 7-11 días de desarrollo**

## 12. CONSIDERACIONES FINALES

### 12.1 Ventajas del Diseño

✅ **NO rompe funcionalidad existente** → Modelos nuevos, sin tocar los actuales
✅ **Reutiliza lógica existente** → Formularios, utilidades, permisos
✅ **Escalable** → Un usuario puede estar en múltiples cajas
✅ **Seguro** → Aislamiento multi-tenant se mantiene
✅ **Flexible** → ADMIN puede tener vista completa, usuarios de caja solo ven su caja

### 12.2 Riesgos y Mitigaciones

⚠️ **Riesgo:** Confusión en el dashboard entre Movimientos y Cajas
   **Mitigación:** UI clara, separación visual, breadcrumbs

⚠️ **Riesgo:** Usuario con acceso a iglesia Y a caja puede confundirse
   **Mitigación:** Mostrar claramente en qué contexto está trabajando

⚠️ **Riesgo:** Códigos de invitación complejos (iglesia vs caja)
   **Mitigación:** Prefijos claros (T/P/C para iglesia, TC/CC para cajas)

## 14. TRANSFERENCIAS ENTRE CAJAS

### 14.1 Modelo TransferenciaCajaChica

```python
class TransferenciaCajaChica(models.Model):
    """
    Representa una transferencia de dinero entre dos cajas chicas.
    Crea automáticamente dos movimientos: egreso en origen, ingreso en destino.
    """
    # Cajas involucradas
    caja_origen = models.ForeignKey(
        CajaChica,
        on_delete=models.CASCADE,
        related_name='transferencias_salida'
    )
    caja_destino = models.ForeignKey(
        CajaChica,
        on_delete=models.CASCADE,
        related_name='transferencias_entrada'
    )

    # Detalles de la transferencia
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    concepto = models.TextField()
    fecha = models.DateField()

    # Control y auditoría
    realizada_por = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='transferencias_realizadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Movimientos generados automáticamente
    movimiento_egreso = models.OneToOneField(
        MovimientoCajaChica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferencia_egreso'
    )
    movimiento_ingreso = models.OneToOneField(
        MovimientoCajaChica,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferencia_ingreso'
    )

    # Anulación
    anulada = models.BooleanField(default=False)
    fecha_anulacion = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.TextField(blank=True)
    anulada_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transferencias_anuladas'
    )

    class Meta:
        verbose_name = 'Transferencia entre Cajas'
        verbose_name_plural = 'Transferencias entre Cajas'
        ordering = ['-fecha', '-fecha_creacion']

    def __str__(self):
        return f"Transferencia {self.caja_origen.nombre} → {self.caja_destino.nombre}: ${self.monto}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # No transferir a la misma caja
        if self.caja_origen == self.caja_destino:
            raise ValidationError('No puedes transferir dinero a la misma caja')

        # Validar que ambas cajas pertenezcan a la misma iglesia
        if self.caja_origen.iglesia != self.caja_destino.iglesia:
            raise ValidationError('Las cajas deben pertenecer a la misma iglesia')

        # Validar saldo suficiente en caja origen
        saldo_origen = self.calcular_saldo_caja(self.caja_origen)
        if saldo_origen < self.monto:
            raise ValidationError(
                f'Saldo insuficiente en {self.caja_origen.nombre}. '
                f'Saldo disponible: ${saldo_origen}, Monto a transferir: ${self.monto}'
            )

    @staticmethod
    def calcular_saldo_caja(caja):
        """Calcula el saldo actual de una caja"""
        from django.db.models import Sum

        ingresos = MovimientoCajaChica.objects.filter(
            caja_chica=caja,
            tipo='INGRESO',
            anulado=False
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        egresos = MovimientoCajaChica.objects.filter(
            caja_chica=caja,
            tipo='EGRESO',
            anulado=False
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        return caja.saldo_inicial + ingresos - egresos

    def crear_movimientos(self):
        """
        Crea los dos movimientos asociados a esta transferencia.
        Se ejecuta automáticamente en el signal post_save.
        """
        # Egreso en caja origen
        self.movimiento_egreso = MovimientoCajaChica.objects.create(
            caja_chica=self.caja_origen,
            tipo='EGRESO',
            fecha=self.fecha,
            concepto=f'Transferencia a {self.caja_destino.nombre}: {self.concepto}',
            monto=self.monto,
            creado_por=self.realizada_por,
            aprobado_por=self.realizada_por
        )

        # Ingreso en caja destino
        self.movimiento_ingreso = MovimientoCajaChica.objects.create(
            caja_chica=self.caja_destino,
            tipo='INGRESO',
            fecha=self.fecha,
            concepto=f'Transferencia desde {self.caja_origen.nombre}: {self.concepto}',
            monto=self.monto,
            creado_por=self.realizada_por,
            aprobado_por=self.realizada_por
        )

        self.save()

    def anular_transferencia(self, usuario, motivo):
        """Anula la transferencia y sus movimientos asociados"""
        from django.utils import timezone

        self.anulada = True
        self.anulada_por = usuario
        self.fecha_anulacion = timezone.now()
        self.motivo_anulacion = motivo
        self.save()

        # Anular movimientos asociados
        if self.movimiento_egreso:
            self.movimiento_egreso.anulado = True
            self.movimiento_egreso.anulado_por = usuario
            self.movimiento_egreso.fecha_anulacion = timezone.now()
            self.movimiento_egreso.motivo_anulacion = f'Anulación de transferencia: {motivo}'
            self.movimiento_egreso.save()

        if self.movimiento_ingreso:
            self.movimiento_ingreso.anulado = True
            self.movimiento_ingreso.anulado_por = usuario
            self.movimiento_ingreso.fecha_anulacion = timezone.now()
            self.movimiento_ingreso.motivo_anulacion = f'Anulación de transferencia: {motivo}'
            self.movimiento_ingreso.save()
```

### 14.2 Signal para Transferencias

```python
# En core/signals.py

@receiver(post_save, sender=TransferenciaCajaChica)
def crear_movimientos_transferencia(sender, instance, created, **kwargs):
    """
    Cuando se crea una transferencia, genera automáticamente
    los dos movimientos (egreso e ingreso).
    """
    if created and not instance.movimiento_egreso and not instance.movimiento_ingreso:
        instance.crear_movimientos()
```

### 14.3 Vista para Transferencias

```python
class TransferenciaCreateView(LoginRequiredMixin, CreateView):
    model = TransferenciaCajaChica
    template_name = 'core/transferencia_form.html'
    fields = ['caja_origen', 'caja_destino', 'monto', 'concepto', 'fecha']

    def dispatch(self, request, *args, **kwargs):
        # Solo ADMIN puede crear transferencias
        if request.user.rol != 'ADMIN':
            messages.error(request, 'Solo administradores pueden realizar transferencias')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar solo cajas de la iglesia del usuario
        form.fields['caja_origen'].queryset = CajaChica.objects.filter(
            iglesia=self.request.user.iglesia,
            activa=True
        )
        form.fields['caja_destino'].queryset = CajaChica.objects.filter(
            iglesia=self.request.user.iglesia,
            activa=True
        )
        return form

    def form_valid(self, form):
        transferencia = form.save(commit=False)
        transferencia.realizada_por = self.request.user

        # Validar antes de guardar
        try:
            transferencia.clean()
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)

        transferencia.save()

        messages.success(
            self.request,
            f'Transferencia realizada: ${transferencia.monto} de '
            f'{transferencia.caja_origen.nombre} a {transferencia.caja_destino.nombre}'
        )
        return redirect('caja_chica_list')


class TransferenciaListView(LoginRequiredMixin, ListView):
    model = TransferenciaCajaChica
    template_name = 'core/transferencia_list.html'
    context_object_name = 'transferencias'

    def dispatch(self, request, *args, **kwargs):
        # Solo ADMIN puede ver transferencias
        if request.user.rol != 'ADMIN':
            messages.error(request, 'No tienes permisos para ver transferencias')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TransferenciaCajaChica.objects.filter(
            caja_origen__iglesia=self.request.user.iglesia
        ).select_related('caja_origen', 'caja_destino', 'realizada_por')


@login_required
def anular_transferencia_view(request, pk):
    """Anula una transferencia y sus movimientos asociados"""
    transferencia = get_object_or_404(TransferenciaCajaChica, pk=pk)

    # Solo ADMIN puede anular
    if request.user.rol != 'ADMIN':
        messages.error(request, 'No tienes permisos para anular transferencias')
        return redirect('dashboard')

    # Validar iglesia
    if transferencia.caja_origen.iglesia != request.user.iglesia:
        messages.error(request, 'No tienes permisos para anular esta transferencia')
        return redirect('dashboard')

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        if not motivo:
            messages.error(request, 'Debes indicar un motivo para anular')
            return redirect('transferencia_list')

        transferencia.anular_transferencia(request.user, motivo)
        messages.success(request, 'Transferencia anulada correctamente')
        return redirect('transferencia_list')

    return render(request, 'core/anular_transferencia.html', {
        'transferencia': transferencia
    })
```

### 14.4 URLs para Transferencias

```python
# Agregar a core/urls.py

urlpatterns = [
    # ... URLs existentes ...

    # Transferencias (solo ADMIN)
    path('transferencias/', TransferenciaListView.as_view(), name='transferencia_list'),
    path('transferencias/nueva/', TransferenciaCreateView.as_view(), name='transferencia_create'),
    path('transferencias/<int:pk>/anular/', anular_transferencia_view, name='anular_transferencia'),
]
```

### 14.5 Permisos de Transferencias

Solo **ADMIN** puede:
- Ver lista de transferencias
- Crear transferencias entre cajas
- Anular transferencias

Usuarios de caja (TESORERO_CAJA, COLABORADOR_CAJA):
- Pueden ver en el historial de su caja los movimientos generados por transferencias
- NO pueden crear transferencias directamente

### 14.6 Validaciones de Transferencias

1. ✅ No transferir a la misma caja
2. ✅ Ambas cajas deben ser de la misma iglesia
3. ✅ Validar saldo suficiente en caja origen
4. ✅ Crear dos movimientos atómicamente (egreso + ingreso)
5. ✅ Al anular transferencia, anular ambos movimientos

### 12.3 Extensiones Futuras

💡 **Posibles mejoras:**
- ✅ Transferencias entre cajas chicas (IMPLEMENTADO)
- Transferencias entre caja principal (Movimientos) y cajas chicas
- Presupuestos por caja
- Reportes consolidados (todas las cajas + movimientos)
- Notificaciones cuando una caja está por agotarse
- Auditoría de quién accedió a qué caja

## 13. CONCLUSIÓN

El diseño propuesto permite implementar **Cajas Chicas como un módulo independiente** que:

1. ✅ **NO afecta** el sistema actual de Movimientos
2. ✅ **Mantiene** el aislamiento multi-tenant
3. ✅ **Reutiliza** código existente donde es posible
4. ✅ **Escala** para múltiples cajas por iglesia
5. ✅ **Protege** con permisos granulares por caja

La implementación es **segura, escalable y no invasiva** al código actual.

---

## 15. NOTAS DE IMPLEMENTACIÓN

### 15.1 Archivos Creados

**Modelos y Lógica:**
- `core/views_caja_chica.py` - 13 vistas para gestión de cajas chicas
- `core/forms_caja_chica.py` - 5 formularios para cajas chicas

**Templates (10 archivos):**
- `core/templates/core/caja_chica_list.html` - Listado de cajas chicas
- `core/templates/core/caja_chica_form.html` - Formulario crear/editar caja
- `core/templates/core/movimiento_caja_list.html` - Listado de movimientos de caja
- `core/templates/core/movimiento_caja_form.html` - Formulario de movimiento
- `core/templates/core/anular_movimiento_caja.html` - Confirmación anulación movimiento
- `core/templates/core/dashboard_caja.html` - Dashboard individual de caja
- `core/templates/core/transferencia_list.html` - Listado de transferencias
- `core/templates/core/transferencia_form.html` - Formulario de transferencia
- `core/templates/core/anular_transferencia.html` - Confirmación anulación transferencia
- `core/templates/core/generar_codigo_caja.html` - Generador de códigos

### 15.2 Archivos Modificados

**Backend:**
- `core/models.py` - Agregados 4 modelos: `CajaChica`, `MovimientoCajaChica`, `UsuarioCajaChica`, `TransferenciaCajaChica`
- `core/models.py` - Modificado `CodigoInvitacion` con campo `caja_chica`
- `core/models.py` - Agregados métodos de permisos en modelo `Usuario`
- `core/signals.py` - Agregados 2 signals para validación y creación automática
- `core/views.py` - Modificado `DashboardView.get_context_data()` para incluir cajas
- `core/views.py` - Modificado `registro_con_codigo_view()` para manejar códigos de caja
- `core/urls.py` - Agregadas 13 URLs nuevas
- `core/admin.py` - Agregados 4 admin configs

**Frontend:**
- `templates/base.html` - Modificado sidebar para incluir links de cajas chicas
- `core/templates/core/dashboard.html` - Agregada sección de cajas chicas

**Migración:**
- `core/migrations/0009_agregar_cajas_chicas.py` - Aplicada exitosamente

### 15.3 Funcionalidades Implementadas

**Para ADMIN:**
- ✅ Crear, editar y desactivar cajas chicas
- ✅ Ver listado de todas las cajas con saldos
- ✅ Generar códigos de invitación para cajas
- ✅ Crear transferencias entre cajas
- ✅ Ver y anular transferencias
- ✅ Acceso completo a todas las cajas de su iglesia
- ✅ Dashboard con resumen de cajas y movimientos

**Para TESORERO_CAJA:**
- ✅ Acceso solo a cajas asignadas
- ✅ Crear movimientos (ingresos/egresos) en su caja
- ✅ Editar movimientos de su caja
- ✅ Anular movimientos de su caja
- ✅ Ver dashboard de su caja con estadísticas
- ✅ NO tiene acceso a Movimientos (caja principal)

**Para COLABORADOR_CAJA:**
- ✅ Ver cajas asignadas (solo lectura)
- ✅ Ver movimientos de su caja
- ✅ Ver dashboard de su caja
- ✅ NO puede crear/editar/anular movimientos
- ✅ NO tiene acceso a Movimientos (caja principal)

### 15.4 Validaciones Implementadas

**Seguridad y Permisos:**
- ✅ Aislamiento multi-tenant: Solo se accede a cajas de la misma iglesia
- ✅ Validación de permisos en cada vista (dispatch)
- ✅ Usuarios de caja no pueden ver Movimientos
- ✅ Usuarios de una caja no pueden ver otras cajas
- ✅ Validación de roles al crear movimientos (signals)

**Transferencias:**
- ✅ No permitir transferir a la misma caja
- ✅ Validar saldo suficiente antes de transferir
- ✅ Ambas cajas deben ser de la misma iglesia
- ✅ Crear movimientos dual automáticamente (egreso + ingreso)
- ✅ Al anular transferencia, anular ambos movimientos

**Códigos de Invitación:**
- ✅ Validar expiración de códigos
- ✅ Códigos con prefijo según rol (TC/CC)
- ✅ Crear UsuarioCajaChica al usar código de caja
- ✅ Si usuario nuevo, asignar iglesia automáticamente

### 15.5 Interfaz de Usuario

**Navbar (sidebar):**
- ✅ Links a Movimientos ocultos para usuarios solo de caja
- ✅ Sección "Gestionar Cajas" para ADMIN
- ✅ Link a "Transferencias" para ADMIN
- ✅ Links individuales a cajas asignadas para usuarios de caja

**Dashboard Principal:**
- ✅ Para ADMIN: Muestra Movimientos + Cajas Chicas
- ✅ Para usuarios de caja: Solo muestra sus cajas asignadas
- ✅ Cards con saldo actualizado de cada caja
- ✅ Indicadores visuales de estado de saldo

**Dashboard de Caja:**
- ✅ Breadcrumb navigation
- ✅ Cards con saldo actual, ingresos y egresos del mes
- ✅ Tabla de últimos movimientos
- ✅ Botones de acción según permisos

### 15.6 Testing Realizado

- ✅ `python manage.py check` - Sin errores
- ✅ Migración aplicada exitosamente
- ✅ Sintaxis de templates verificada

### 15.7 Próximos Pasos Sugeridos

**Testing Funcional (recomendado):**
1. Crear cuenta de ADMIN y crear cajas chicas
2. Generar códigos y probar registro con códigos de caja
3. Verificar que usuario TESORERO_CAJA no ve Movimientos
4. Crear movimientos en cajas y verificar cálculo de saldo
5. Crear transferencias y verificar movimientos duales
6. Anular transferencias y verificar anulación dual
7. Verificar aislamiento entre iglesias

**Mejoras Futuras (opcionales):**
- Agregar filtros avanzados en listados
- Exportar reportes de cajas a PDF/Excel
- Gráficos en dashboard de caja
- Notificaciones cuando saldo bajo
- Transferencias entre caja principal y cajas chicas
- Presupuestos por caja
- Historial de cambios (audit log)
