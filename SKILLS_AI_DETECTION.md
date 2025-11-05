# 🤖 Detección de Habilidades con IA

## 📋 Resumen

Se ha implementado un **sistema híbrido de detección de habilidades** que combina:

1. **Método tradicional** (keywords): Base de datos de ~800 habilidades predefinidas
2. **Método con IA** (GPT/Claude): Detección inteligente de habilidades no listadas

---

## 🎯 Características Implementadas

### ✅ **1. Detección Híbrida**

El sistema ahora ejecuta **dos fases de detección**:

```python
# Fase 1: Keywords (tradicional)
traditional_skills = {
    "python": 1.0,
    "django": 0.9,
    "android": 1.0,
    # ... ~800 habilidades predefinidas
}

# Fase 2: IA (adicional)
ai_skills = {
    "SberPay": 0.7,          # Tecnología específica no listada
    "Material Design": 0.7,   # Framework de diseño
    "Accessibility": 0.7,     # Habilidad blanda específica
    # ... habilidades emergentes o específicas del dominio
}

# Resultado final: combinación de ambas
all_skills = {**traditional_skills, **ai_skills}
```

### ✅ **2. Prompt Inteligente**

El prompt enviado a la IA:
- ✅ Excluye habilidades ya detectadas (evita duplicados)
- ✅ Solicita normalización de nombres (ej: "React.js" → "React")
- ✅ Busca habilidades técnicas, blandas, certificaciones y metodologías
- ✅ Limita el texto del CV a 4000 caracteres para optimizar tokens
- ✅ Solicita formato simple (lista separada por comas)

### ✅ **3. Fallback Automático**

```python
# Intenta con OpenAI primero
response, used_fallback = ai_service.generate_text_and_track_fallback(prompt)

# Si OpenAI falla (cuota, timeout, error), usa Anthropic automáticamente
if used_fallback:
    logger.info("✅ Habilidades detectadas con Anthropic (fallback)")
else:
    logger.info("✅ Habilidades detectadas con OpenAI")
```

### ✅ **4. Validación y Filtrado**

Las habilidades detectadas por IA pasan por:
- ✅ Validación de longitud (2-50 caracteres)
- ✅ Eliminación de duplicados con habilidades existentes
- ✅ Filtrado de stop words
- ✅ Aplicación de sinónimos
- ✅ Score de confianza: **0.7** (IA) vs **1.0** (keyword exacto)

### ✅ **5. Integración con Progress Tracker**

El frontend ahora muestra:
```
📊 Analizando texto del CV con keywords...
🤖 Detectando habilidades adicionales con IA...
✅ 35 habilidades detectadas (hybrid_keyword_and_ai)
```

---

## 🔧 Cambios Técnicos

### **Archivo: `matching/services/skills_extractor.py`**

#### **Nuevos Métodos:**

1. **`__init__(use_ai: bool = True)`**
   - Parámetro para habilitar/deshabilitar IA
   - Lazy loading del servicio de IA

2. **`ai_service` (property)**
   - Inicializa `AIEmailService` solo cuando se necesita
   - Maneja errores de inicialización gracefully

3. **`extract_skills(cv_text, min_confidence, progress_tracker)`**
   - Ahora acepta `progress_tracker` opcional
   - Ejecuta detección tradicional + IA
   - Combina resultados y retorna metadata detallada

4. **`_extract_skills_with_ai(cv_text, existing_skills, progress_tracker)`**
   - Crea prompt optimizado
   - Llama a IA con fallback
   - Parsea respuesta y filtra duplicados

5. **`_create_ai_skills_prompt(cv_text, existing_skills)`**
   - Genera prompt estructurado
   - Limita texto a 4000 caracteres
   - Incluye lista de habilidades ya detectadas

6. **`_parse_ai_skills_response(response, existing_skills)`**
   - Parsea respuesta de IA (formato CSV)
   - Valida y normaliza habilidades
   - Asigna score de confianza 0.7

#### **Cambios en Métodos Existentes:**

- **`extract_skills()`**: Ahora retorna metadata adicional:
  ```python
  {
      "skills": [...],
      "categories": {...},
      "confidence_scores": {...},
      "total_skills": 35,
      "extraction_method": "hybrid_keyword_and_ai",  # ← Nuevo
      "details": {
          "exact_matches": 15,
          "keyword_matches": 10,
          "context_matches": 5,
          "ai_detected": 5,  # ← Nuevo
          "traditional_total": 30  # ← Nuevo
      }
  }
  ```

### **Archivo: `matching/tasks.py`**

#### **Cambios en `process_cv_async`:**

```python
# Antes:
extractor = SkillsExtractor()
skills_data = extractor.extract_skills(parsed_text)

# Ahora:
extractor = SkillsExtractor(use_ai=True)  # ← Habilitar IA
skills_data = extractor.extract_skills(parsed_text, progress_tracker=tracker)  # ← Pasar tracker

# Logging mejorado:
extraction_method = skills_data.get('extraction_method', 'unknown')
ai_detected = skills_data.get('details', {}).get('ai_detected', 0)

logger.info(f"✅ Habilidades extraídas: {skills_count} (método: {extraction_method})")
if ai_detected > 0:
    logger.info(f"   └─ {ai_detected} habilidades adicionales detectadas con IA")
```

---

## 📊 Ejemplo de Uso

### **Input: CV de Desarrollador Android**

```
Gleb Ursol
DESARROLLADOR ANDROID

Experiencia:
- Desarrollo de apps Android con Kotlin
- Integración de APIs con Retrofit y OkHttp
- Uso de Jetpack Compose, ViewModel, Room
- Implementación de SberPay para pagos
- Diseño con Material Design y Figma
```

### **Output: Habilidades Detectadas**

#### **Fase 1: Keywords (30 habilidades)**
```python
{
    "kotlin": 1.0,
    "android": 1.0,
    "retrofit": 1.0,
    "okhttp": 1.0,
    "jetpack compose": 1.0,
    "viewmodel": 1.0,
    "room": 1.0,
    "figma": 1.0,
    # ... más habilidades de la base de datos
}
```

#### **Fase 2: IA (5 habilidades adicionales)**
```python
{
    "SberPay": 0.7,           # ← No estaba en la base de datos
    "Material Design": 0.7,   # ← Específico del dominio
    "API Integration": 0.7,   # ← Habilidad inferida
    "Mobile Development": 0.7,# ← Categoría general
    "UI/UX Design": 0.7       # ← Habilidad blanda
}
```

#### **Resultado Final: 35 habilidades**
```json
{
  "skills": ["kotlin", "android", "retrofit", "SberPay", "Material Design", ...],
  "total_skills": 35,
  "extraction_method": "hybrid_keyword_and_ai",
  "details": {
    "exact_matches": 15,
    "keyword_matches": 10,
    "context_matches": 5,
    "ai_detected": 5,
    "traditional_total": 30
  }
}
```

---

## 🚀 Ventajas del Sistema Híbrido

### **1. Mayor Cobertura**
- ✅ Detecta tecnologías emergentes (ej: SberPay, Bun, Deno)
- ✅ Captura habilidades específicas del dominio
- ✅ Identifica certificaciones no listadas

### **2. Flexibilidad**
- ✅ Se puede deshabilitar IA (`use_ai=False`)
- ✅ Fallback a keywords si IA falla
- ✅ No rompe el flujo existente

### **3. Precisión**
- ✅ Evita duplicados (compara con habilidades existentes)
- ✅ Normaliza nombres automáticamente
- ✅ Valida longitud y formato

### **4. Observabilidad**
- ✅ Logs detallados de cada fase
- ✅ Metadata de método de extracción
- ✅ Conteo de habilidades por fuente

---

## ⚙️ Configuración

### **Habilitar/Deshabilitar IA**

```python
# Habilitar IA (por defecto)
extractor = SkillsExtractor(use_ai=True)

# Deshabilitar IA (solo keywords)
extractor = SkillsExtractor(use_ai=False)
```

### **Ajustar Confianza Mínima**

```python
# Por defecto: 0.3 (30%)
skills_data = extractor.extract_skills(cv_text, min_confidence=0.3)

# Más estricto: 0.5 (50%)
skills_data = extractor.extract_skills(cv_text, min_confidence=0.5)

# Menos estricto: 0.2 (20%)
skills_data = extractor.extract_skills(cv_text, min_confidence=0.2)
```

### **Limitar Texto del CV**

```python
# En _create_ai_skills_prompt():
max_chars = 4000  # ← Ajustar según necesidad
truncated_text = cv_text[:max_chars]
```

---

## 🧪 Testing

### **Probar con un CV Real**

1. **Subir CV** en `http://localhost:8000/matching/mis-cvs/`
2. **Observar logs** en el worker:
   ```bash
   docker-compose logs -f worker
   ```
3. **Buscar líneas clave**:
   ```
   🔍 Habilidades detectadas con keywords: 30
   🤖 Iniciando detección de habilidades con IA...
   ✅ Respuesta recibida de OpenAI: 250 caracteres
   ✅ Habilidades parseadas de IA: 5
   ✅ Habilidades adicionales detectadas con IA: 5
   ✅ Habilidades extraídas: 35 (método: hybrid_keyword_and_ai)
      └─ 5 habilidades adicionales detectadas con IA
   ```

### **Verificar en Base de Datos**

```python
from matching.models import UserCV

cv = UserCV.objects.latest('id')
print(cv.skills)

# Output esperado:
{
    "skills": ["kotlin", "android", "SberPay", ...],
    "total_skills": 35,
    "extraction_method": "hybrid_keyword_and_ai",
    "details": {
        "ai_detected": 5,
        ...
    }
}
```

---

## 🔮 Mejoras Futuras

### **1. Categorización Automática con IA**
- Usar IA para categorizar habilidades detectadas
- Crear categorías dinámicas según el dominio

### **2. Detección de Nivel de Habilidad**
- Extraer años de experiencia por habilidad
- Clasificar como Junior/Mid/Senior

### **3. Detección de Sinónimos con IA**
- Usar IA para normalizar variantes (ej: "JS" → "JavaScript")
- Aprender sinónimos del contexto

### **4. Caché de Resultados**
- Cachear respuestas de IA por hash del CV
- Evitar llamadas duplicadas

### **5. Fine-tuning del Modelo**
- Entrenar modelo específico para detección de habilidades
- Mejorar precisión y reducir costos

---

## 📝 Notas Importantes

1. **Costos de IA**: Cada CV procesado consume ~500-1000 tokens (OpenAI/Anthropic)
2. **Timeout**: Si IA tarda >60s, se usa solo keywords
3. **Fallback**: Si OpenAI falla, Anthropic se intenta automáticamente
4. **Confianza**: Habilidades de IA tienen score 0.7 vs 1.0 de keywords exactos
5. **Duplicados**: El sistema evita duplicados comparando con habilidades existentes

---

## 🎉 Conclusión

El sistema híbrido de detección de habilidades combina lo mejor de ambos mundos:
- **Keywords**: Rápido, predecible, sin costos adicionales
- **IA**: Flexible, inteligente, detecta habilidades emergentes

Esto permite capturar **más habilidades** sin sacrificar **precisión** ni **rendimiento**. 🚀


