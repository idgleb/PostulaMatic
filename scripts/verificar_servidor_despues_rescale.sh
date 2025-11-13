#!/bin/bash
# Script para verificar y reiniciar servicios después de un rescale en Hetzner

SSH_KEY="${HOME}/.ssh/postulamatic_win_ed25519"
SERVER="deploy@178.156.188.95"

echo "🔍 Verificando estado del servidor después del rescale..."
echo ""

ssh -i "$SSH_KEY" "$SERVER" << 'EOF'
echo "📋 Información del sistema:"
echo "=========================="
echo "CPU: $(nproc) vCPU"
echo "RAM: $(free -h | grep Mem | awk '{print $2}')"
echo "Uptime: $(uptime -p)"
echo ""

echo "🐳 Estado de Docker:"
echo "===================="
if systemctl is-active --quiet docker; then
    echo "✅ Docker está corriendo"
else
    echo "❌ Docker NO está corriendo - iniciando..."
    sudo systemctl start docker
    sleep 3
fi
echo ""

echo "📦 Contenedores Docker:"
echo "======================"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "🌐 Estado de Nginx:"
echo "=================="
if docker ps | grep -q nginx-proxy; then
    echo "✅ Nginx está corriendo"
    docker exec nginx-proxy nginx -t 2>&1 | head -2
else
    echo "❌ Nginx NO está corriendo"
fi
echo ""

echo "🚀 Reiniciando servicios de PostulaMatic..."
echo "==========================================="
cd /home/deploy/apps/postulamatic

# Verificar que docker-compose.yml existe
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml no encontrado"
    exit 1
fi

# Iniciar servicios
echo "Iniciando contenedores..."
docker compose up -d

# Esperar a que los contenedores se inicien
echo "Esperando 10 segundos para que los contenedores se inicien..."
sleep 10

# Verificar estado
echo ""
echo "📊 Estado final de contenedores:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "🔍 Verificando logs de errores..."
echo "=================================="
docker compose logs --tail=20 postulamatic_web 2>&1 | grep -i error | head -5 || echo "✅ No se encontraron errores recientes"
echo ""

echo "🌐 Verificando conectividad..."
echo "=============================="
if curl -f -s http://localhost:8000 > /dev/null 2>&1; then
    echo "✅ Django responde en localhost:8000"
else
    echo "❌ Django NO responde en localhost:8000"
fi

if docker exec nginx-proxy curl -f -s http://postulamatic_web:8000 > /dev/null 2>&1; then
    echo "✅ Nginx puede conectarse a Django"
else
    echo "❌ Nginx NO puede conectarse a Django"
fi
echo ""

echo "📋 Verificando puertos:"
echo "======================"
netstat -tlnp 2>/dev/null | grep -E ':(80|443|8000)' || ss -tlnp | grep -E ':(80|443|8000)'
echo ""

echo "✅ Verificación completada"
echo ""
echo "💡 Si el sitio aún no funciona, verifica:"
echo "   1. Que Nginx esté corriendo: docker ps | grep nginx"
echo "   2. Que Django esté corriendo: docker ps | grep postulamatic"
echo "   3. Los logs: docker compose logs postulamatic_web"
echo "   4. La configuración de Nginx: docker exec nginx-proxy nginx -t"

EOF

echo ""
echo "✅ Script completado"
echo ""
echo "🌐 Verifica el sitio: https://postulamatic.app"

