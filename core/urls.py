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
    politica_cookies_view,
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
    # Ayuda
    path('ayuda/', ayuda_view, name='ayuda'),
    # Política de Cookies
    path('politica-cookies/', politica_cookies_view, name='politica_cookies'),
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
]
