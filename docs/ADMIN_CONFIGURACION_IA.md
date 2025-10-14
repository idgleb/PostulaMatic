# 🤖 Guía de Configuración de IA para Administradores

## 📋 **Resumen**

Los administradores pueden configurar las API Keys de IA directamente desde la interfaz web, sin necesidad de editar archivos o reiniciar contenedores.

## 🚀 **Acceso a la Configuración**

### **1. Hacer Login como Administrador**
```
URL: http://localhost:8000/matching/login/
Usuario: admin
Contraseña: admin123
```

### **2. Acceder a Configuración de IA**
- **Opción A**: Hacer clic en tu nombre (dropdown) → "Configurar IA"
- **Opción B**: Ir directamente a: `http://localhost:8000/matching/admin/ai-config/`

## 🔧 **Configuración de Proveedores**

### **Interfaz de Configuración**

La interfaz muestra:
- ✅ **Estado actual** de cada proveedor
- 🔧 **Formulario de configuración** para ambos proveedores
- 🧪 **Botones de prueba** para verificar conectividad
- 📚 **Guía de configuración** integrada

### **Configurar OpenAI**

1. **Habilitar OpenAI**: Marcar checkbox "Habilitar OpenAI"
2. **Seleccionar Modelo**:
   - `GPT-3.5 Turbo` (Recomendado - Económico)
   - `GPT-4` (Mejor calidad - Más caro)
   - `GPT-4 Turbo` (Balanceado)
3. **Ingresar API Key**:
   - Ir a [OpenAI Platform](https://platform.openai.com/api-keys)
   - Crear nueva API key
   - Copiar clave que empieza con `sk-`
   - Pegar en el campo "API Key"

### **Configurar Anthropic**

1. **Habilitar Anthropic**: Marcar checkbox "Habilitar Anthropic"
2. **Seleccionar Modelo**:
   - `Claude 3 Haiku` (Rápido - Económico)
   - `Claude 3 Sonnet` (Balanceado)
   - `Claude 3 Opus` (Mejor calidad - Más caro)
3. **Ingresar API Key**:
   - Ir a [Anthropic Console](https://console.anthropic.com/)
   - Crear nueva API key
   - Copiar clave que empieza con `sk-ant-`
   - Pegar en el campo "API Key"

### **Configuración General**

- **Proveedor por Defecto**: Seleccionar cuál usar cuando no se especifique uno
- **Guardar Configuración**: Hacer clic en "Guardar Configuración"

## 🧪 **Probar Conectividad**

### **Probar Proveedores Individuales**
- Cada proveedor tiene un botón "Probar" individual
- Se envía un mensaje de prueba y se muestra la respuesta

### **Probar Todos los Proveedores**
- Botón "Probar Todos" ejecuta pruebas en paralelo
- Muestra resultados para cada proveedor configurado

### **Interpretar Resultados**

**✅ Conectividad Exitosa:**
- Muestra la respuesta del modelo
- Incluye tokens usados (si aplica)
- Indica que el proveedor está funcionando

**❌ Error de Conectividad:**
- Muestra el mensaje de error específico
- Indica problemas de configuración o red

## 🔐 **Seguridad**

### **Encriptación Automática**
- Las API keys se almacenan **encriptadas** en la base de datos
- Se usa el módulo `cryptography.fernet` para encriptación
- La clave de encriptación se genera automáticamente

### **Acceso Restringido**
- Solo usuarios con `is_staff=True` pueden acceder
- Decorador `@staff_member_required` protege las vistas
- El enlace solo aparece para administradores

### **Logs de Seguridad**
- Todas las operaciones se registran en logs
- No se almacenan API keys en texto plano
- Errores de encriptación se registran

## 📊 **Monitoreo**

### **Estado en Tiempo Real**
- La página muestra el estado actual de cada proveedor
- Preview de las API keys (primeros caracteres)
- Indicadores visuales de estado (✅/⚠️)

### **Verificar Configuración**
```bash
# Ver estado desde terminal
docker compose exec postulamatic_web python manage.py shell -c "
from matching.models import AIConfiguration
config = AIConfiguration.get_config()
print(f'OpenAI: {\"✅\" if config.openai_enabled else \"❌\"}')
print(f'Anthropic: {\"✅\" if config.anthropic_enabled else \"❌\"}')
print(f'Proveedores disponibles: {config.get_available_providers()}')
"
```

## 🚨 **Troubleshooting**

### **Error: "No tienes permisos"**
✅ **Solución**: Asegúrate de estar logueado como usuario con `is_staff=True`

### **Error: "API Key inválida"**
✅ **Solución**: 
1. Verifica que la API key sea correcta
2. Asegúrate de que no tenga espacios al inicio/final
3. Para OpenAI, verifica que tengas créditos disponibles

### **Error: "Proveedor no configurado"**
✅ **Solución**:
1. Asegúrate de marcar "Habilitar [Proveedor]"
2. Ingresa una API key válida
3. Guarda la configuración

### **Error de Encriptación**
✅ **Solución**:
1. Verifica que el módulo `cryptography` esté instalado
2. Revisa los logs para más detalles
3. Las keys se almacenan sin encriptar como fallback

## 🔄 **Actualización del Sistema**

### **Cambios Automáticos**
- Los cambios se aplican **inmediatamente**
- No es necesario reiniciar contenedores
- El sistema usa lazy loading para la configuración

### **Invalidar Cache**
Si los cambios no se reflejan:
```bash
# Reiniciar worker para limpiar cache
docker compose restart worker
```

## 📈 **Beneficios del Sistema**

### **Para Administradores**
- ✅ **Interfaz web intuitiva** - No más edición de archivos
- ✅ **Configuración segura** - API keys encriptadas
- ✅ **Pruebas integradas** - Verificar conectividad fácilmente
- ✅ **Cambios inmediatos** - Sin reinicios necesarios

### **Para Usuarios**
- ✅ **Transparencia** - Ver estado de proveedores
- ✅ **Confiabilidad** - Sistema robusto con fallbacks
- ✅ **Flexibilidad** - Múltiples proveedores disponibles

### **Para el Sistema**
- ✅ **Escalabilidad** - Fácil agregar nuevos proveedores
- ✅ **Mantenibilidad** - Configuración centralizada
- ✅ **Observabilidad** - Logs detallados de todas las operaciones

## 🎯 **Próximos Pasos**

1. **Configurar al menos un proveedor** (OpenAI o Anthropic)
2. **Probar conectividad** con el botón de prueba
3. **Verificar funcionamiento** en la página de generación de emails
4. **Monitorear logs** para detectar problemas

---

**¡Con esta interfaz, los administradores pueden configurar IA de forma segura y eficiente!** 🚀✨
