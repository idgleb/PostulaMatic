#!/bin/bash
# Script para limpiar crontabs no utilizados en el servidor

echo "🧹 Limpiando crontabs no utilizados..."

# Primero mostrar qué se eliminaría (dry-run)
echo "📋 Modo dry-run - Ver qué se eliminaría:"
docker compose exec postulamatic_web python manage.py cleanup_unused_crontabs --dry-run

echo ""
echo "⚠️  ¿Deseas continuar y eliminar los crontabs no utilizados? (s/N)"
read -r response

if [[ "$response" =~ ^([sS][iI][mM]|[sS])$ ]]; then
    echo "🗑️  Eliminando crontabs no utilizados..."
    docker compose exec postulamatic_web python manage.py cleanup_unused_crontabs
    echo "✅ Limpieza completada"
else
    echo "❌ Operación cancelada"
fi

