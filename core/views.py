from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, CreateView, ListView
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponse
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from core.models import Movimiento, SaldoMensual, CategoriaIngreso, CategoriaEgreso, Iglesia
from core.forms import MovimientoForm, FiltroMovimientosForm, RegistroForm
from core.forms_google import RegistroIglesiaGoogleForm
from core.utils import formato_pesos, calcular_saldo_mes, generar_reporte_pdf, get_dashboard_data
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required


class CustomLoginView(LoginView):
    template_name = 'core/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'OIKOS'
        return context


def registro_view(request):
    """
    Vista para registro de nueva iglesia y usuario tesorero
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Iniciar sesión automáticamente
            login(request, user)
            messages.success(
                request,
                f'¡Bienvenido a OIKOS! La iglesia {user.iglesia.nombre} ha sido registrada exitosamente.'
            )
            return redirect('dashboard')
    else:
        form = RegistroForm()

    return render(request, 'core/registro.html', {'form': form})


@login_required
def registro_iglesia_google_view(request):
    """
    Vista para registrar iglesia después de login con Google.
    El usuario ya está autenticado pero no tiene iglesia asignada.
    """
    # Si ya tiene iglesia, redirigir al dashboard
    if hasattr(request.user, 'iglesia') and request.user.iglesia:
        return redirect('dashboard')

    # Si es admin/staff, puede acceder al dashboard sin iglesia
    if request.user.is_staff or request.user.is_superuser:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegistroIglesiaGoogleForm(request.POST)
        if form.is_valid():
            # Crear la iglesia
            iglesia = form.save(commit=False)
            iglesia.activa = True
            iglesia.save()

            # Asignar iglesia al usuario y hacerlo tesorero
            request.user.iglesia = iglesia
            request.user.rol = 'TESORERO'
            request.user.puede_aprobar = True
            request.user.save()

            messages.success(
                request,
                f'¡Bienvenido a OIKOS! La iglesia {iglesia.nombre} ha sido registrada exitosamente.'
            )
            return redirect('dashboard')
    else:
        form = RegistroIglesiaGoogleForm()

    return render(request, 'core/registro_iglesia_google.html', {
        'form': form,
        'user': request.user
    })


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'core/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        # Si el usuario no tiene iglesia, redirigir a registro de iglesia
        if request.user.is_authenticated:
            if not request.user.is_staff and not request.user.is_superuser:
                if not request.user.iglesia:
                    return redirect('registro_iglesia_google')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        iglesia = self.request.user.iglesia
        fecha_actual = timezone.now()
        mes_actual = fecha_actual.strftime('%Y-%m')

        # Calcular saldo actual
        try:
            saldo_actual = SaldoMensual.objects.get(iglesia=iglesia, año_mes=mes_actual)
        except SaldoMensual.DoesNotExist:
            saldo_actual = calcular_saldo_mes(iglesia, mes_actual)

        # Totales del mes actual
        año, mes = mes_actual.split('-')
        movimientos_mes = Movimiento.objects.filter(
            iglesia=iglesia,
            fecha__year=int(año),
            fecha__month=int(mes)
        )

        total_ingresos_mes = movimientos_mes.filter(tipo='INGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')

        total_egresos_mes = movimientos_mes.filter(tipo='EGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')

        # Últimos movimientos
        ultimos_movimientos = Movimiento.objects.filter(
            iglesia=iglesia
        ).order_by('-fecha', '-fecha_creacion')[:5]

        # Alertas
        alertas = []
        saldo_final = saldo_actual.saldo_final

        if saldo_final < Decimal('2000000'):
            alertas.append({
                'tipo': 'warning',
                'mensaje': f'Saldo actual bajo: {formato_pesos(saldo_final)}'
            })

        if total_egresos_mes > total_ingresos_mes * Decimal('1.2'):
            alertas.append({
                'tipo': 'danger',
                'mensaje': 'Los egresos superan el 120% de los ingresos del mes'
            })

        # Determinar clase de color para saldo
        if saldo_final < 0:
            saldo_clase = 'saldo-negativo'
        elif saldo_final < Decimal('2000000'):
            saldo_clase = 'saldo-alerta'
        else:
            saldo_clase = 'saldo-positivo'

        context.update({
            'iglesia': iglesia,
            'saldo_actual': saldo_final,
            'saldo_actual_format': formato_pesos(saldo_final),
            'saldo_clase': saldo_clase,
            'total_ingresos_mes': formato_pesos(total_ingresos_mes),
            'total_egresos_mes': formato_pesos(total_egresos_mes),
            'ultimos_movimientos': ultimos_movimientos,
            'alertas': alertas,
        })

        return context


class MovimientoCreateView(LoginRequiredMixin, CreateView):
    model = Movimiento
    form_class = MovimientoForm
    template_name = 'core/movimiento_form.html'
    success_url = reverse_lazy('movimiento_list')

    def dispatch(self, request, *args, **kwargs):
        # Si el usuario no tiene iglesia, redirigir a registro de iglesia
        if request.user.is_authenticated:
            if not request.user.is_staff and not request.user.is_superuser:
                if not request.user.iglesia:
                    return redirect('registro_iglesia_google')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['iglesia'] = self.request.user.iglesia
        return kwargs

    def form_valid(self, form):
        form.instance.iglesia = self.request.user.iglesia
        form.instance.creado_por = self.request.user
        return super().form_valid(form)


class MovimientoListView(LoginRequiredMixin, ListView):
    model = Movimiento
    template_name = 'core/movimiento_list.html'
    context_object_name = 'movimientos'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Si el usuario no tiene iglesia, redirigir a registro de iglesia
        if request.user.is_authenticated:
            if not request.user.is_staff and not request.user.is_superuser:
                if not request.user.iglesia:
                    return redirect('registro_iglesia_google')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Movimiento.objects.filter(
            iglesia=self.request.user.iglesia
        ).order_by('-fecha', '-fecha_creacion')

        # Aplicar filtros
        form = FiltroMovimientosForm(
            self.request.GET,
            iglesia=self.request.user.iglesia
        )

        if form.is_valid():
            if form.cleaned_data.get('mes'):
                mes_fecha = form.cleaned_data['mes']
                queryset = queryset.filter(
                    fecha__year=mes_fecha.year,
                    fecha__month=mes_fecha.month
                )

            if form.cleaned_data.get('tipo'):
                queryset = queryset.filter(tipo=form.cleaned_data['tipo'])

            if form.cleaned_data.get('categoria'):
                cat = form.cleaned_data['categoria']
                if cat.startswith('ingreso_'):
                    cat_id = int(cat.split('_')[1])
                    queryset = queryset.filter(categoria_ingreso_id=cat_id)
                elif cat.startswith('egreso_'):
                    cat_id = int(cat.split('_')[1])
                    queryset = queryset.filter(categoria_egreso_id=cat_id)

            if form.cleaned_data.get('buscar'):
                queryset = queryset.filter(
                    concepto__icontains=form.cleaned_data['buscar']
                )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = FiltroMovimientosForm(
            self.request.GET,
            iglesia=self.request.user.iglesia
        )
        return context


@login_required
def reporte_mensual_view(request):
    """
    Vista para generar reporte PDF mensual
    """
    # Si el usuario no tiene iglesia, redirigir a registro de iglesia
    if request.user.is_authenticated:
        if not request.user.is_staff and not request.user.is_superuser:
            if not request.user.iglesia:
                return redirect('registro_iglesia_google')

    iglesia = request.user.iglesia
    año_mes = request.GET.get('mes', timezone.now().strftime('%Y-%m'))

    # Generar PDF
    pdf_buffer = generar_reporte_pdf(iglesia, año_mes)

    # Retornar como descarga
    response = HttpResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_{iglesia.nombre}_{año_mes}.pdf"'

    return response


@login_required
def dashboard_data_api(request):
    """
    API para obtener datos de gráficos del dashboard
    """
    # Si el usuario no tiene iglesia, retornar datos vacíos
    if request.user.is_authenticated:
        if not request.user.is_staff and not request.user.is_superuser:
            if not request.user.iglesia:
                return JsonResponse({'labels': [], 'ingresos': [], 'egresos': []})

    iglesia = request.user.iglesia
    data = get_dashboard_data(iglesia, meses=6)

    return JsonResponse(data)


@login_required
def exportar_excel_view(request):
    """
    Exportar movimientos a Excel
    """
    # Si el usuario no tiene iglesia, redirigir a registro de iglesia
    if request.user.is_authenticated:
        if not request.user.is_staff and not request.user.is_superuser:
            if not request.user.iglesia:
                return redirect('registro_iglesia_google')

    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    from io import BytesIO

    iglesia = request.user.iglesia

    # Obtener filtros
    queryset = Movimiento.objects.filter(iglesia=iglesia).order_by('-fecha')

    # Aplicar filtros si existen
    mes = request.GET.get('mes')
    if mes:
        año, mes_num = mes.split('-')
        queryset = queryset.filter(fecha__year=int(año), fecha__month=int(mes_num))

    # Crear workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Movimientos"

    # Estilos
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    header_alignment = Alignment(horizontal="center", vertical="center")

    # Estilos para montos
    egreso_font = Font(bold=True, color="DC3545")  # Rojo
    ingreso_font = Font(bold=True, color="198754")  # Verde

    # Headers
    headers = ['Fecha', 'Tipo', 'Categoría', 'Concepto', 'Monto', 'Comprobante']
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment

    # Datos
    for row, mov in enumerate(queryset, start=2):
        categoria = mov.categoria_ingreso or mov.categoria_egreso
        ws.cell(row=row, column=1, value=mov.fecha.strftime('%d/%m/%Y'))
        ws.cell(row=row, column=2, value=mov.get_tipo_display())
        ws.cell(row=row, column=3, value=str(categoria))
        ws.cell(row=row, column=4, value=mov.concepto)

        # Monto: negativo para egresos, positivo para ingresos
        monto_cell = ws.cell(row=row, column=5)
        if mov.tipo == 'EGRESO':
            monto_cell.value = -float(mov.monto)  # Negativo
            monto_cell.font = egreso_font  # Rojo
        else:
            monto_cell.value = float(mov.monto)
            monto_cell.font = ingreso_font  # Verde

        # Formato de número con separador de miles
        monto_cell.number_format = '#,##0.00'

        ws.cell(row=row, column=6, value=mov.comprobante_nro or '')

    # Ajustar anchos de columna
    ws.column_dimensions['A'].width = 12
    ws.column_dimensions['B'].width = 10
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 50
    ws.column_dimensions['E'].width = 15
    ws.column_dimensions['F'].width = 15

    # Guardar en buffer
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Retornar como descarga
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'movimientos_{iglesia.nombre}_{timezone.now().strftime("%Y%m%d")}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response
