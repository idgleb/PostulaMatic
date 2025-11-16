#!/bin/bash
# Script para limpiar automáticamente Docker y liberar espacio

echo "🧹 Iniciando limpieza automática de Docker..."
echo ""

# Verificar espacio en disco antes
echo "📊 Espacio en disco ANTES de la limpieza:"
df -h / | grep -E "Filesystem|/dev/"
echo ""

# Obtener estadísticas de Docker
echo "📦 Estadísticas de Docker:"
docker system df
echo ""

# Limpiar contenedores detenidos
echo "🗑️ Limpiando contenedores detenidos..."
docker container prune -f

# Limpiar imágenes no usadas (sin eliminar las activas)
echo "🗑️ Limpiando imágenes no usadas..."
docker image prune -a -f

# Limpiar volúmenes no usados
echo "🗑️ Limpiando volúmenes no usados..."
docker volume prune -f

# Limpiar build cache
echo "🗑️ Limpiando build cache..."
docker builder prune -f

echo ""
echo "📊 Espacio en disco DESPUÉS de la limpieza:"
df -h / | grep -E "Filesystem|/dev/"
echo ""

echo "✅ Limpieza completada"

