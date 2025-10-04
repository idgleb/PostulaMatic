#!/bin/bash

# Script de health check para PostulaMatic

SITE_URL="https://postulamatic.app"
MAX_RETRIES=5
RETRY_DELAY=10

echo "🏥 Iniciando health check para $SITE_URL..."

for i in $(seq 1 $MAX_RETRIES); do
    echo "Intento $i/$MAX_RETRIES..."
    
    # Verificar que el sitio responde
    if curl -f -s -I "$SITE_URL" > /dev/null 2>&1; then
        echo "✅ Sitio respondiendo correctamente"
        
        # Verificar headers importantes
        echo "📋 Verificando headers de seguridad..."
        
        # HSTS
        if curl -s -I "$SITE_URL" | grep -q "Strict-Transport-Security"; then
            echo "✅ HSTS header presente"
        else
            echo "⚠️ HSTS header no encontrado"
        fi
        
        # X-Frame-Options
        if curl -s -I "$SITE_URL" | grep -q "X-Frame-Options"; then
            echo "✅ X-Frame-Options header presente"
        else
            echo "⚠️ X-Frame-Options header no encontrado"
        fi
        
        echo "🎉 Health check exitoso"
        exit 0
    else
        echo "❌ Sitio no responde (intento $i/$MAX_RETRIES)"
        
        if [[ $i -lt $MAX_RETRIES ]]; then
            echo "⏳ Esperando $RETRY_DELAY segundos antes del siguiente intento..."
            sleep $RETRY_DELAY
        fi
    fi
done

echo "❌ Health check falló después de $MAX_RETRIES intentos"
exit 1
