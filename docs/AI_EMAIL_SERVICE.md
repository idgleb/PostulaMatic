# 🤖 Servicio de IA para Generación de Emails

## 📋 Resumen

Implementación completa del servicio de IA para generar emails personalizados de postulación de trabajo. El sistema soporta múltiples proveedores de IA con fallback automático y templates personalizables.

## 🏗️ Arquitectura

### Componentes Principales

```
matching/services/
├── ai_service.py          # Servicio principal de IA
├── email_prompts.py       # Templates y personalización
└── test_ai_service.py     # Tests unitarios
```

### Flujo de Generación

```
CV Skills + Job Description + User Profile
                    ↓
            EmailPersonalizationData
                    ↓
            Prompt Template Selection
                    ↓
            AI Provider (OpenAI/Anthropic)
                    ↓
            EmailContent (Subject + Body)
```

## 🔧 Configuración

### Variables de Entorno

```bash
# OpenAI
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-3-haiku-20240307

# Proveedor por defecto
AI_PROVIDER=openai
```

### Instalación de Dependencias

```bash
pip install openai anthropic
```

## 🚀 Uso Básico

### Importar el Servicio

```python
from matching.services.ai_service import ai_email_service
```

### Generar Email Simple

```python
# Datos de entrada
job_description = "Desarrollador Python con Django..."
cv_skills = {
    'skills': ['Python', 'Django', 'PostgreSQL'],
    'experience': '3 años'
}
user_profile = {
    'display_name': 'Juan Pérez',
    'email': 'juan@example.com'
}

# Generar email
result = ai_email_service.generate_email(
    job_description=job_description,
    cv_skills=cv_skills,
    user_profile=user_profile,
    provider='openai'  # Opcional
)

# Resultado
print(f"Asunto: {result.subject}")
print(f"Cuerpo: {result.body}")
print(f"Proveedor: {result.provider}")
print(f"Tokens usados: {result.tokens_used}")
```

### Generar Email Personalizado

```python
from matching.services.email_prompts import EmailPersonalizationData

# Crear datos de personalización
personalization_data = EmailPersonalizationData(
    job_description=job_description,
    cv_skills=cv_skills,
    user_profile=user_profile,
    template_type='technical',  # formal, creative, startup, etc.
    custom_instructions='Sé muy específico con las tecnologías',
    company_info={'name': 'TechCorp', 'industry': 'Software'},
    job_metadata={'location': 'Buenos Aires', 'urgent': True}
)

# Construir prompt personalizado
custom_prompt = personalization_data.build_prompt()

# Generar email
result = ai_email_service.generate_email(
    job_description=job_description,
    cv_skills=cv_skills,
    user_profile=user_profile,
    custom_prompt=custom_prompt
)
```

## 📝 Templates Disponibles

### 1. Base (Por Defecto)
- Tono profesional estándar
- Máximo 200 palabras
- Estructura clásica

### 2. Formal
- Tono muy formal y respetuoso
- Estructura clásica de carta
- Máximo 250 palabras

### 3. Creative
- Tono cercano y personal
- Asunto creativo y memorable
- Máximo 180 palabras

### 4. Technical
- Enfoque en habilidades técnicas
- Terminología técnica apropiada
- Máximo 200 palabras

### 5. Startup
- Tono dinámico y directo
- Enfatiza proactividad
- Máximo 150 palabras

### 6. Corporate
- Tono muy profesional
- Enfatiza resultados cuantificables
- Máximo 220 palabras

## 🔄 Proveedores de IA

### OpenAI Provider
- **Modelo por defecto**: `gpt-3.5-turbo`
- **Características**: Rápido, económico, buena calidad
- **Configuración**: `OPENAI_API_KEY`

### Anthropic Provider
- **Modelo por defecto**: `claude-3-haiku-20240307`
- **Características**: Muy buena calidad, más caro
- **Configuración**: `ANTHROPIC_API_KEY`

### Fallback Automático
Si el proveedor principal falla, el sistema automáticamente intenta con el proveedor alternativo.

## 🧪 Testing

### Ejecutar Tests

```bash
python manage.py test matching.services.test_ai_service
```

### Tests Incluidos

- ✅ Inicialización del servicio
- ✅ Proveedores disponibles
- ✅ Configuración de API keys
- ✅ Construcción de prompts
- ✅ Parsing de emails generados
- ✅ Manejo de errores

## 📊 Estructura de Datos

### EmailContent
```python
@dataclass
class EmailContent:
    subject: str              # Asunto del email
    body: str                 # Cuerpo del email
    provider: str             # Proveedor usado
    model: str               # Modelo usado
    tokens_used: Optional[int] # Tokens consumidos
    error: Optional[str]      # Error si ocurrió
```

### EmailPersonalizationData
```python
class EmailPersonalizationData:
    job_description: str      # Descripción del puesto
    cv_skills: Dict          # Habilidades del CV
    user_profile: Dict       # Perfil del usuario
    template_type: str       # Tipo de template
    custom_instructions: str # Instrucciones personalizadas
    company_info: Dict       # Info de la empresa
    job_metadata: Dict       # Metadatos del puesto
```

## 🔍 Logging y Monitoreo

### Logs Generados

```python
# Éxito
logger.info(f"Email generado exitosamente con {provider}")

# Error
logger.error(f"Error generando email con {provider}: {error}")

# Fallback
logger.warning(f"Error con {provider}, intentando con {fallback_provider}")
```

### Métricas Disponibles

- Tokens consumidos por proveedor
- Tiempo de respuesta
- Tasa de éxito/fallo
- Uso de fallbacks

## 🛠️ Extensibilidad

### Agregar Nuevo Proveedor

```python
class CustomProvider(AIProvider):
    def generate_email_content(self, ...):
        # Implementar lógica personalizada
        pass

# Registrar en el servicio
ai_email_service.providers['custom'] = CustomProvider()
```

### Agregar Nuevo Template

```python
class EmailPromptTemplates:
    @staticmethod
    def get_custom_template() -> str:
        return "Tu template personalizado aquí..."
```

## 🚨 Manejo de Errores

### Errores Comunes

1. **API Key no configurada**
   - Error: `Proveedor no disponible`
   - Solución: Configurar variables de entorno

2. **Límite de tokens excedido**
   - Error: `Token limit exceeded`
   - Solución: Reducir prompt o usar modelo más grande

3. **Proveedor no disponible**
   - Error: `Service unavailable`
   - Solución: Sistema usa fallback automático

### Fallbacks Implementados

- ✅ Proveedor alternativo si el principal falla
- ✅ Template por defecto si no se encuentra el especificado
- ✅ Valores por defecto para subject/body si parsing falla

## 📈 Rendimiento

### Optimizaciones

- **Caching de prompts**: Templates reutilizables
- **Fallback rápido**: Cambio automático de proveedor
- **Parsing eficiente**: Extracción rápida de subject/body

### Límites Recomendados

- **Máximo de palabras**: 250 palabras por email
- **Tiempo de timeout**: 30 segundos por request
- **Rate limiting**: Respetar límites de API de proveedores

## 🔐 Seguridad

### Datos Sensibles

- ✅ API keys en variables de entorno
- ✅ No logging de contenido de emails
- ✅ Validación de inputs
- ✅ Sanitización de prompts

### Privacidad

- ✅ No almacenamiento de emails generados
- ✅ Logs sin información personal
- ✅ Manejo seguro de credenciales

## 📚 Referencias

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic API Documentation](https://docs.anthropic.com)
- [Django Settings Documentation](https://docs.djangoproject.com/en/stable/topics/settings/)

---

## ✅ Estado del Desarrollo

**PASO 1 COMPLETADO** ✅
- [x] Servicio de IA implementado
- [x] Soporte multi-proveedor
- [x] Templates personalizables
- [x] Tests unitarios
- [x] Documentación completa

**PRÓXIMO PASO**: Integración con datos reales de CV y puestos de trabajo.
