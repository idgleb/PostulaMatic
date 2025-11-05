# 🤖 Selección Dinámica de Modelos de IA

## 📋 Resumen

Se ha implementado un **sistema de selección dinámica de modelos** que consulta en tiempo real los modelos disponibles en las cuentas de OpenAI y Anthropic del usuario, evitando errores de configuración por modelos inexistentes o no disponibles.

---

## 🎯 Características Implementadas

### ✅ **1. Consulta Dinámica de Modelos**

El sistema ahora consulta los modelos disponibles directamente desde las APIs de OpenAI y Anthropic:

```python
# Vista: matching/views_ai_admin.py
@staff_member_required
@require_http_methods(["GET"])
def get_available_models(request):
    """
    Consulta los modelos disponibles en OpenAI y Anthropic.
    Retorna JSON con los modelos que el usuario puede usar.
    """
    # Consulta modelos de OpenAI
    client = openai.OpenAI(api_key=config.get_openai_key())
    models_response = client.models.list()
    
    # Filtra solo modelos GPT relevantes (gpt-3.5, gpt-4, gpt-4o)
    # Ordena por fecha de creación (más reciente primero)
    
    # Consulta modelos de Anthropic
    finder = AnthropicModelFinder(api_key=config.get_anthropic_key())
    available_models = finder.get_available_models()
    
    return JsonResponse({
        'openai': {'models': [...], 'error': None},
        'anthropic': {'models': [...], 'error': None}
    })
```

---

### ✅ **2. Dropdowns Dinámicos en el Frontend**

Los dropdowns de modelos se poblan automáticamente al cargar la página:

```javascript
// templates/matching/ai_admin_config.html
function loadAvailableModels() {
    fetch('/matching/admin/get-available-models/')
        .then(response => response.json())
        .then(data => {
            // Poblar dropdown de OpenAI
            data.openai.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.name;
                openaiModelSelect.appendChild(option);
            });
            
            // Poblar dropdown de Anthropic
            data.anthropic.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = model.name;
                anthropicModelSelect.appendChild(option);
            });
        });
}

// Cargar modelos al cargar la página
loadAvailableModels();
```

---

### ✅ **3. Manejo de Errores**

Si no hay API keys configuradas o hay errores de conectividad, el sistema muestra mensajes claros:

```
❌ API Key no configurada
❌ Error: You exceeded your current quota...
⚠️ No hay modelos disponibles
```

---

## 🔍 Flujo de Funcionamiento

```
┌─────────────────────────────────────────────────────────────┐
│  🌐 Usuario accede a /matching/admin/ai-config/            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  📡 JavaScript hace fetch a /admin/get-available-models/    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  🔍 Backend consulta APIs de OpenAI y Anthropic             │
│  ├─ OpenAI: client.models.list()                            │
│  ├─ Anthropic: AnthropicModelFinder.get_available_models()  │
│  └─ Filtra y ordena modelos relevantes                      │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  📊 Backend retorna JSON con modelos disponibles            │
│  {                                                           │
│    "openai": {                                               │
│      "models": [                                             │
│        {"id": "gpt-4o-mini-2024-07-18", "name": "GPT-4o..."},│
│        {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"}     │
│      ],                                                      │
│      "error": null                                           │
│    },                                                        │
│    "anthropic": {                                            │
│      "models": [                                             │
│        {"id": "claude-sonnet-4-5-20250929", "name": "..."}  │
│      ],                                                      │
│      "error": null                                           │
│    }                                                         │
│  }                                                           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  🎨 Frontend pobla los dropdowns con modelos reales         │
│  ├─ Selecciona automáticamente el modelo actual             │
│  ├─ Muestra nombres legibles (ej: "GPT-4o Mini (gpt-4o...)")│
│  └─ Deshabilita dropdowns si no hay API key                 │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  ✅ Usuario solo puede seleccionar modelos DISPONIBLES      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Archivos Modificados

### **1. `matching/views_ai_admin.py`**
- **Nueva vista**: `get_available_models()`
- Consulta modelos de OpenAI con `client.models.list()`
- Consulta modelos de Anthropic con `AnthropicModelFinder`
- Filtra y formatea modelos para el frontend
- Maneja errores de API keys no configuradas

### **2. `matching/urls.py`**
- **Nueva URL**: `path("admin/get-available-models/", views_ai_admin.get_available_models, name="get_available_models")`

### **3. `templates/matching/ai_admin_config.html`**
- **Nueva función JavaScript**: `loadAvailableModels()`
- Hace fetch a `/matching/admin/get-available-models/`
- Pobla dinámicamente los dropdowns de modelos
- Maneja errores de carga
- Preserva el modelo seleccionado actual

---

## 🚀 Ventajas del Sistema

### **Antes (Hardcodeado)**
```python
# matching/forms.py
self.fields['openai_model'].choices = [
    ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
    ('gpt-4-turbo', 'GPT-4 Turbo'),  # ❌ Puede no existir
    ('claude-3-sonnet-20240229', 'Claude 3 Sonnet'),  # ❌ Puede dar 404
]
```

**Problemas:**
- ❌ Modelos hardcodeados pueden no existir en la cuenta del usuario
- ❌ Errores 404 al usar modelos no disponibles
- ❌ No se actualizan cuando OpenAI/Anthropic lanzan nuevos modelos
- ❌ Usuario puede configurar modelos que no puede usar

---

### **Ahora (Dinámico)**
```javascript
// Consulta en tiempo real
fetch('/matching/admin/get-available-models/')
    .then(data => {
        // Solo muestra modelos que el usuario PUEDE usar
        data.openai.models.forEach(model => {
            // ✅ Modelo verificado y disponible
            dropdown.add(model);
        });
    });
```

**Ventajas:**
- ✅ **Solo modelos disponibles**: El usuario solo ve modelos que puede usar
- ✅ **Actualización automática**: Nuevos modelos aparecen automáticamente
- ✅ **Sin errores 404**: Imposible configurar un modelo inexistente
- ✅ **Validación en tiempo real**: Detecta problemas de API key inmediatamente
- ✅ **Mejor UX**: Mensajes claros de error si no hay API key

---

## 🔧 Cómo Probar

1. **Accede a la configuración de IA:**
   ```
   http://localhost:8000/matching/admin/ai-config/
   ```

2. **Observa la consola del navegador:**
   ```
   🔄 Cargando modelos disponibles...
   ✅ Modelos recibidos: {...}
   ✅ 5 modelos OpenAI cargados
   ✅ 8 modelos Anthropic cargados
   ✅ Modelos cargados exitosamente
   ```

3. **Verifica los dropdowns:**
   - Los dropdowns de "Modelo de OpenAI" y "Modelo de Anthropic" deben mostrar solo modelos disponibles
   - Si no hay API key configurada, debe mostrar: `❌ API Key no configurada`
   - Si hay error de cuota, debe mostrar: `❌ Error: You exceeded your current quota...`

4. **Selecciona un modelo y guarda:**
   - Solo podrás seleccionar modelos que realmente existen en tu cuenta
   - No habrá errores 404 al usar el sistema

---

## 📊 Ejemplo de Respuesta de la API

```json
{
  "success": true,
  "openai": {
    "models": [
      {
        "id": "gpt-4o-mini-2024-07-18",
        "name": "GPT-4o Mini (gpt-4o-mini-2024-07-18)",
        "created": 1721172741
      },
      {
        "id": "gpt-3.5-turbo",
        "name": "GPT-3.5 Turbo (gpt-3.5-turbo)",
        "created": 1677610602
      }
    ],
    "error": null
  },
  "anthropic": {
    "models": [
      {
        "id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet (claude-sonnet-4-5-20250929)"
      },
      {
        "id": "claude-haiku-4-5-20251001",
        "name": "Claude Haiku (claude-haiku-4-5-20251001)"
      }
    ],
    "error": null
  }
}
```

---

## 🎯 Resultado Final

Ahora, cuando el usuario accede a `/matching/admin/ai-config/`, los dropdowns de modelos se llenan automáticamente con **solo los modelos que están disponibles en su cuenta**, evitando errores de configuración y mejorando significativamente la experiencia del usuario.

✅ **Problema resuelto**: El usuario ya no puede configurar modelos que no existen o no están disponibles en su cuenta.


