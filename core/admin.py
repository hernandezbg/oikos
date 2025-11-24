from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from core.models import (
    Iglesia, Usuario, CategoriaIngreso, CategoriaEgreso,
    Movimiento, SaldoMensual,
    CajaChica, MovimientoCajaChica, UsuarioCajaChica, TransferenciaCajaChica
)
from core.utils import formato_pesos


class CategoriasIngresoInline(admin.TabularInline):
    model = CategoriaIngreso
    extra = 1
    fields = ('codigo', 'nombre', 'activa')


class CategoriasEgresoInline(admin.TabularInline):
    model = CategoriaEgreso
    extra = 1
    fields = ('codigo', 'nombre', 'presupuesto_mensual', 'activa')


@admin.register(Iglesia)
class IglesiaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'localidad', 'provincia', 'celular', 'email', 'activa', 'fecha_creacion')
    list_filter = ('activa', 'provincia', 'fecha_creacion')
    search_fields = ('nombre', 'localidad', 'provincia', 'email')
    inlines = [CategoriasIngresoInline, CategoriasEgresoInline]
    readonly_fields = ('fecha_creacion',)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'email', 'get_full_name', 'iglesia', 'rol', 'puede_aprobar', 'terminos_aceptados', 'is_active')
    list_filter = ('iglesia', 'rol', 'puede_aprobar', 'terminos_aceptados', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = UserAdmin.fieldsets + (
        ('Información de Iglesia', {
            'fields': ('iglesia', 'celular', 'rol', 'puede_aprobar')
        }),
        ('Términos y Condiciones', {
            'fields': ('terminos_aceptados', 'fecha_aceptacion_terminos'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información de Iglesia', {
            'fields': ('iglesia', 'celular', 'rol', 'puede_aprobar')
        }),
    )

    readonly_fields = UserAdmin.readonly_fields + ('fecha_aceptacion_terminos',)


@admin.register(CategoriaIngreso)
class CategoriaIngresoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'iglesia', 'activa')
    list_filter = ('iglesia', 'activa')
    search_fields = ('codigo', 'nombre')
    ordering = ('iglesia', 'codigo')


@admin.register(CategoriaEgreso)
class CategoriaEgresoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'iglesia', 'presupuesto_formateado', 'activa')
    list_filter = ('iglesia', 'activa')
    search_fields = ('codigo', 'nombre')
    ordering = ('iglesia', 'codigo')

    def presupuesto_formateado(self, obj):
        if obj.presupuesto_mensual:
            return formato_pesos(obj.presupuesto_mensual)
        return '-'
    presupuesto_formateado.short_description = 'Presupuesto Mensual'


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = (
        'fecha', 'tipo', 'iglesia', 'get_categoria', 'concepto_corto',
        'monto_formateado', 'comprobante_nro', 'creado_por'
    )
    list_filter = ('tipo', 'iglesia', 'fecha', 'creado_por')
    search_fields = ('concepto', 'comprobante_nro')
    date_hierarchy = 'fecha'
    readonly_fields = ('fecha_creacion', 'fecha_aprobacion')
    ordering = ('-fecha', '-fecha_creacion')

    fieldsets = (
        ('Información Básica', {
            'fields': ('iglesia', 'tipo', 'fecha')
        }),
        ('Categoría', {
            'fields': ('categoria_ingreso', 'categoria_egreso')
        }),
        ('Detalles', {
            'fields': ('concepto', 'monto', 'comprobante_nro')
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'aprobado_por', 'fecha_aprobacion')
        }),
    )

    def get_categoria(self, obj):
        return obj.categoria_ingreso or obj.categoria_egreso
    get_categoria.short_description = 'Categoría'

    def concepto_corto(self, obj):
        return obj.concepto[:50] + '...' if len(obj.concepto) > 50 else obj.concepto
    concepto_corto.short_description = 'Concepto'

    def monto_formateado(self, obj):
        return formato_pesos(obj.monto)
    monto_formateado.short_description = 'Monto'


@admin.register(SaldoMensual)
class SaldoMensualAdmin(admin.ModelAdmin):
    list_display = (
        'iglesia', 'año_mes', 'saldo_inicial_formateado',
        'total_ingresos_formateado', 'total_egresos_formateado',
        'saldo_final_formateado', 'fecha_actualizacion'
    )
    list_filter = ('iglesia', 'año_mes')
    search_fields = ('iglesia__nombre', 'año_mes')
    readonly_fields = ('fecha_actualizacion',)
    ordering = ('-año_mes', 'iglesia')

    def saldo_inicial_formateado(self, obj):
        return formato_pesos(obj.saldo_inicial)
    saldo_inicial_formateado.short_description = 'Saldo Inicial'

    def total_ingresos_formateado(self, obj):
        return formato_pesos(obj.total_ingresos)
    total_ingresos_formateado.short_description = 'Total Ingresos'

    def total_egresos_formateado(self, obj):
        return formato_pesos(obj.total_egresos)
    total_egresos_formateado.short_description = 'Total Egresos'

    def saldo_final_formateado(self, obj):
        return formato_pesos(obj.saldo_final)
    saldo_final_formateado.short_description = 'Saldo Final'


# ============================================
# ADMIN PARA CAJAS CHICAS
# ============================================

@admin.register(CajaChica)
class CajaChicaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'iglesia', 'saldo_inicial_formateado', 'activa', 'creada_por', 'fecha_creacion')
    list_filter = ('iglesia', 'activa', 'fecha_creacion')
    search_fields = ('nombre', 'iglesia__nombre', 'descripcion')
    readonly_fields = ('fecha_creacion', 'creada_por')

    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'iglesia', 'descripcion', 'saldo_inicial')
        }),
        ('Estado', {
            'fields': ('activa',)
        }),
        ('Auditoría', {
            'fields': ('creada_por', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )

    def saldo_inicial_formateado(self, obj):
        return formato_pesos(obj.saldo_inicial)
    saldo_inicial_formateado.short_description = 'Saldo Inicial'


class UsuarioCajaChicaInline(admin.TabularInline):
    model = UsuarioCajaChica
    extra = 0
    fields = ('usuario', 'rol_caja', 'puede_aprobar', 'fecha_asignacion')
    readonly_fields = ('fecha_asignacion',)


@admin.register(MovimientoCajaChica)
class MovimientoCajaChicaAdmin(admin.ModelAdmin):
    list_display = (
        'comprobante_nro', 'caja_chica', 'tipo', 'fecha',
        'concepto_corto', 'monto_formateado', 'creado_por', 'anulado'
    )
    list_filter = ('caja_chica__iglesia', 'caja_chica', 'tipo', 'anulado', 'fecha')
    search_fields = ('concepto', 'comprobante_nro', 'caja_chica__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_aprobacion', 'fecha_anulacion', 'comprobante_nro')
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('caja_chica', 'tipo', 'fecha', 'concepto', 'monto', 'comprobante_nro')
        }),
        ('Anulación', {
            'fields': ('anulado', 'motivo_anulacion', 'anulado_por', 'fecha_anulacion'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'fecha_creacion', 'aprobado_por', 'fecha_aprobacion'),
            'classes': ('collapse',)
        }),
    )

    def concepto_corto(self, obj):
        return obj.concepto[:50] + '...' if len(obj.concepto) > 50 else obj.concepto
    concepto_corto.short_description = 'Concepto'

    def monto_formateado(self, obj):
        return formato_pesos(obj.monto)
    monto_formateado.short_description = 'Monto'


@admin.register(UsuarioCajaChica)
class UsuarioCajaChicaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'caja_chica', 'rol_caja', 'puede_aprobar', 'asignado_por', 'fecha_asignacion')
    list_filter = ('caja_chica__iglesia', 'caja_chica', 'rol_caja', 'puede_aprobar')
    search_fields = ('usuario__username', 'usuario__email', 'caja_chica__nombre')
    readonly_fields = ('fecha_asignacion',)


@admin.register(TransferenciaCajaChica)
class TransferenciaCajaChicaAdmin(admin.ModelAdmin):
    list_display = (
        'fecha', 'caja_origen', 'caja_destino', 'monto_formateado',
        'realizada_por', 'anulada', 'fecha_creacion'
    )
    list_filter = ('caja_origen__iglesia', 'anulada', 'fecha')
    search_fields = ('concepto', 'caja_origen__nombre', 'caja_destino__nombre')
    readonly_fields = ('fecha_creacion', 'fecha_anulacion', 'movimiento_egreso', 'movimiento_ingreso')
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Información de Transferencia', {
            'fields': ('caja_origen', 'caja_destino', 'monto', 'concepto', 'fecha')
        }),
        ('Movimientos Generados', {
            'fields': ('movimiento_egreso', 'movimiento_ingreso'),
            'classes': ('collapse',)
        }),
        ('Anulación', {
            'fields': ('anulada', 'motivo_anulacion', 'anulada_por', 'fecha_anulacion'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('realizada_por', 'fecha_creacion'),
            'classes': ('collapse',)
        }),
    )

    def monto_formateado(self, obj):
        return formato_pesos(obj.monto)
    monto_formateado.short_description = 'Monto'


# Personalizar el sitio admin
admin.site.site_header = "OIKOS - Administración"
admin.site.site_title = "OIKOS Admin"
admin.site.index_title = "Panel de Administración OIKOS"
