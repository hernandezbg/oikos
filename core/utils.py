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

# Nombres de meses en español
MESES_ES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
            'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

MESES_ES_CORTO = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
                   'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def formato_mes(fecha, corto=False):
    """
    Formatea una fecha mostrando el mes en español
    fecha: objeto datetime
    corto: True para formato corto (Ene 2025), False para formato largo (Enero 2025)
    """
    meses = MESES_ES_CORTO if corto else MESES_ES
    return f"{meses[fecha.month]} {fecha.year}"


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


def formato_moneda(monto, moneda='ARS'):
    """
    Convierte un número a formato según la moneda especificada

    Parámetros:
        monto: Valor numérico a formatear
        moneda: Código de moneda ('ARS', 'USD', 'EUR')

    Formatos:
        - ARS: $1.234.567,89 (separador de miles: punto, decimal: coma)
        - USD: US$1,234,567.89 (separador de miles: coma, decimal: punto)
        - EUR: €1.234.567,89 (separador de miles: punto, decimal: coma)

    Ejemplos:
        formato_moneda(1234567.89, 'ARS') -> "$1.234.567,89"
        formato_moneda(1234567.89, 'USD') -> "US$1,234,567.89"
        formato_moneda(1234567.89, 'EUR') -> "€1.234.567,89"
    """
    if monto is None:
        simbolos = {'ARS': '$', 'USD': 'US$', 'EUR': '€'}
        simbolo = simbolos.get(moneda, '$')
        return f"{simbolo}0,00" if moneda != 'USD' else f"{simbolo}0.00"

    monto = Decimal(str(monto))
    signo = '-' if monto < 0 else ''
    monto_abs = abs(monto)

    # Separar parte entera y decimal
    partes = str(monto_abs).split('.')
    parte_entera = partes[0]
    parte_decimal = partes[1][:2] if len(partes) > 1 else '00'

    if moneda == 'USD':
        # Formato USD: US$1,234,567.89
        parte_entera_formateada = ''
        for i, digito in enumerate(reversed(parte_entera)):
            if i > 0 and i % 3 == 0:
                parte_entera_formateada = ',' + parte_entera_formateada
            parte_entera_formateada = digito + parte_entera_formateada
        return f"{signo}US${parte_entera_formateada}.{parte_decimal.ljust(2, '0')}"

    elif moneda == 'EUR':
        # Formato EUR: €1.234.567,89
        parte_entera_formateada = ''
        for i, digito in enumerate(reversed(parte_entera)):
            if i > 0 and i % 3 == 0:
                parte_entera_formateada = '.' + parte_entera_formateada
            parte_entera_formateada = digito + parte_entera_formateada
        return f"{signo}€{parte_entera_formateada},{parte_decimal.ljust(2, '0')}"

    else:  # ARS por defecto
        # Formato ARS: $1.234.567,89
        parte_entera_formateada = ''
        for i, digito in enumerate(reversed(parte_entera)):
            if i > 0 and i % 3 == 0:
                parte_entera_formateada = '.' + parte_entera_formateada
            parte_entera_formateada = digito + parte_entera_formateada
        return f"{signo}${parte_entera_formateada},{parte_decimal.ljust(2, '0')}"


def calcular_saldo_mes(iglesia, año_mes):
    """
    Calcula el saldo de un mes específico para una iglesia
    año_mes: formato 'YYYY-MM'
    """
    from core.models import Movimiento, SaldoMensual
    from datetime import datetime

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

    # Calcular saldo inicial basado en TODOS los movimientos anteriores a este mes
    año, mes = año_mes.split('-')
    fecha_limite = datetime(int(año), int(mes), 1).date()

    # Calcular saldo acumulado de todos los movimientos ANTES de este mes
    movimientos_anteriores = Movimiento.objects.filter(
        iglesia=iglesia,
        fecha__lt=fecha_limite,
        anulado=False
    )

    ingresos_anteriores = movimientos_anteriores.filter(tipo='INGRESO').aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0.00')

    egresos_anteriores = movimientos_anteriores.filter(tipo='EGRESO').aggregate(
        total=Sum('monto')
    )['total'] or Decimal('0.00')

    saldo.saldo_inicial = ingresos_anteriores - egresos_anteriores

    # Calcular totales del mes actual (excluye movimientos anulados)
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
    Genera un PDF profesional con el reporte mensual de movimientos
    """
    from core.models import Movimiento, SaldoMensual, CategoriaEgreso, CategoriaIngreso
    from django.db.models import Sum

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.75*inch)
    elements = []

    styles = getSampleStyleSheet()

    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#6366f1'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#4f46e5'),
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )

    # Encabezado con información
    title = Paragraph("OIKOS - Sistema de Gestión Financiera", title_style)
    elements.append(title)

    subtitle = Paragraph(f"Reporte Mensual", subtitle_style)
    elements.append(subtitle)

    # Información de la iglesia
    año, mes = año_mes.split('-')
    mes_nombre = MESES_ES[int(mes)]

    info_iglesia = Paragraph(
        f"<b>{iglesia.nombre}</b><br/>"
        f"{iglesia.direccion if iglesia.direccion else ''}<br/>"
        f"Período: {mes_nombre} {año}",
        info_style
    )
    elements.append(info_iglesia)

    # Fecha de generación
    fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
    info_generacion = Paragraph(
        f"<i>Generado: {fecha_generacion}</i>",
        ParagraphStyle('small', parent=info_style, fontSize=8, textColor=colors.HexColor('#9ca3af'))
    )
    elements.append(info_generacion)
    elements.append(Spacer(1, 20))

    # Obtener saldo mensual
    try:
        saldo = SaldoMensual.objects.get(iglesia=iglesia, año_mes=año_mes)
    except SaldoMensual.DoesNotExist:
        saldo = calcular_saldo_mes(iglesia, año_mes)

    # Tabla de resumen financiero
    data_resumen = [
        ['RESUMEN FINANCIERO', ''],
        ['Saldo Inicial', formato_pesos(saldo.saldo_inicial)],
        ['(+) Total Ingresos', formato_pesos(saldo.total_ingresos)],
        ['(-) Total Egresos', formato_pesos(saldo.total_egresos)],
        ['Saldo Final', formato_pesos(saldo.saldo_final)],
    ]

    table_resumen = Table(data_resumen, colWidths=[4.5*inch, 2*inch])
    table_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor('#f9fafb')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dbeafe')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor('#1e40af')),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))

    elements.append(table_resumen)
    elements.append(Spacer(1, 20))

    # Resumen por categorías de INGRESOS
    ingresos_por_categoria = Movimiento.objects.filter(
        iglesia=iglesia,
        tipo='INGRESO',
        fecha__year=int(año),
        fecha__month=int(mes),
        anulado=False
    ).values('categoria_ingreso__nombre').annotate(
        total=Sum('monto')
    ).order_by('-total')

    if ingresos_por_categoria:
        elements.append(Paragraph("INGRESOS POR CATEGORÍA", styles['Heading3']))
        elements.append(Spacer(1, 10))

        data_ingresos_cat = [['Categoría', 'Monto']]
        for item in ingresos_por_categoria:
            data_ingresos_cat.append([
                item['categoria_ingreso__nombre'],
                formato_pesos(item['total'])
            ])

        table_ingresos_cat = Table(data_ingresos_cat, colWidths=[4.5*inch, 2*inch])
        table_ingresos_cat.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))

        elements.append(table_ingresos_cat)
        elements.append(Spacer(1, 20))

    # Resumen por categorías de EGRESOS
    egresos_por_categoria = Movimiento.objects.filter(
        iglesia=iglesia,
        tipo='EGRESO',
        fecha__year=int(año),
        fecha__month=int(mes),
        anulado=False
    ).values('categoria_egreso__nombre').annotate(
        total=Sum('monto')
    ).order_by('-total')

    if egresos_por_categoria:
        elements.append(Paragraph("EGRESOS POR CATEGORÍA", styles['Heading3']))
        elements.append(Spacer(1, 10))

        data_egresos_cat = [['Categoría', 'Monto']]
        for item in egresos_por_categoria:
            data_egresos_cat.append([
                item['categoria_egreso__nombre'],
                formato_pesos(item['total'])
            ])

        table_egresos_cat = Table(data_egresos_cat, colWidths=[4.5*inch, 2*inch])
        table_egresos_cat.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ef4444')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fef2f2')]),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))

        elements.append(table_egresos_cat)
        elements.append(Spacer(1, 20))

    # Detalle de movimientos del mes (excluye anulados)
    movimientos = Movimiento.objects.filter(
        iglesia=iglesia,
        fecha__year=int(año),
        fecha__month=int(mes),
        anulado=False
    ).order_by('fecha', 'tipo')

    if movimientos.exists():
        elements.append(Paragraph("DETALLE DE MOVIMIENTOS", styles['Heading3']))
        elements.append(Spacer(1, 10))

        data_movimientos = [['Fecha', 'Tipo', 'Categoría', 'Concepto', 'Monto']]

        for mov in movimientos:
            categoria = mov.categoria_ingreso or mov.categoria_egreso
            tipo_color = 'green' if mov.tipo == 'INGRESO' else 'red'

            data_movimientos.append([
                mov.fecha.strftime('%d/%m'),
                Paragraph(f'<font color="{tipo_color}">{mov.get_tipo_display()}</font>', styles['Normal']),
                str(categoria),
                mov.concepto[:45] + '...' if len(mov.concepto) > 45 else mov.concepto,
                formato_pesos(mov.monto)
            ])

        table_movimientos = Table(data_movimientos, colWidths=[0.7*inch, 0.9*inch, 1.4*inch, 2.5*inch, 1*inch])
        table_movimientos.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table_movimientos)

    # Pie de página
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#9ca3af'),
        alignment=TA_CENTER
    )
    footer = Paragraph(
        "<i>Este reporte fue generado automáticamente por OIKOS - Sistema de Gestión Financiera para Iglesias<br/>"
        "Los movimientos anulados no están incluidos en este reporte</i>",
        footer_style
    )
    elements.append(footer)

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer


def get_dashboard_data(iglesia, meses=None, mes_distribucion=None):
    """
    Obtiene los datos para los gráficos del dashboard
    Retorna todos los meses del año en curso (desde enero hasta el mes actual)
    mes_distribucion: mes para el gráfico de distribución (formato YYYY-MM), por defecto mes actual
    """
    from core.models import SaldoMensual, Movimiento
    from django.db.models import Sum
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta

    # Calcular desde enero del año en curso hasta el mes actual
    fecha_actual = datetime.now()
    fecha_inicio = datetime(fecha_actual.year, 1, 1)  # 1 de enero del año actual

    # Calcular cantidad de meses desde enero hasta ahora
    meses_transcurridos = fecha_actual.month

    # Generar lista de meses
    meses_labels = []
    saldos_data = []
    ingresos_data = []
    egresos_data = []
    balance_data = []

    for i in range(meses_transcurridos):
        fecha = fecha_inicio + relativedelta(months=i)
        año_mes = fecha.strftime('%Y-%m')
        mes_label = formato_mes(fecha, corto=True)  # Formato corto en español

        # Recalcular saldo del mes (siempre, para asegurar datos correctos)
        saldo = calcular_saldo_mes(iglesia, año_mes)

        meses_labels.append(mes_label)
        saldos_data.append(float(saldo.saldo_final))
        ingresos_data.append(float(saldo.total_ingresos))
        egresos_data.append(float(saldo.total_egresos))
        balance_data.append(float(saldo.total_ingresos - saldo.total_egresos))

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

    # Distribución de ingresos por categoría (mes seleccionado)
    ingresos_por_categoria = Movimiento.objects.filter(
        iglesia=iglesia,
        tipo='INGRESO',
        fecha__year=int(año),
        fecha__month=int(mes),
        anulado=False
    ).values('categoria_ingreso__nombre').annotate(
        total=Sum('monto')
    ).order_by('-total')

    categorias_ingresos_labels = [item['categoria_ingreso__nombre'] for item in ingresos_por_categoria]
    categorias_ingresos_data = [float(item['total']) for item in ingresos_por_categoria]

    # Calcular KPIs
    promedio_ingresos = sum(ingresos_data) / len(ingresos_data) if ingresos_data else 0
    promedio_egresos = sum(egresos_data) / len(egresos_data) if egresos_data else 0
    meses_superavit = sum(1 for b in balance_data if b > 0)
    meses_deficit = sum(1 for b in balance_data if b < 0)

    return {
        'meses_labels': meses_labels,
        'saldos_data': saldos_data,
        'ingresos_data': ingresos_data,
        'egresos_data': egresos_data,
        'balance_data': balance_data,
        'categorias_labels': categorias_labels,
        'categorias_data': categorias_data,
        'categorias_ingresos_labels': categorias_ingresos_labels,
        'categorias_ingresos_data': categorias_ingresos_data,
        'promedio_ingresos': promedio_ingresos,
        'promedio_egresos': promedio_egresos,
        'meses_superavit': meses_superavit,
        'meses_deficit': meses_deficit,
    }


def generar_reporte_movimientos_completo_pdf(iglesia, fecha_desde=None, fecha_hasta=None):
    """
    Genera un PDF con todos los movimientos y saldo acumulado
    Similar a un extracto bancario
    """
    from core.models import Movimiento
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.75*inch)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#6366f1'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#4f46e5'),
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER
    )
    
    # Encabezado
    title = Paragraph("OIKOS - Sistema de Gestión Financiera", title_style)
    elements.append(title)
    
    subtitle = Paragraph("Reporte de Movimientos Completo", subtitle_style)
    elements.append(subtitle)
    
    # Información de la iglesia
    periodo_texto = ""
    if fecha_desde and fecha_hasta:
        periodo_texto = f"Período: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
    elif fecha_desde:
        periodo_texto = f"Desde: {fecha_desde.strftime('%d/%m/%Y')}"
    elif fecha_hasta:
        periodo_texto = f"Hasta: {fecha_hasta.strftime('%d/%m/%Y')}"
    else:
        periodo_texto = "Todos los movimientos"
    
    info_iglesia = Paragraph(
        f"<b>{iglesia.nombre}</b><br/>"
        f"{iglesia.direccion if iglesia.direccion else ''}<br/>"
        f"{periodo_texto}",
        info_style
    )
    elements.append(info_iglesia)
    
    # Fecha de generación
    fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
    info_generacion = Paragraph(
        f"<i>Generado: {fecha_generacion}</i>",
        ParagraphStyle('small', parent=info_style, fontSize=8, textColor=colors.HexColor('#9ca3af'))
    )
    elements.append(info_generacion)
    elements.append(Spacer(1, 20))
    
    # Obtener movimientos ordenados por fecha
    movimientos = Movimiento.objects.filter(iglesia=iglesia, anulado=False)
    
    if fecha_desde:
        movimientos = movimientos.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        movimientos = movimientos.filter(fecha__lte=fecha_hasta)
    
    movimientos = movimientos.order_by('fecha', 'id')
    
    # Tabla de movimientos
    data = [['Fecha', 'Tipo', 'Categoría', 'Concepto', 'Monto', 'Saldo']]
    
    saldo_acumulado = Decimal('0.00')
    
    for mov in movimientos:
        # Calcular saldo acumulado
        if mov.tipo == 'INGRESO':
            saldo_acumulado += mov.monto
        else:  # EGRESO
            saldo_acumulado -= mov.monto
        
        # Obtener categoría
        categoria = mov.categoria_ingreso.nombre if mov.categoria_ingreso else mov.categoria_egreso.nombre
        
        # Formatear monto con signo
        monto_formateado = formato_pesos(mov.monto) if mov.tipo == 'INGRESO' else f"-{formato_pesos(mov.monto)}"
        
        # Truncar concepto si es muy largo
        concepto = mov.concepto[:40] + '...' if len(mov.concepto) > 40 else mov.concepto
        
        data.append([
            mov.fecha.strftime('%d/%m/%Y'),
            mov.get_tipo_display(),
            categoria,
            concepto,
            monto_formateado,
            formato_pesos(saldo_acumulado)
        ])
    
    # Si no hay movimientos
    if len(data) == 1:
        data.append(['', '', 'No hay movimientos registrados', '', '', ''])
    
    # Crear tabla
    tabla = Table(data, colWidths=[0.9*inch, 0.8*inch, 1.2*inch, 2.2*inch, 1.0*inch, 1.0*inch])
    
    # Estilo de la tabla
    tabla.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Fecha centrada
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Tipo centrado
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),   # Monto a la derecha
        ('ALIGN', (5, 1), (5, -1), 'RIGHT'),   # Saldo a la derecha
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        
        # Líneas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#4f46e5')),
        
        # Alternar colores de filas
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
    ]))
    
    elements.append(tabla)
    
    # Resumen final
    elements.append(Spacer(1, 20))
    
    resumen_style = ParagraphStyle(
        'ResumenStyle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1f2937'),
        alignment=TA_RIGHT
    )
    
    resumen = Paragraph(f"<b>SALDO FINAL: {formato_pesos(saldo_acumulado)}</b>", resumen_style)
    elements.append(resumen)
    
    # Construir PDF
    doc.build(elements)

    buffer.seek(0)
    return buffer


def generar_dashboard_pdf(iglesia, mes_seleccionado=None):
    """
    Genera un PDF del dashboard con gráficas, KPIs y saldos de cajas chicas
    """
    import matplotlib
    matplotlib.use('Agg')  # Backend sin interfaz gráfica
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from reportlab.platypus import Image, PageBreak
    import tempfile
    import os

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.75*inch)
    elements = []

    styles = getSampleStyleSheet()

    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#6366f1'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#4f46e5'),
        spaceAfter=15,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )

    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )

    # Encabezado
    title = Paragraph("OIKOS - Sistema de Gestión Financiera", title_style)
    elements.append(title)

    subtitle = Paragraph(f"Dashboard Financiero - {iglesia.nombre}", subtitle_style)
    elements.append(subtitle)

    # Fecha actual
    fecha_actual = datetime.now()
    if not mes_seleccionado:
        mes_seleccionado = fecha_actual.strftime('%Y-%m')

    año, mes = mes_seleccionado.split('-')
    fecha_sel = datetime(int(año), int(mes), 1)
    mes_nombre = formato_mes(fecha_sel, corto=False)

    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER,
        spaceAfter=20
    )

    fecha_info = Paragraph(
        f"Reporte generado el {fecha_actual.strftime('%d/%m/%Y %H:%M')} | Período analizado: {mes_nombre}",
        info_style
    )
    elements.append(fecha_info)

    # Obtener datos del dashboard
    from core.models import Movimiento, CajaChica
    from django.db.models import Sum
    from calendar import monthrange

    # Calcular fecha límite: último día del mes seleccionado
    año_int, mes_int = int(año), int(mes)
    ultimo_dia = monthrange(año_int, mes_int)[1]
    fecha_limite = datetime(año_int, mes_int, ultimo_dia, 23, 59, 59)

    # Calcular saldo total hasta el último día del mes seleccionado
    total_ingresos_historico = Movimiento.objects.filter(
        iglesia=iglesia,
        tipo='INGRESO',
        anulado=False,
        fecha__lte=fecha_limite
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    total_egresos_historico = Movimiento.objects.filter(
        iglesia=iglesia,
        tipo='EGRESO',
        anulado=False,
        fecha__lte=fecha_limite
    ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    saldo_final = total_ingresos_historico - total_egresos_historico

    # Totales del mes seleccionado
    movimientos_mes = Movimiento.objects.filter(
        iglesia=iglesia,
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

    balance_mes = total_ingresos_mes - total_egresos_mes

    # Tabla de KPIs principales
    elements.append(Paragraph("Resumen Financiero", section_style))

    kpi_data = [
        ['CONCEPTO', 'MONTO'],
        [f'Saldo Total al {ultimo_dia}/{mes}/{año}', formato_pesos(saldo_final)],
        [f'Ingresos {mes_nombre}', formato_pesos(total_ingresos_mes)],
        [f'Egresos {mes_nombre}', formato_pesos(total_egresos_mes)],
        [f'Balance {mes_nombre}', formato_pesos(balance_mes)],
    ]

    kpi_table = Table(kpi_data, colWidths=[4*inch, 2*inch])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#dbeafe')),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 12),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 2), (-1, -1), 10),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))

    elements.append(kpi_table)
    elements.append(Spacer(1, 20))

    # Cajas Chicas
    cajas_chicas = CajaChica.objects.filter(iglesia=iglesia, activa=True).order_by('nombre')

    if cajas_chicas.exists():
        elements.append(Paragraph(f"Saldos de Cajas Chicas al {ultimo_dia}/{mes}/{año}", section_style))

        from core.models import MovimientoCajaChica
        caja_data = [['CAJA CHICA', 'SALDO']]
        total_cajas = Decimal('0.00')

        for caja in cajas_chicas:
            # Calcular saldo de la caja hasta la fecha límite
            ingresos_caja = MovimientoCajaChica.objects.filter(
                caja_chica=caja,
                tipo='INGRESO',
                anulado=False,
                fecha__lte=fecha_limite
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            egresos_caja = MovimientoCajaChica.objects.filter(
                caja_chica=caja,
                tipo='EGRESO',
                anulado=False,
                fecha__lte=fecha_limite
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            # Incluir transferencias hasta la fecha límite
            from core.models import TransferenciaCajaChica
            transferencias_recibidas = TransferenciaCajaChica.objects.filter(
                caja_destino=caja,
                anulada=False,
                fecha__lte=fecha_limite
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            transferencias_enviadas = TransferenciaCajaChica.objects.filter(
                caja_origen=caja,
                anulada=False,
                fecha__lte=fecha_limite
            ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

            saldo_caja = caja.saldo_inicial + ingresos_caja - egresos_caja + transferencias_recibidas - transferencias_enviadas
            total_cajas += saldo_caja
            caja_data.append([caja.nombre, formato_pesos(saldo_caja)])

        caja_data.append(['TOTAL CAJAS CHICAS', formato_pesos(total_cajas)])

        caja_table = Table(caja_data, colWidths=[4*inch, 2*inch])
        caja_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 10),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d1fae5')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
        ]))

        elements.append(caja_table)
        elements.append(Spacer(1, 20))

    # Obtener datos para gráficas
    dashboard_data = get_dashboard_data(iglesia, mes_distribucion=mes_seleccionado)

    # Configurar matplotlib para español y mejor visualización
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['xtick.labelsize'] = 9
    plt.rcParams['ytick.labelsize'] = 9
    plt.rcParams['legend.fontsize'] = 9

    # Crear archivo temporal para las gráficas
    temp_files = []

    try:
        # Gráfica 1: Evolución de Saldos
        elements.append(PageBreak())
        elements.append(Paragraph("Evolución de Saldos", section_style))

        fig1, ax1 = plt.subplots(figsize=(8, 4))

        ax1.plot(dashboard_data['meses_labels'], dashboard_data['saldos_data'],
                marker='o', linewidth=2, color='#6366f1', markersize=6, label='Saldo')
        ax1.fill_between(range(len(dashboard_data['meses_labels'])), dashboard_data['saldos_data'],
                         alpha=0.2, color='#6366f1')

        ax1.set_xlabel('Mes')
        ax1.set_ylabel('Saldo ($)')
        ax1.set_title('Evolución del Saldo Total')
        ax1.set_xticks(range(len(dashboard_data['meses_labels'])))
        ax1.set_xticklabels(dashboard_data['meses_labels'], rotation=45, ha='right')
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)

        # Formatear eje Y con separador de miles
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        plt.tight_layout()

        temp1 = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_files.append(temp1.name)
        fig1.savefig(temp1.name, dpi=150, bbox_inches='tight')
        plt.close(fig1)

        img1 = Image(temp1.name, width=6.5*inch, height=3.25*inch)
        elements.append(img1)
        elements.append(Spacer(1, 15))

        # Gráfica 2: Evolución de Ingresos y Egresos (líneas)
        elements.append(Paragraph("Evolución de Ingresos y Egresos", section_style))

        fig2, ax2 = plt.subplots(figsize=(8, 4))

        ax2.plot(dashboard_data['meses_labels'], dashboard_data['ingresos_data'],
                marker='o', linewidth=2, color='#10b981', markersize=6, label='Ingresos')
        ax2.plot(dashboard_data['meses_labels'], dashboard_data['egresos_data'],
                marker='o', linewidth=2, color='#ef4444', markersize=6, label='Egresos')

        ax2.set_xlabel('Mes')
        ax2.set_ylabel('Monto ($)')
        ax2.set_title('Ingresos vs Egresos por Mes')
        ax2.set_xticks(range(len(dashboard_data['meses_labels'])))
        ax2.set_xticklabels(dashboard_data['meses_labels'], rotation=45, ha='right')
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)

        # Formatear eje Y con separador de miles
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        plt.tight_layout()

        temp2 = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_files.append(temp2.name)
        fig2.savefig(temp2.name, dpi=150, bbox_inches='tight')
        plt.close(fig2)

        img2 = Image(temp2.name, width=6.5*inch, height=3.25*inch)
        elements.append(img2)
        elements.append(Spacer(1, 15))

        # Gráfica 3: Balance Mensual
        elements.append(Paragraph("Balance Mensual", section_style))

        fig3, ax3 = plt.subplots(figsize=(8, 4))
        colors_balance = ['#10b981' if b >= 0 else '#ef4444' for b in dashboard_data['balance_data']]

        ax3.bar(dashboard_data['meses_labels'], dashboard_data['balance_data'],
                color=colors_balance, alpha=0.8)
        ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax3.set_xlabel('Mes')
        ax3.set_ylabel('Balance ($)')
        ax3.set_title('Balance Mensual (Ingresos - Egresos)')
        ax3.set_xticklabels(dashboard_data['meses_labels'], rotation=45, ha='right')
        ax3.grid(axis='y', alpha=0.3)
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        plt.tight_layout()

        temp3 = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        temp_files.append(temp3.name)
        fig3.savefig(temp3.name, dpi=150, bbox_inches='tight')
        plt.close(fig3)

        img3 = Image(temp3.name, width=6.5*inch, height=3.25*inch)
        elements.append(img3)
        elements.append(Spacer(1, 15))

        # Gráfica 4: Distribución de Egresos por Categoría (Dona)
        if dashboard_data['categorias_labels'] and dashboard_data['categorias_data']:
            elements.append(PageBreak())
            elements.append(Paragraph(f"Distribución de Egresos por Categoría - {mes_nombre}", section_style))

            fig4, ax4 = plt.subplots(figsize=(8, 6))

            # Tomar solo las top 10 categorías
            top_n = 10
            if len(dashboard_data['categorias_labels']) > top_n:
                labels = dashboard_data['categorias_labels'][:top_n]
                data = dashboard_data['categorias_data'][:top_n]
                otros = sum(dashboard_data['categorias_data'][top_n:])
                if otros > 0:
                    labels.append('Otros')
                    data.append(otros)
            else:
                labels = dashboard_data['categorias_labels']
                data = dashboard_data['categorias_data']

            # Colores para el gráfico de dona
            colors_dona = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff', '#ff9f40',
                          '#ff6384', '#c9cbcf', '#4bc0c0', '#ff6384', '#36a2eb']

            # Calcular porcentajes
            total = sum(data)
            percentages = [(value / total * 100) if total > 0 else 0 for value in data]

            # Crear gráfico de dona
            wedges, texts, autotexts = ax4.pie(data, labels=None, autopct='%1.1f%%',
                                                colors=colors_dona[:len(data)], startangle=90,
                                                pctdistance=0.85, wedgeprops=dict(width=0.5))

            ax4.set_title('Distribución de Egresos por Categoría')

            # Mejorar el formato de los porcentajes
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(9)
                autotext.set_weight('bold')

            # Crear leyenda con nombres y porcentajes
            legend_labels = [f'{label}: {pct:.1f}%' for label, pct in zip(labels, percentages)]
            ax4.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1),
                      fontsize=9)

            plt.tight_layout()

            temp4 = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_files.append(temp4.name)
            fig4.savefig(temp4.name, dpi=150, bbox_inches='tight')
            plt.close(fig4)

            img4 = Image(temp4.name, width=6.5*inch, height=4.5*inch)
            elements.append(img4)
            elements.append(Spacer(1, 15))

        # Construir PDF
        doc.build(elements)

    finally:
        # Limpiar archivos temporales
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

    buffer.seek(0)
    return buffer
