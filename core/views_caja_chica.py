from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from decimal import Decimal

from core.models import CajaChica, MovimientoCajaChica, TransferenciaCajaChica, CodigoInvitacion, UsuarioCajaChica
from core.forms_caja_chica import (
    CajaChicaForm,
    MovimientoCajaChicaForm,
    TransferenciaCajaChicaForm,
    GenerarCodigoCajaForm
)


# ============================================================================
# VISTAS DE CAJAS CHICAS
# ============================================================================

class CajaChicaListView(LoginRequiredMixin, ListView):
    model = CajaChica
    template_name = 'core/caja_chica_list.html'
    context_object_name = 'cajas'

    def dispatch(self, request, *args, **kwargs):
        # Solo ADMIN puede ver esta vista
        if request.user.rol != 'ADMIN':
            messages.error(request, 'No tienes permisos para gestionar cajas chicas')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return CajaChica.objects.filter(
            iglesia=self.request.user.iglesia
        ).order_by('-activa', 'nombre')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calcular saldo de cada caja
        for caja in context['cajas']:
            caja.saldo_actual = caja.calcular_saldo_actual()

        return context


class CajaChicaCreateView(LoginRequiredMixin, CreateView):
    model = CajaChica
    form_class = CajaChicaForm
    template_name = 'core/caja_chica_form.html'
    success_url = reverse_lazy('caja_chica_list')

    def dispatch(self, request, *args, **kwargs):
        # Solo ADMIN puede crear cajas
        if request.user.rol != 'ADMIN':
            messages.error(request, 'Solo los administradores pueden crear cajas chicas')
            return redirect('caja_chica_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.iglesia = self.request.user.iglesia
        form.instance.creada_por = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Caja "{self.object.nombre}" creada exitosamente'
        )
        return response


class CajaChicaUpdateView(LoginRequiredMixin, UpdateView):
    model = CajaChica
    form_class = CajaChicaForm
    template_name = 'core/caja_chica_form.html'
    success_url = reverse_lazy('caja_chica_list')

    def dispatch(self, request, *args, **kwargs):
        # Solo ADMIN puede editar cajas
        if request.user.rol != 'ADMIN':
            messages.error(request, 'Solo los administradores pueden editar cajas chicas')
            return redirect('caja_chica_list')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return CajaChica.objects.filter(iglesia=self.request.user.iglesia)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Caja "{self.object.nombre}" actualizada exitosamente'
        )
        return response


@login_required
def desactivar_caja_chica(request, pk):
    """Vista para desactivar/reactivar una caja chica"""
    if request.user.rol != 'ADMIN':
        messages.error(request, 'No tienes permisos para esta acción')
        return redirect('caja_chica_list')

    caja = get_object_or_404(CajaChica, pk=pk, iglesia=request.user.iglesia)

    if request.method == 'POST':
        caja.activa = not caja.activa
        caja.save()
        estado = 'activada' if caja.activa else 'desactivada'
        messages.success(request, f'Caja "{caja.nombre}" {estado} exitosamente')
        return redirect('caja_chica_list')

    return render(request, 'core/caja_chica_confirmar_desactivar.html', {'caja': caja})


# ============================================================================
# VISTAS DE MOVIMIENTOS DE CAJA CHICA
# ============================================================================

class MovimientoCajaChicaListView(LoginRequiredMixin, ListView):
    model = MovimientoCajaChica
    template_name = 'core/movimiento_caja_list.html'
    context_object_name = 'movimientos'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self.caja = get_object_or_404(CajaChica, pk=self.kwargs['caja_pk'])

        # Verificar que el usuario tenga acceso a esta caja
        if not request.user.puede_ver_caja(self.caja):
            messages.error(request, 'No tienes acceso a esta caja')
            return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return MovimientoCajaChica.objects.filter(
            caja_chica=self.caja
        ).order_by('-fecha', '-fecha_creacion')

    def get_context_data(self, **kwargs):
        from django.db.models import Sum
        from decimal import Decimal

        context = super().get_context_data(**kwargs)
        context['caja'] = self.caja
        context['saldo_actual'] = self.caja.calcular_saldo_actual()
        context['puede_crear'] = self.request.user.puede_crear_movimiento_caja(self.caja)
        context['es_admin'] = self.request.user.rol == 'ADMIN'

        # Calcular totales
        movimientos = MovimientoCajaChica.objects.filter(caja_chica=self.caja, anulado=False)
        context['total_ingresos'] = movimientos.filter(tipo='INGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')
        context['total_egresos'] = movimientos.filter(tipo='EGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')

        # Filtrar categorías por iglesia para el modal
        context['categorias_ingreso'] = self.caja.iglesia.categorias_ingreso.filter(activa=True)
        context['categorias_egreso'] = self.caja.iglesia.categorias_egreso.filter(activa=True)

        return context


class MovimientoCajaChicaCreateView(LoginRequiredMixin, CreateView):
    model = MovimientoCajaChica
    form_class = MovimientoCajaChicaForm
    template_name = 'core/movimiento_caja_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.caja = get_object_or_404(CajaChica, pk=self.kwargs['caja_pk'])

        # Verificar permisos para crear
        if not request.user.puede_crear_movimiento_caja(self.caja):
            messages.error(request, 'No tienes permisos para crear movimientos en esta caja')
            return redirect('movimiento_caja_list', caja_pk=self.caja.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['iglesia'] = self.caja.iglesia
        return kwargs

    def form_valid(self, form):
        movimiento = form.save(commit=False)
        movimiento.caja_chica = self.caja
        movimiento.creado_por = self.request.user
        movimiento.aprobado_por = self.request.user
        movimiento.save()

        messages.success(self.request, f'{movimiento.get_tipo_display()} registrado: ${movimiento.monto}')

        # Manejar el action (save vs save_and_new)
        action = self.request.POST.get('action', 'save')
        if action == 'save_and_new':
            return redirect(f"{reverse('movimiento_caja_list', kwargs={'caja_pk': self.caja.pk})}?nuevo=1")

        return redirect('movimiento_caja_list', caja_pk=self.caja.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['caja'] = self.caja
        return context


class MovimientoCajaChicaUpdateView(LoginRequiredMixin, UpdateView):
    model = MovimientoCajaChica
    form_class = MovimientoCajaChicaForm
    template_name = 'core/movimiento_caja_form.html'

    def dispatch(self, request, *args, **kwargs):
        movimiento = self.get_object()
        self.caja = movimiento.caja_chica

        # Solo ADMIN o TESORERO_CAJA puede editar
        if not (request.user.rol == 'ADMIN' or
                request.user.puede_crear_movimiento_caja(self.caja)):
            messages.error(request, 'No tienes permisos para editar movimientos')
            return redirect('movimiento_caja_list', caja_pk=self.caja.pk)

        # No se pueden editar movimientos anulados
        if movimiento.anulado:
            messages.error(request, 'No puedes editar un movimiento anulado')
            return redirect('movimiento_caja_list', caja_pk=self.caja.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return MovimientoCajaChica.objects.filter(anulado=False)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['iglesia'] = self.caja.iglesia
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Movimiento actualizado exitosamente')
        return response

    def get_success_url(self):
        return reverse_lazy('movimiento_caja_list', kwargs={'caja_pk': self.caja.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['caja'] = self.caja
        return context


@login_required
def anular_movimiento_caja(request, caja_pk, pk):
    """Vista para anular un movimiento de caja chica"""
    caja = get_object_or_404(CajaChica, pk=caja_pk)
    movimiento = get_object_or_404(MovimientoCajaChica, pk=pk, caja_chica=caja)

    # Solo ADMIN puede anular
    if request.user.rol != 'ADMIN':
        messages.error(request, 'Solo los administradores pueden anular movimientos')
        return redirect('movimiento_caja_list', caja_pk=caja.pk)

    if movimiento.anulado:
        messages.warning(request, 'Este movimiento ya está anulado')
        return redirect('movimiento_caja_list', caja_pk=caja.pk)

    if request.method == 'POST':
        motivo_anulacion = request.POST.get('motivo_anulacion', '')
        movimiento.anulado = True
        movimiento.motivo_anulacion = motivo_anulacion
        movimiento.anulado_por = request.user
        movimiento.save()

        messages.success(request, f'Movimiento anulado: {movimiento.concepto}')
        return redirect('movimiento_caja_list', caja_pk=caja.pk)

    return render(request, 'core/movimiento_caja_anular.html', {
        'movimiento': movimiento,
        'caja': caja
    })


# ============================================================================
# VISTAS DE TRANSFERENCIAS
# ============================================================================

class TransferenciaListView(LoginRequiredMixin, ListView):
    model = TransferenciaCajaChica
    template_name = 'core/transferencia_list.html'
    context_object_name = 'transferencias'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        # Solo ADMIN puede ver transferencias
        if request.user.rol != 'ADMIN':
            messages.error(request, 'No tienes permisos para ver transferencias')
            return redirect('dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TransferenciaCajaChica.objects.filter(
            caja_origen__iglesia=self.request.user.iglesia
        ).order_by('-fecha', '-fecha_creacion')


class TransferenciaCreateView(LoginRequiredMixin, CreateView):
    model = TransferenciaCajaChica
    form_class = TransferenciaCajaChicaForm
    template_name = 'core/transferencia_form.html'
    success_url = reverse_lazy('transferencia_list')

    def dispatch(self, request, *args, **kwargs):
        # Solo ADMIN puede crear transferencias
        if request.user.rol != 'ADMIN':
            messages.error(request, 'Solo los administradores pueden crear transferencias')
            return redirect('transferencia_list')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['iglesia'] = self.request.user.iglesia
        return kwargs

    def form_valid(self, form):
        form.instance.realizada_por = self.request.user
        response = super().form_valid(form)

        messages.success(
            self.request,
            f'Transferencia realizada: ${form.instance.monto} de {form.instance.caja_origen.nombre} '
            f'a {form.instance.caja_destino.nombre}'
        )
        return response


@login_required
def anular_transferencia(request, pk):
    """Vista para anular una transferencia"""
    transferencia = get_object_or_404(
        TransferenciaCajaChica,
        pk=pk,
        caja_origen__iglesia=request.user.iglesia
    )

    # Solo ADMIN puede anular
    if request.user.rol != 'ADMIN':
        messages.error(request, 'Solo los administradores pueden anular transferencias')
        return redirect('transferencia_list')

    if transferencia.anulada:
        messages.warning(request, 'Esta transferencia ya está anulada')
        return redirect('transferencia_list')

    if request.method == 'POST':
        transferencia.anular()
        messages.success(request, 'Transferencia anulada exitosamente')
        return redirect('transferencia_list')

    return render(request, 'core/transferencia_anular.html', {
        'transferencia': transferencia
    })


# ============================================================================
# VISTA PARA GENERAR CÓDIGOS DE INVITACIÓN PARA CAJAS
# ============================================================================

@login_required
def generar_codigo_caja_view(request):
    """Vista para que ADMIN genere códigos de invitación para cajas chicas"""
    if request.user.rol != 'ADMIN':
        messages.error(request, 'Solo los administradores pueden generar códigos')
        return redirect('caja_chica_list')

    if request.method == 'POST':
        form = GenerarCodigoCajaForm(request.POST, iglesia=request.user.iglesia)
        if form.is_valid():
            caja = form.cleaned_data['caja_chica']
            rol = form.cleaned_data['rol']
            dias_expiracion = form.cleaned_data['dias_expiracion']
            usos_maximos = form.cleaned_data['usos_maximos']

            # Crear código de invitación
            codigo = CodigoInvitacion.crear(
                iglesia=request.user.iglesia,
                rol=rol,
                creado_por=request.user,
                dias_expiracion=dias_expiracion,
                usos_maximos=usos_maximos,
                caja_chica=caja
            )

            messages.success(
                request,
                f'Código generado: {codigo.codigo} para {caja.nombre} '
                f'(válido por {dias_expiracion} días, hasta {usos_maximos} usos)'
            )
            return redirect('caja_chica_list')
    else:
        form = GenerarCodigoCajaForm(iglesia=request.user.iglesia)

    return render(request, 'core/generar_codigo_caja.html', {'form': form})


# ============================================================================
# DASHBOARD DE CAJA CHICA
# ============================================================================

class DashboardCajaChicaView(LoginRequiredMixin, DetailView):
    model = CajaChica
    template_name = 'core/dashboard_caja.html'
    context_object_name = 'caja'

    def dispatch(self, request, *args, **kwargs):
        caja = self.get_object()

        # Verificar acceso
        if not request.user.puede_ver_caja(caja):
            messages.error(request, 'No tienes acceso a esta caja')
            return redirect('dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from django.utils import timezone
        from dateutil.relativedelta import relativedelta
        from decimal import Decimal

        context = super().get_context_data(**kwargs)
        caja = self.object

        # Selector de mes (por defecto mes anterior)
        mes_anterior = (timezone.now() - relativedelta(months=1)).strftime('%Y-%m')
        mes_seleccionado = self.request.GET.get('mes', mes_anterior)

        # Saldo actual (histórico total)
        total_ingresos_historico = MovimientoCajaChica.objects.filter(
            caja_chica=caja,
            tipo='INGRESO',
            anulado=False
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        total_egresos_historico = MovimientoCajaChica.objects.filter(
            caja_chica=caja,
            tipo='EGRESO',
            anulado=False
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        saldo_final = total_ingresos_historico - total_egresos_historico + caja.saldo_inicial

        # Movimientos del mes seleccionado
        año, mes = mes_seleccionado.split('-')
        movimientos_mes = MovimientoCajaChica.objects.filter(
            caja_chica=caja,
            fecha__year=int(año),
            fecha__month=int(mes),
            anulado=False
        )

        total_ingresos_mes = movimientos_mes.filter(tipo='INGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')

        total_egresos_mes = movimientos_mes.filter(tipo='EGRESO').aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')

        # Últimos movimientos
        ultimos_movimientos = MovimientoCajaChica.objects.filter(
            caja_chica=caja
        ).order_by('-fecha', '-fecha_creacion')[:5]

        # Alertas
        alertas = []
        if saldo_final < Decimal('100000'):
            alertas.append({
                'tipo': 'warning',
                'mensaje': f'Saldo actual bajo: ${saldo_final:,.2f}'
            })

        if total_egresos_mes > total_ingresos_mes * Decimal('1.2'):
            alertas.append({
                'tipo': 'danger',
                'mensaje': 'Los egresos superan el 120% de los ingresos del mes'
            })

        # Clase de color para saldo
        if saldo_final < 0:
            saldo_clase = 'saldo-negativo'
        elif saldo_final < Decimal('100000'):
            saldo_clase = 'saldo-alerta'
        else:
            saldo_clase = 'saldo-positivo'

        # Formatear nombre del mes
        from datetime import datetime
        from core.utils import formato_mes, formato_pesos
        fecha_sel = datetime.strptime(mes_seleccionado, '%Y-%m')
        mes_nombre = formato_mes(fecha_sel, corto=False)

        context.update({
            'caja': caja,
            'mes_seleccionado': mes_seleccionado,
            'mes_nombre': mes_nombre,
            'saldo_actual': saldo_final,
            'saldo_actual_format': formato_pesos(saldo_final),
            'saldo_clase': saldo_clase,
            'total_ingresos_mes': formato_pesos(total_ingresos_mes),
            'total_egresos_mes': formato_pesos(total_egresos_mes),
            'ultimos_movimientos': ultimos_movimientos,
            'alertas': alertas,
            'puede_crear': self.request.user.puede_crear_movimiento_caja(caja),
            'puede_crear_movimientos': self.request.user.puede_crear_movimiento_caja(caja),
            'es_admin': self.request.user.rol == 'ADMIN',
        })

        return context


@login_required
def dashboard_caja_data_api(request, caja_pk):
    """API para obtener datos de gráficas del dashboard de caja chica"""
    from datetime import datetime, timedelta
    from django.db.models import Q
    from collections import defaultdict

    caja = get_object_or_404(CajaChica, pk=caja_pk)

    # Verificar acceso
    if not request.user.puede_ver_caja(caja):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    # Obtener año actual
    año_actual = datetime.now().year

    # Inicializar datos mensuales
    meses_labels = []
    saldos_data = []
    ingresos_data = []
    egresos_data = []
    balance_data = []

    saldo_acumulado = float(caja.saldo_inicial)

    # Procesar cada mes del año
    for mes in range(1, 13):
        fecha = datetime(año_actual, mes, 1)
        mes_nombre = fecha.strftime('%b')
        meses_labels.append(mes_nombre)

        # Obtener movimientos del mes
        movimientos = MovimientoCajaChica.objects.filter(
            caja_chica=caja,
            fecha__year=año_actual,
            fecha__month=mes,
            anulado=False
        )

        ingresos = float(movimientos.filter(tipo='INGRESO').aggregate(
            total=Sum('monto')
        )['total'] or 0)

        egresos = float(movimientos.filter(tipo='EGRESO').aggregate(
            total=Sum('monto')
        )['total'] or 0)

        # Calcular saldo acumulado
        saldo_acumulado += ingresos - egresos

        ingresos_data.append(ingresos)
        egresos_data.append(egresos)
        saldos_data.append(saldo_acumulado)
        balance_data.append(ingresos - egresos)

    # Calcular KPIs
    meses_con_datos = [i for i in range(len(ingresos_data)) if ingresos_data[i] > 0 or egresos_data[i] > 0]

    if meses_con_datos:
        promedio_ingresos = sum(ingresos_data[i] for i in meses_con_datos) / len(meses_con_datos)
        promedio_egresos = sum(egresos_data[i] for i in meses_con_datos) / len(meses_con_datos)
    else:
        promedio_ingresos = 0
        promedio_egresos = 0

    meses_superavit = sum(1 for b in balance_data if b > 0)
    meses_deficit = sum(1 for b in balance_data if b < 0)

    # Distribución de gastos por categoría
    categorias_labels = []
    categorias_data = []

    gastos_por_categoria = MovimientoCajaChica.objects.filter(
        caja_chica=caja,
        fecha__year=año_actual,
        tipo='EGRESO',
        anulado=False,
        categoria_egreso__isnull=False
    ).values('categoria_egreso__nombre').annotate(
        total=Sum('monto')
    ).order_by('-total')[:6]

    for item in gastos_por_categoria:
        categorias_labels.append(item['categoria_egreso__nombre'])
        categorias_data.append(float(item['total']))

    return JsonResponse({
        'meses_labels': meses_labels,
        'saldos_data': saldos_data,
        'ingresos_data': ingresos_data,
        'egresos_data': egresos_data,
        'balance_data': balance_data,
        'promedio_ingresos': promedio_ingresos,
        'promedio_egresos': promedio_egresos,
        'meses_superavit': meses_superavit,
        'meses_deficit': meses_deficit,
        'categorias_labels': categorias_labels,
        'categorias_data': categorias_data,
    })


# Alias para compatibilidad con urls.py
toggle_caja_chica = desactivar_caja_chica
toggle_categoria_egreso = None  # Placeholder si se necesita
anular_movimiento_caja_view = anular_movimiento_caja
anular_transferencia_view = anular_transferencia
