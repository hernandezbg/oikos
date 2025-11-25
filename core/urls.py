from django.urls import path
from core.views import (
    home_view,
    CustomLoginView,
    DashboardView,
    MovimientoCreateView,
    MovimientoUpdateView,
    MovimientoListView,
    reporte_mensual_view,
    generar_reporte_pdf_view,
    generar_reporte_movimientos_completo_view,
    dashboard_data_api,
    exportar_excel_view,
    registro_view,
    registro_iglesia_google_view,
    seleccionar_tipo_registro_view,
    registro_con_codigo_view,
    gestionar_usuarios_view,
    anular_movimiento_view,
    ayuda_view,
    contadora_billetes_view,
    politica_cookies_view,
    terminos_condiciones_view,
    aceptar_terminos_view,
    perfil_usuario_view,
    # Categorías de Ingreso
    CategoriaIngresoListView,
    CategoriaIngresoCreateView,
    CategoriaIngresoUpdateView,
    toggle_categoria_ingreso,
    # Categorías de Egreso
    CategoriaEgresoListView,
    CategoriaEgresoCreateView,
    CategoriaEgresoUpdateView,
    toggle_categoria_egreso,
)
from core.views_caja_chica import (
    # Cajas Chicas
    CajaChicaListView,
    CajaChicaCreateView,
    CajaChicaUpdateView,
    toggle_caja_chica,
    DashboardCajaChicaView,
    dashboard_caja_data_api,
    # Movimientos de Caja
    MovimientoCajaChicaListView,
    MovimientoCajaChicaCreateView,
    MovimientoCajaChicaUpdateView,
    anular_movimiento_caja_view,
    # Transferencias
    TransferenciaListView,
    TransferenciaCreateView,
    anular_transferencia_view,
    # Códigos de invitación
    generar_codigo_caja_view,
)
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # Home / Landing page
    path('', home_view, name='home'),
    # Login y logout
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('registro/', registro_view, name='registro'),
    # Registro con código de invitación
    path('seleccionar-registro/', seleccionar_tipo_registro_view, name='seleccionar_tipo_registro'),
    path('registro-iglesia/', registro_iglesia_google_view, name='registro_iglesia_google'),
    path('registro-codigo/', registro_con_codigo_view, name='registro_con_codigo'),
    # Dashboard y vistas principales
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('movimientos/nuevo/', MovimientoCreateView.as_view(), name='movimiento_create'),
    path('movimientos/<int:pk>/editar/', MovimientoUpdateView.as_view(), name='movimiento_update'),
    path('movimientos/', MovimientoListView.as_view(), name='movimiento_list'),
    path('movimientos/<int:pk>/anular/', anular_movimiento_view, name='anular_movimiento'),
    path('reportes/mensual/', reporte_mensual_view, name='reporte_mensual'),
    path('reportes/generar-pdf/', generar_reporte_pdf_view, name='generar_reporte_pdf'),
    path('reportes/movimientos-completo/', generar_reporte_movimientos_completo_view, name='reporte_movimientos_completo'),
    # Gestión de usuarios (solo ADMIN)
    path('usuarios/gestionar/', gestionar_usuarios_view, name='gestionar_usuarios'),
    # Perfil de usuario
    path('perfil/', perfil_usuario_view, name='perfil_usuario'),
    # Ayuda
    path('ayuda/', ayuda_view, name='ayuda'),
    # Contadora de Billetes
    path('contadora-billetes/', contadora_billetes_view, name='contadora_billetes'),
    # Política de Cookies
    path('politica-cookies/', politica_cookies_view, name='politica_cookies'),
    # Términos y Condiciones
    path('terminos-condiciones/', terminos_condiciones_view, name='terminos_condiciones'),
    path('aceptar-terminos/', aceptar_terminos_view, name='aceptar_terminos'),
    # API y exportación
    path('api/dashboard-data/', dashboard_data_api, name='dashboard_data_api'),
    path('exportar/excel/', exportar_excel_view, name='exportar_excel'),
    # Categorías de Ingreso
    path('categorias/ingresos/', CategoriaIngresoListView.as_view(), name='categoria_ingreso_list'),
    path('categorias/ingresos/nueva/', CategoriaIngresoCreateView.as_view(), name='categoria_ingreso_create'),
    path('categorias/ingresos/<int:pk>/editar/', CategoriaIngresoUpdateView.as_view(), name='categoria_ingreso_update'),
    path('categorias/ingresos/<int:pk>/toggle/', toggle_categoria_ingreso, name='toggle_categoria_ingreso'),
    # Categorías de Egreso
    path('categorias/egresos/', CategoriaEgresoListView.as_view(), name='categoria_egreso_list'),
    path('categorias/egresos/nueva/', CategoriaEgresoCreateView.as_view(), name='categoria_egreso_create'),
    path('categorias/egresos/<int:pk>/editar/', CategoriaEgresoUpdateView.as_view(), name='categoria_egreso_update'),
    path('categorias/egresos/<int:pk>/toggle/', toggle_categoria_egreso, name='toggle_categoria_egreso'),

    # ======================================
    # CAJAS CHICAS
    # ======================================

    # Gestión de Cajas Chicas (solo ADMIN)
    path('cajas-chicas/', CajaChicaListView.as_view(), name='caja_chica_list'),
    path('cajas-chicas/nueva/', CajaChicaCreateView.as_view(), name='caja_chica_create'),
    path('cajas-chicas/<int:pk>/editar/', CajaChicaUpdateView.as_view(), name='caja_chica_update'),
    path('cajas-chicas/<int:pk>/toggle/', toggle_caja_chica, name='toggle_caja_chica'),
    path('cajas-chicas/<int:pk>/dashboard/', DashboardCajaChicaView.as_view(), name='dashboard_caja'),
    path('api/dashboard-caja-data/<int:caja_pk>/', dashboard_caja_data_api, name='dashboard_caja_data_api'),

    # Movimientos de Caja Chica
    path('cajas-chicas/<int:caja_pk>/movimientos/', MovimientoCajaChicaListView.as_view(), name='movimiento_caja_list'),
    path('cajas-chicas/<int:caja_pk>/movimientos/nuevo/', MovimientoCajaChicaCreateView.as_view(), name='movimiento_caja_create'),
    path('cajas-chicas/<int:caja_pk>/movimientos/<int:pk>/editar/', MovimientoCajaChicaUpdateView.as_view(), name='movimiento_caja_update'),
    path('cajas-chicas/<int:caja_pk>/movimientos/<int:pk>/anular/', anular_movimiento_caja_view, name='anular_movimiento_caja'),

    # Transferencias entre Cajas (solo ADMIN)
    path('transferencias/', TransferenciaListView.as_view(), name='transferencia_list'),
    path('transferencias/nueva/', TransferenciaCreateView.as_view(), name='transferencia_create'),
    path('transferencias/<int:pk>/anular/', anular_transferencia_view, name='anular_transferencia'),

    # Códigos de Invitación para Cajas
    path('cajas-chicas/generar-codigo/', generar_codigo_caja_view, name='generar_codigo_caja'),
]
