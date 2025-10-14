# 📚 Documentación de PostulaMatic

## 🎯 Descripción General

PostulaMatic es un sistema automatizado de postulación a trabajos que utiliza inteligencia artificial para generar emails personalizados y enviar aplicaciones de forma masiva a puestos de trabajo relevantes.

## 📋 Índice de Documentación

### 🤖 Sistema de IA y Personalización

1. **[Servicio de IA para Emails](AI_EMAIL_SERVICE.md)**
   - Configuración de proveedores de IA (OpenAI, Anthropic)
   - Generación de contenido personalizado
   - Manejo de errores y fallbacks
   - Testing y validación

2. **[Servicio de Personalización de Emails](EMAIL_PERSONALIZATION_SERVICE.md)**
   - Extracción de datos de CV y puestos
   - Selección automática de templates
   - Personalización basada en contexto
   - Análisis de requisitos del puesto

3. **[Personalización de CV](CV_PERSONALIZATION_SYSTEM.md)**
   - Análisis de requisitos del puesto
   - Adaptación de contenido del CV
   - Generación de versiones personalizadas
   - Integración con sistema de emails

### 📧 Sistema de Envío Automático

4. **[Sistema de Envío Automático de Emails](EMAIL_AUTOMATION_SYSTEM.md)**
   - Arquitectura completa del sistema
   - Tareas de Celery para envío masivo
   - Dashboard de monitoreo
   - APIs REST y endpoints
   - Configuración de rate limiting
   - Manejo de errores y reintentos

5. **[Diagramas del Sistema de Emails](EMAIL_SYSTEM_DIAGRAMS.md)**
   - Arquitectura visual del sistema
   - Flujos de proceso detallados
   - Modelos de datos y relaciones
   - Estados de tareas y métricas

6. **[Guía Rápida - Sistema de Emails](EMAIL_SYSTEM_QUICKSTART.md)**
   - Inicio rápido en 5 minutos
   - Comandos esenciales
   - Troubleshooting común
   - Testing y monitoreo

### 🔧 Configuración y Despliegue

7. **[Guía de Instalación](../README.md)**
   - Requisitos del sistema
   - Instalación con Docker
   - Configuración inicial
   - Variables de entorno

8. **[Configuración de Producción](PRODUCTION_SETUP.md)**
   - Configuración de servidores
   - Optimización de rendimiento
   - Monitoreo y alertas
   - Backup y recuperación

### 🧪 Testing y Desarrollo

9. **[Guía de Testing](TESTING_GUIDE.md)**
   - Tests unitarios y de integración
   - Testing de servicios de IA
   - Testing de tareas de Celery
   - Cobertura de código

10. **[Guía de Desarrollo](DEVELOPMENT_GUIDE.md)**
    - Estructura del proyecto
    - Convenciones de código
    - Flujo de trabajo Git
    - Contribución al proyecto

## 🚀 Inicio Rápido

### Para Usuarios
1. **Configurar credenciales**: [Guía Rápida - Sistema de Emails](EMAIL_SYSTEM_QUICKSTART.md)
2. **Probar el sistema**: [Comandos de Testing](EMAIL_SYSTEM_QUICKSTART.md#testing-rápido)
3. **Usar el dashboard**: [Sistema de Envío Automático](EMAIL_AUTOMATION_SYSTEM.md#dashboard-de-monitoreo)

### Para Desarrolladores
1. **Configurar entorno**: [Guía de Instalación](../README.md)
2. **Entender la arquitectura**: [Diagramas del Sistema](EMAIL_SYSTEM_DIAGRAMS.md)
3. **Desarrollar nuevas funcionalidades**: [Guía de Desarrollo](DEVELOPMENT_GUIDE.md)

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        POSTULAMATIC                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Landing       │  │   Matching      │  │   Scraping      │  │
│  │   Pages         │  │   System        │  │   System        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   AI Email      │  │   CV            │  │   Email         │  │
│  │   Generation    │  │   Personalization│  │   Automation    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Celery        │  │   Redis         │  │   PostgreSQL    │  │
│  │   Workers       │  │   Broker        │  │   Database      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Características Principales

### 🤖 Inteligencia Artificial
- **Generación de emails personalizados** con OpenAI GPT y Anthropic Claude
- **Análisis de requisitos** de puestos de trabajo
- **Personalización de CV** basada en contexto
- **Selección automática de templates** según el tipo de puesto

### 📧 Automatización de Emails
- **Envío masivo** con rate limiting inteligente
- **Pausas aleatorias** para emular comportamiento humano
- **Reintentos automáticos** con backoff exponencial
- **Monitoreo en tiempo real** del estado de envíos

### 🎯 Matching Inteligente
- **Cálculo de coincidencias** entre CV y puestos
- **Umbrales configurables** por usuario
- **Filtrado automático** de puestos relevantes
- **Envío automático** solo a matches altos

### 📊 Dashboard y Monitoreo
- **Estadísticas en tiempo real** de envíos
- **Historial completo** de aplicaciones
- **Configuración de usuario** personalizable
- **APIs REST** para integración

## 🛠️ Tecnologías Utilizadas

### Backend
- **Django 5.x** - Framework web
- **Python 3.12** - Lenguaje de programación
- **Celery** - Cola de tareas asíncronas
- **Redis** - Broker de mensajes y caché
- **PostgreSQL** - Base de datos principal

### Frontend
- **Bootstrap 5** - Framework CSS
- **HTMX** - Interactividad sin JavaScript
- **Chart.js** - Gráficos y visualizaciones
- **Bootstrap Icons** - Iconografía

### IA y Procesamiento
- **OpenAI GPT** - Generación de contenido
- **Anthropic Claude** - Generación alternativa
- **BeautifulSoup** - Scraping de datos
- **PyPDF2/python-docx** - Procesamiento de CVs

### Infraestructura
- **Docker** - Containerización
- **Docker Compose** - Orquestación
- **Nginx** - Servidor web y proxy
- **Gunicorn** - Servidor WSGI

## 📈 Métricas del Sistema

### Rendimiento
- **Tiempo de envío individual**: 2-5 segundos
- **Envío masivo (10 emails)**: 30-60 segundos
- **Matching automático**: 10-30 segundos
- **Tasa de éxito**: 85-95%

### Límites
- **Límite diario por usuario**: 50-100 emails
- **Batch size recomendado**: 5-10 emails
- **Delay entre batches**: 300-600 segundos
- **Pausas individuales**: 30-120 segundos

## 🔒 Seguridad

### Datos Sensibles
- **Credenciales encriptadas** en base de datos
- **Variables de entorno** para secretos
- **No logging** de información sensible
- **Cumplimiento TOS** de sitios web

### Rate Limiting
- **Límites configurables** por usuario
- **Pausas aleatorias** entre envíos
- **Backoff exponencial** en reintentos
- **Verificación de límites** antes de envío

## 📞 Soporte

### Documentación
- **Guías detalladas** para cada componente
- **Ejemplos de código** y configuración
- **Troubleshooting** común
- **APIs documentadas** con ejemplos

### Comandos Útiles
```bash
# Verificar estado del sistema
docker compose ps

# Ver logs de workers
docker compose logs worker --tail 20

# Probar sistema de emails
docker compose exec postulamatic_web python manage.py test_email_system

# Acceder al dashboard
# http://localhost:8000/matching/email-monitoring/
```

---

## 📝 Notas de Versión

### v1.0.0 (Octubre 2025)
- ✅ Sistema completo de envío automático de emails
- ✅ Integración con OpenAI y Anthropic
- ✅ Dashboard de monitoreo en tiempo real
- ✅ Personalización de CV con IA
- ✅ Rate limiting y manejo de errores
- ✅ APIs REST completas
- ✅ Documentación exhaustiva

### Próximas Versiones
- 🔄 Notificaciones en tiempo real
- 🔄 Métricas avanzadas de analytics
- 🔄 Integración con más sitios de trabajo
- 🔄 Templates de email personalizables
- 🔄 Sistema de feedback y mejora continua

---

**📧 PostulaMatic - Automatiza tu búsqueda de trabajo con IA**

Para más información, consulta la documentación específica de cada componente o contacta al equipo de desarrollo.
