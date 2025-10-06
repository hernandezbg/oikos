from django.urls import path
from core.views import (
    home_view,
    CustomLoginView,
    DashboardView,
    MovimientoCreateView,
    MovimientoListView,
    reporte_mensual_view,
    generar_reporte_pdf_view,
    dashboard_data_api,
    exportar_excel_view,
    registro_view,
    registro_iglesia_google_view,
    anular_movimiento_view
)
from django.contrib.auth.views import LogoutView

urlpatterns = [
    # Home / Landing page
    path('', home_view, name='home'),
    # Login y logout
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('registro/', registro_view, name='registro'),
    path('registro-iglesia/', registro_iglesia_google_view, name='registro_iglesia_google'),
    # Dashboard y vistas principales
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('movimientos/nuevo/', MovimientoCreateView.as_view(), name='movimiento_create'),
    path('movimientos/', MovimientoListView.as_view(), name='movimiento_list'),
    path('movimientos/<int:pk>/anular/', anular_movimiento_view, name='anular_movimiento'),
    path('reportes/mensual/', reporte_mensual_view, name='reporte_mensual'),
    path('reportes/generar-pdf/', generar_reporte_pdf_view, name='generar_reporte_pdf'),
    path('api/dashboard-data/', dashboard_data_api, name='dashboard_data_api'),
    path('exportar/excel/', exportar_excel_view, name='exportar_excel'),
]
