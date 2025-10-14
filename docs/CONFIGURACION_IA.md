# 🤖 Guía de Configuración de IA para PostulaMatic

## 📋 **Resumen**

PostulaMatic soporta dos proveedores de IA para generar emails personalizados:
- **OpenAI** (GPT-3.5-turbo, GPT-4)
- **Anthropic** (Claude-3-haiku, Claude-3-sonnet)

## 🚀 **Configuración Rápida**

### **Opción 1: Script Automático**
```bash
# Ejecutar el script de configuración
docker compose exec postulamatic_web python scripts/configure_ai_keys.py
```

### **Opción 2: Configuración Manual**

#### **1. Obtener API Keys**

**Para OpenAI:**
1. Ve a [OpenAI Platform](https://platform.openai.com/api-keys)
2. Crea una cuenta o inicia sesión
3. Haz clic en "Create new secret key"
4. Copia la API key (empieza con `sk-`)

**Para Anthropic:**
1. Ve a [Anthropic Console](https://console.anthropic.com/)
2. Crea una cuenta o inicia sesión
3. Ve a "API Keys"
4. Haz clic en "Create Key"
5. Copia la API key (empieza con `sk-ant-`)

#### **2. Configurar Variables de Entorno**

Crea o edita el archivo `.env` en la raíz del proyecto:

```bash
# OpenAI
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Proveedor por defecto
AI_PROVIDER=openai
```

#### **3. Reiniciar Contenedores**
```bash
docker compose restart
```

## 🔍 **Verificar Configuración**

### **1. Página de Estado**
```
URL: http://localhost:8000/matching/ai-providers-status/
```

### **2. Comando de Terminal**
```bash
# Verificar estado
docker compose exec postulamatic_web python -c "
import os
print('OpenAI:', 'CONFIGURADA' if os.getenv('OPENAI_API_KEY') else 'NO CONFIGURADA')
print('Anthropic:', 'CONFIGURADA' if os.getenv('ANTHROPIC_API_KEY') else 'NO CONFIGURADA')
"
```

### **3. Probar Conectividad**
```bash
# Probar OpenAI
docker compose exec postulamatic_web python manage.py test_ai_integration --provider=openai

# Probar Anthropic
docker compose exec postulamatic_web python manage.py test_ai_integration --provider=anthropic
```

## 🧪 **Pruebas del Sistema**

### **1. Generar Email de Prueba**
```
URL: http://localhost:8000/matching/email-generation-test/
```

### **2. Comando de Terminal**
```bash
# Probar sistema completo
docker compose exec postulamatic_web python manage.py test_email_system --test-type=single
```

## 📊 **Monitoreo y Logs**

### **Ver Logs de IA**
```bash
# Logs del worker (incluye generación de emails)
docker compose logs worker --tail 50

# Logs específicos de IA
docker compose logs worker | grep -i "ai\|openai\|anthropic"
```

### **Dashboard de Monitoreo**
```
URL: http://localhost:8000/matching/email-monitoring/
```

## 🚨 **Troubleshooting**

### **Error: "API Key no configurada"**
✅ **Solución:**
1. Verifica que la API key esté en el archivo `.env`
2. Reinicia los contenedores: `docker compose restart`
3. Verifica en la página de estado de IA

### **Error: "Invalid API Key"**
✅ **Solución:**
1. Verifica que la API key sea correcta
2. Asegúrate de que no tenga espacios al inicio/final
3. Para OpenAI, verifica que tenga créditos disponibles

### **Error: "Rate limit exceeded"**
✅ **Solución:**
1. Espera unos minutos antes de reintentar
2. Considera usar un modelo más económico (gpt-3.5-turbo vs gpt-4)
3. Verifica tu límite de uso en la plataforma

### **Error: "Connection timeout"**
✅ **Solución:**
1. Verifica tu conexión a internet
2. Verifica que no haya firewall bloqueando las conexiones
3. Intenta con el otro proveedor

## 💡 **Consejos de Uso**

### **Modelos Recomendados**

**Para uso general:**
- OpenAI: `gpt-3.5-turbo` (más económico)
- Anthropic: `claude-3-haiku-20240307` (más rápido)

**Para calidad superior:**
- OpenAI: `gpt-4` (más caro, mejor calidad)
- Anthropic: `claude-3-sonnet-20240229` (balanceado)

### **Configuración de Fallback**
El sistema usa automáticamente el otro proveedor si uno falla:
1. Intenta con el proveedor configurado en `AI_PROVIDER`
2. Si falla, intenta con el otro proveedor disponible
3. Si ambos fallan, devuelve error

### **Optimización de Costos**
- Usa `gpt-3.5-turbo` para emails simples
- Usa `claude-3-haiku` para respuestas rápidas
- Reserva modelos premium para casos especiales

## 📈 **Monitoreo de Uso**

### **Verificar Uso de Tokens**
```bash
# En los logs del worker
docker compose logs worker | grep -i "tokens"
```

### **Estadísticas de Uso**
```
URL: http://localhost:8000/matching/email-analytics/
```

## 🔐 **Seguridad**

### **Buenas Prácticas**
1. **Nunca** commits las API keys al repositorio
2. Usa archivos `.env` que estén en `.gitignore`
3. Rota las API keys periódicamente
4. Monitorea el uso de tus cuentas de IA

### **Variables Sensibles**
```bash
# Verificar que no estén en el repositorio
git status
git diff --cached | grep -i "api.*key"
```

## 🆘 **Soporte**

### **Comandos de Diagnóstico**
```bash
# Estado completo del sistema
docker compose exec postulamatic_web python manage.py check

# Verificar configuración de IA
docker compose exec postulamatic_web python manage.py shell -c "
from matching.services.ai_service import ai_email_service
print('Proveedores disponibles:', ai_email_service.get_available_providers())
"

# Verificar conectividad
docker compose exec postulamatic_web python scripts/configure_ai_keys.py
```

### **Logs Útiles**
```bash
# Todos los logs
docker compose logs --tail 100

# Solo errores
docker compose logs | grep -i "error\|exception"

# Solo IA
docker compose logs | grep -i "openai\|anthropic\|ai"
```

---

**¡Con esta configuración tendrás el sistema de IA completamente funcional!** 🚀✨
