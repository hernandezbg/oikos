from decimal import Decimal
from datetime import datetime
from django.db.models import Sum, Q
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO


def formato_pesos(monto):
    """
    Convierte un número a formato de pesos argentinos
    Ejemplo: 1234567.89 -> "$1.234.567,89"
    """
    if monto is None:
        return "$0,00"

    monto = Decimal(str(monto))

    # Separar parte entera y decimal
    partes = str(abs(monto)).split('.')
    parte_entera = partes[0]
    parte_decimal = partes[1][:2] if len(partes) > 1 else '00'

    # Agregar separador de miles
    parte_entera_formateada = ''
    for i, digito in enumerate(reversed(parte_entera)):
        if i > 0 and i % 3 == 0:
            parte_entera_formateada = '.' + parte_entera_formateada
        parte_entera_formateada = digito + parte_entera_formateada

    # Agregar signo negativo si corresponde
    signo = '-' if monto < 0 else ''

    return f"{signo}${parte_entera_formateada},{parte_decimal.ljust(2, '0')}"


def calcular_saldo_mes(iglesia, año_mes):
    """
    Calcula el saldo de un mes específico para una iglesia
    año_mes: formato 'YYYY-MM'
    """
    from core.models import Movimiento, SaldoMensual

    # Obtener o crear el saldo mensual
    saldo, created = SaldoMensual.objects.get_or_create(
        iglesia=iglesia,
        año_mes=año_mes,
        defaults={
            'saldo_inicial': 0,
            'total_ingresos': 0,
            'total_egresos': 0,
            'saldo_final': 0
        }
    )

    # Calcular saldo inicial (saldo final del mes anterior)
    año, mes = año_mes.split('-')
    mes_anterior = int(mes) - 1
    año_anterior = int(año)

    if mes_anterior == 0:
        mes_anterior = 12
        año_anterior -= 1

    año_mes_anterior = f"{año_anterior}-{str(mes_anterior).zfill(2)}"

    try:
        saldo_mes_anterior = SaldoMensual.objects.get(iglesia=iglesia, año_mes=año_mes_anterior)
        saldo.saldo_inicial = saldo_mes_anterior.saldo_final
    except SaldoMensual.DoesNotExist:
        saldo.saldo_inicial = 0

    # Calcular totales del mes (excluye movimientos anulados)
    movimientos_mes = Movimiento.objects.filter(
        iglesia=iglesia,
        fecha__year=int(año),
        fecha__month=int(mes),
        anulado=False
    )

    ingresos = movimientos_mes.filter(tipo='INGRESO').aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0.00')

    egresos = movimientos_mes.filter(tipo='EGRESO').aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0.00')

    saldo.total_ingresos = ingresos
    saldo.total_egresos = egresos
    saldo.calcular_saldo_final()
    saldo.save()

    return saldo


def generar_reporte_pdf(iglesia, año_mes):
    """
    Genera un PDF con el reporte mensual de movimientos
    """
    from core.models import Movimiento, SaldoMensual, CategoriaEgreso

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    # Título
    title = Paragraph(f"OIKOS - Reporte Mensual", title_style)
    elements.append(title)

    subtitle = Paragraph(
        f"{iglesia.nombre}<br/>{año_mes}",
        ParagraphStyle('subtitle', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER)
    )
    elements.append(subtitle)
    elements.append(Spacer(1, 20))

    # Obtener saldo mensual
    try:
        saldo = SaldoMensual.objects.get(iglesia=iglesia, año_mes=año_mes)
    except SaldoMensual.DoesNotExist:
        saldo = calcular_saldo_mes(iglesia, año_mes)

    # Tabla de resumen
    data_resumen = [
        ['RESUMEN MENSUAL', ''],
        ['Saldo Inicial', formato_pesos(saldo.saldo_inicial)],
        ['Total Ingresos', formato_pesos(saldo.total_ingresos)],
        ['Total Egresos', formato_pesos(saldo.total_egresos)],
        ['Saldo Final', formato_pesos(saldo.saldo_final)],
    ]

    table_resumen = Table(data_resumen, colWidths=[4*inch, 2*inch])
    table_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ecf0f1')),
    ]))

    elements.append(table_resumen)
    elements.append(Spacer(1, 30))

    # Movimientos del mes
    año, mes = año_mes.split('-')
    movimientos = Movimiento.objects.filter(
        iglesia=iglesia,
        fecha__year=int(año),
        fecha__month=int(mes)
    ).order_by('fecha')

    if movimientos.exists():
        elements.append(Paragraph("DETALLE DE MOVIMIENTOS", styles['Heading2']))
        elements.append(Spacer(1, 12))

        data_movimientos = [['Fecha', 'Tipo', 'Categoría', 'Concepto', 'Monto']]

        for mov in movimientos:
            categoria = mov.categoria_ingreso or mov.categoria_egreso
            data_movimientos.append([
                mov.fecha.strftime('%d/%m/%Y'),
                mov.get_tipo_display(),
                str(categoria),
                mov.concepto[:40] + '...' if len(mov.concepto) > 40 else mov.concepto,
                formato_pesos(mov.monto)
            ])

        table_movimientos = Table(data_movimientos, colWidths=[1*inch, 1*inch, 1.5*inch, 2.5*inch, 1*inch])
        table_movimientos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))

        elements.append(table_movimientos)

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def get_dashboard_data(iglesia, meses=6, mes_distribucion=None):
    """
    Obtiene los datos para los gráficos del dashboard
    Retorna los últimos N meses de datos
    mes_distribucion: mes para el gráfico de distribución (formato YYYY-MM), por defecto mes actual
    """
    from core.models import SaldoMensual, Movimiento
    from django.db.models import Sum
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta

    # Calcular fecha de inicio (N meses atrás)
    fecha_actual = datetime.now()
    fecha_inicio = fecha_actual - relativedelta(months=meses-1)

    # Generar lista de meses
    meses_labels = []
    saldos_data = []

    for i in range(meses):
        fecha = fecha_inicio + relativedelta(months=i)
        año_mes = fecha.strftime('%Y-%m')
        mes_label = fecha.strftime('%b %Y')

        # Obtener o calcular saldo del mes
        try:
            saldo = SaldoMensual.objects.get(iglesia=iglesia, año_mes=año_mes)
        except SaldoMensual.DoesNotExist:
            saldo = calcular_saldo_mes(iglesia, año_mes)

        meses_labels.append(mes_label)
        saldos_data.append(float(saldo.saldo_final))

    # Distribución de gastos por categoría (mes seleccionado o mes actual)
    mes_para_distribucion = mes_distribucion if mes_distribucion else fecha_actual.strftime('%Y-%m')
    año, mes = mes_para_distribucion.split('-')

    egresos_por_categoria = Movimiento.objects.filter(
        iglesia=iglesia,
        tipo='EGRESO',
        fecha__year=int(año),
        fecha__month=int(mes),
        anulado=False
    ).values('categoria_egreso__nombre').annotate(
        total=Sum('monto')
    ).order_by('-total')

    categorias_labels = [item['categoria_egreso__nombre'] for item in egresos_por_categoria]
    categorias_data = [float(item['total']) for item in egresos_por_categoria]

    return {
        'meses_labels': meses_labels,
        'saldos_data': saldos_data,
        'categorias_labels': categorias_labels,
        'categorias_data': categorias_data,
    }
