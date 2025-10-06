#!/bin/bash

# Script para iniciar OIKOS en desarrollo

echo "==================================="
echo "    OIKOS - Iniciando Servidor    "
echo "==================================="
echo ""

# Activar entorno virtual
source venv/bin/activate

# Ejecutar servidor
echo "Servidor disponible en: http://localhost:8000"
echo "Panel admin en: http://localhost:8000/admin/"
echo ""
echo "Credenciales por defecto:"
echo "  Usuario: admin"
echo "  Contraseña: admin"
echo ""
echo "Presiona Ctrl+C para detener el servidor"
echo ""

python manage.py runserver
