from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Iglesia, CategoriaIngreso, CategoriaEgreso, Movimiento
from datetime import datetime, timedelta
from decimal import Decimal
import random

Usuario = get_user_model()


class Command(BaseCommand):
    help = 'Setup inicial de OIKOS con datos de ejemplo'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('=== OIKOS - Setup Inicial ===\n'))

        # 1. Crear superusuario
        if not Usuario.objects.filter(username='admin').exists():
            # Primero crear iglesia demo
            iglesia_demo, created = Iglesia.objects.get_or_create(
                nombre='Iglesia Ejemplo',
                defaults={
                    'direccion': 'Calle Principal 123',
                    'telefono': '011-4444-5555',
                    'email': 'contacto@iglesiaejemplo.org',
                    'activa': True
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Iglesia creada: {iglesia_demo.nombre}'))
            else:
                self.stdout.write(self.style.WARNING(f'○ Iglesia ya existente: {iglesia_demo.nombre}'))

            # Crear superusuario
            admin = Usuario.objects.create_superuser(
                username='admin',
                email='admin@oikos.com',
                password='admin',
                first_name='Admin',
                last_name='OIKOS',
                iglesia=iglesia_demo,
                rol='ADMIN',
                puede_aprobar=True
            )
            self.stdout.write(self.style.SUCCESS('✓ Superusuario creado: admin/admin'))
        else:
            self.stdout.write(self.style.WARNING('○ Superusuario ya existe'))
            admin = Usuario.objects.get(username='admin')
            iglesia_demo = admin.iglesia

        # 2. Verificar categorías (se crean automáticamente por señal)
        categorias_ingreso = CategoriaIngreso.objects.filter(iglesia=iglesia_demo).count()
        categorias_egreso = CategoriaEgreso.objects.filter(iglesia=iglesia_demo).count()

        self.stdout.write(self.style.SUCCESS(f'✓ Categorías de ingreso: {categorias_ingreso}'))
        self.stdout.write(self.style.SUCCESS(f'✓ Categorías de egreso: {categorias_egreso}'))

        # 3. Crear movimientos de ejemplo (últimos 3 meses)
        if not Movimiento.objects.filter(iglesia=iglesia_demo).exists():
            fecha_actual = datetime.now()

            # Obtener categorías
            cat_diezmo = CategoriaIngreso.objects.get(iglesia=iglesia_demo, codigo='DIEZMO')
            cat_ofrenda = CategoriaIngreso.objects.get(iglesia=iglesia_demo, codigo='OFRENDA')
            cat_donacion = CategoriaIngreso.objects.get(iglesia=iglesia_demo, codigo='DONACION')

            cat_alquiler = CategoriaEgreso.objects.get(iglesia=iglesia_demo, codigo='ALQUILER')
            cat_servicios = CategoriaEgreso.objects.get(iglesia=iglesia_demo, codigo='SERVICIOS')
            cat_misiones = CategoriaEgreso.objects.get(iglesia=iglesia_demo, codigo='MISIONES')
            cat_mantenimiento = CategoriaEgreso.objects.get(iglesia=iglesia_demo, codigo='MANTENIMIENTO')

            movimientos_creados = 0

            # Generar movimientos para los últimos 3 meses
            for mes in range(3):
                fecha_mes = fecha_actual - timedelta(days=30 * mes)

                # Ingresos del mes
                ingresos_mes = [
                    {
                        'categoria': cat_diezmo,
                        'concepto': f'Diezmos mes {fecha_mes.strftime("%B %Y")}',
                        'monto': Decimal(random.randint(800000, 1200000))
                    },
                    {
                        'categoria': cat_diezmo,
                        'concepto': f'Diezmos especiales {fecha_mes.strftime("%B %Y")}',
                        'monto': Decimal(random.randint(200000, 400000))
                    },
                    {
                        'categoria': cat_ofrenda,
                        'concepto': f'Ofrendas dominicales {fecha_mes.strftime("%B %Y")}',
                        'monto': Decimal(random.randint(150000, 300000))
                    },
                    {
                        'categoria': cat_donacion,
                        'concepto': f'Donación anónima {fecha_mes.strftime("%B %Y")}',
                        'monto': Decimal(random.randint(50000, 150000))
                    },
                ]

                for ingreso in ingresos_mes:
                    Movimiento.objects.create(
                        iglesia=iglesia_demo,
                        tipo='INGRESO',
                        fecha=fecha_mes - timedelta(days=random.randint(1, 25)),
                        categoria_ingreso=ingreso['categoria'],
                        concepto=ingreso['concepto'],
                        monto=ingreso['monto'],
                        creado_por=admin,
                        aprobado_por=admin
                    )
                    movimientos_creados += 1

                # Egresos del mes
                egresos_mes = [
                    {
                        'categoria': cat_alquiler,
                        'concepto': f'Alquiler local {fecha_mes.strftime("%B %Y")}',
                        'monto': Decimal(450000)
                    },
                    {
                        'categoria': cat_servicios,
                        'concepto': f'Luz, gas y agua {fecha_mes.strftime("%B %Y")}',
                        'monto': Decimal(random.randint(80000, 120000))
                    },
                    {
                        'categoria': cat_misiones,
                        'concepto': f'Apoyo misionero {fecha_mes.strftime("%B %Y")}',
                        'monto': Decimal(random.randint(100000, 200000))
                    },
                    {
                        'categoria': cat_mantenimiento,
                        'concepto': f'Reparaciones varias {fecha_mes.strftime("%B %Y")}',
                        'monto': Decimal(random.randint(50000, 150000))
                    },
                ]

                for egreso in egresos_mes:
                    Movimiento.objects.create(
                        iglesia=iglesia_demo,
                        tipo='EGRESO',
                        fecha=fecha_mes - timedelta(days=random.randint(1, 25)),
                        categoria_egreso=egreso['categoria'],
                        concepto=egreso['concepto'],
                        monto=egreso['monto'],
                        comprobante_nro=f'FC-{random.randint(1000, 9999)}',
                        creado_por=admin,
                        aprobado_por=admin
                    )
                    movimientos_creados += 1

            self.stdout.write(self.style.SUCCESS(f'✓ Movimientos de ejemplo creados: {movimientos_creados}'))
        else:
            self.stdout.write(self.style.WARNING('○ Ya existen movimientos en la base de datos'))

        # Resumen final
        self.stdout.write(self.style.SUCCESS('\n=== Setup completado exitosamente ==='))
        self.stdout.write(self.style.SUCCESS('OIKOS está listo para usar!'))
        self.stdout.write(self.style.SUCCESS('\nCredenciales:'))
        self.stdout.write(self.style.SUCCESS('  Usuario: admin'))
        self.stdout.write(self.style.SUCCESS('  Contraseña: admin'))
        self.stdout.write(self.style.SUCCESS('\nAccede al sistema en: http://localhost:8000'))
        self.stdout.write(self.style.SUCCESS('Panel admin en: http://localhost:8000/admin/\n'))
