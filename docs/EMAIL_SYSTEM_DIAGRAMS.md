# 📊 Diagramas del Sistema de Envío Automático de Emails

## 🏗️ Arquitectura General del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Django)                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Dashboard     │  │   APIs REST     │  │   Templates     │  │
│  │   Monitoreo     │  │   Endpoints     │  │   HTML/JS       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    CELERY TASK QUEUE                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Redis Broker  │  │   Celery Beat   │  │   Celery Worker │  │
│  │   (Message      │  │   (Scheduler)   │  │   (Executor)    │  │
│  │    Queue)       │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    TASK EXECUTION LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Envío Individual│  │  Envío Masivo   │  │Matching Auto    │  │
│  │ send_personalized│  │send_bulk_emails │  │process_auto_    │  │
│  │ _email_task     │  │ _task           │  │ matching_task   │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    AI SERVICES LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Email          │  │  CV             │  │  Job            │  │
│  │  Personalization│  │  Personalization│  │  Analysis       │  │
│  │  Service        │  │  Service        │  │  Service        │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    EXTERNAL AI PROVIDERS                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                      │
│  │    OpenAI       │  │   Anthropic     │                      │
│  │  (GPT Models)   │  │ (Claude Models) │                      │
│  └─────────────────┘  └─────────────────┘                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    DATABASE LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   EmailSentLog  │  │   UserProfile   │  │   JobPosting    │  │
│  │   (Audit Trail) │  │   (Config)      │  │   (Job Data)    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   UserCV        │  │   MatchScore    │  │   ScrapingLog   │  │
│  │   (CV Data)     │  │   (Matching)    │  │   (Debug)       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    EMAIL DELIVERY                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   SMTP Server   │  │   Rate Limiting │  │   Retry Logic   │  │
│  │   (User Config) │  │   (Delays)      │  │   (Backoff)     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🔄 Flujo de Envío de Email Individual

```
1. Usuario inicia envío
   ↓
2. Frontend → API REST
   ↓
3. API → Celery Task Queue
   ↓
4. Worker recibe tarea
   ↓
5. Verificar límites diarios
   ↓
6. ¿Límite excedido?
   ├─ SÍ → Error + Retry After
   └─ NO → Continuar
   ↓
7. Generar email con IA
   ├─ Extraer datos CV
   ├─ Analizar puesto
   ├─ Seleccionar template
   └─ Generar contenido
   ↓
8. Personalizar CV adjunto
   ↓
9. Enviar email SMTP
   ↓
10. Registrar en EmailSentLog
   ↓
11. Aplicar pausa aleatoria
   ↓
12. Retornar resultado
```

## 🔄 Flujo de Envío Masivo

```
1. Usuario selecciona múltiples puestos
   ↓
2. Configurar parámetros:
   ├─ Batch size (1-20)
   ├─ Delay entre batches (60-3600s)
   ├─ Template de email
   └─ Proveedor de IA
   ↓
3. Dividir puestos en batches
   ↓
4. Procesar cada batch:
   ├─ Enviar tareas individuales
   ├─ Esperar delay configurado
   └─ Continuar con siguiente batch
   ↓
5. Agregar resultados a cola de monitoreo
   ↓
6. Retornar estadísticas:
   ├─ Total de puestos
   ├─ Exitosos
   ├─ Fallidos
   └─ Task IDs para monitoreo
```

## 🔄 Flujo de Matching Automático

```
1. Usuario activa matching automático
   ↓
2. Configurar parámetros:
   ├─ Score mínimo (0-100)
   ├─ Template de email
   └─ Proveedor de IA
   ↓
3. Buscar matches con score >= umbral
   ↓
4. ¿Hay matches encontrados?
   ├─ NO → Mensaje "No hay matches"
   └─ SÍ → Continuar
   ↓
5. Extraer job_ids de matches
   ↓
6. Ejecutar envío masivo automático
   ↓
7. Retornar estadísticas de procesamiento
```

## 📊 Dashboard de Monitoreo - Estructura

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMAIL MONITORING DASHBOARD                  │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    HEADER BAR                               │ │
│  │  [Monitoreo Emails] [Enviar Prueba] [Envío Masivo] [Auto]  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  ESTADÍSTICAS GENERALES                     │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │ │
│  │  │Total Emails │ │Emails Hoy   │ │Esta Semana  │ │Tasa Éxito│ │ │
│  │  │    150      │ │     25      │ │     89      │ │   92%   │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  CONFIGURACIÓN ACTUAL                      │ │
│  │  Límite Diario: 50 | Umbral Match: 70% | Estado: Activo    │ │
│  │  Pausas: 30-120s | Template: base | IA: OpenAI            │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                  EMAILS RECIENTES                           │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │ Desarrollador Backend Python                            │ │ │
│  │  │ hr@techcompany.com | Enviado | 14/10/2025 21:30        │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │ Full Stack Developer React/Python                       │ │ │
│  │  │ jobs@startup.com | Fallido | 14/10/2025 21:25          │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    FLOATING ACTION                          │ │
│  │                        [📋] Ver Historial Completo          │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🗄️ Modelo de Datos - Relaciones

```
User (Django Auth)
├── UserProfile (1:1)
│   ├── daily_limit: int
│   ├── match_threshold: int
│   ├── min_pause_seconds: int
│   ├── max_pause_seconds: int
│   └── is_active: bool
│
├── UserCV (1:N)
│   ├── original_file: FileField
│   ├── parsed_text: TextField
│   ├── skills: JSONField
│   └── created_at: DateTimeField
│
├── EmailSentLog (1:N)
│   ├── cv: FK(UserCV)
│   ├── job_posting: FK(JobPosting)
│   ├── email_subject: CharField
│   ├── email_body: TextField
│   ├── sent_to: EmailField
│   ├── status: CharField
│   ├── task_id: CharField
│   ├── email_template: CharField
│   ├── ai_provider: CharField
│   └── sent_at: DateTimeField
│
└── MatchScore (1:N)
    ├── cv: FK(UserCV)
    ├── job_posting: FK(JobPosting)
    ├── score: IntegerField
    └── details: JSONField

JobPosting (Independent)
├── external_id: CharField (unique)
├── title: CharField
├── description: TextField
├── email: EmailField
└── created_at: DateTimeField
```

## 🔄 Estados de Tareas Celery

```
┌─────────────────────────────────────────────────────────────────┐
│                    CELERY TASK STATES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PENDING ────────────────────────────────────────────────────┐  │
│    │                                                        │  │
│    │  Tarea creada, esperando en cola                      │  │
│    │                                                        │  │
│    ▼                                                        │  │
│  STARTED ──────────────────────────────────────────────────┼──┤
│    │                                                        │  │
│    │  Worker comenzó procesamiento                         │  │
│    │                                                        │  │
│    ▼                                                        │  │
│  SUCCESS ──────────────────────────────────────────────────┼──┤
│    │                                                        │  │
│    │  Tarea completada exitosamente                        │  │
│    │                                                        │  │
│    ▼                                                        │  │
│  FAILURE ──────────────────────────────────────────────────┼──┤
│    │                                                        │  │
│    │  Tarea falló con error                                │  │
│    │                                                        │  │
│    ▼                                                        │  │
│  RETRY ────────────────────────────────────────────────────┼──┤
│    │                                                        │  │
│    │  Reintentando con backoff exponencial                 │  │
│    │                                                        │  │
│    └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 🚦 Rate Limiting y Pausas

```
┌─────────────────────────────────────────────────────────────────┐
│                    RATE LIMITING STRATEGY                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Límite Diario: 50 emails/día                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  [████████████████████████████████████████████████████████] │ │
│  │  0                    25                    50             │ │
│  │  └─────────────────────┘                                   │ │
│  │      Emails enviados hoy                                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Pausas Entre Envíos: 30-120 segundos (aleatorias)            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Email 1 ──[45s]──> Email 2 ──[78s]──> Email 3 ──[32s]──>  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Delays Entre Batches: 60-3600 segundos (configurables)       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Batch 1 ──[300s]──> Batch 2 ──[300s]──> Batch 3           │ │
│  │  (5 emails)      (5 emails)      (3 emails)                │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 📈 Métricas y Analytics

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMAIL STATISTICS DASHBOARD                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              MÉTRICAS GENERALES                             │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │ │
│  │  │Total Emails │ │Exitosos     │ │Fallidos     │ │Tasa Éxito│ │ │
│  │  │    150      │ │    138      │ │     12      │ │   92%   │ │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              TENDENCIAS DIARIAS (30 días)                  │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │                                                         │ │ │
│  │  │  📊 Gráfico de barras mostrando envíos por día         │ │ │
│  │  │     │                                                   │ │ │
│  │  │ 10  │   ██                                              │ │ │
│  │  │  8  │   ██ ██                                           │ │ │
│  │  │  6  │   ██ ██ ██                                        │ │ │
│  │  │  4  │ ██ ██ ██ ██                                       │ │ │
│  │  │  2  │ ██ ██ ██ ██ ██                                    │ │ │
│  │  │  0  └───────────────────────────────────────────────────┘ │ │
│  │  │     1   5   10  15  20  25  30                          │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              DISTRIBUCIÓN POR TEMPLATE                      │ │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────┐ │ │
│  │  │   Base      │ │   Formal    │ │  Creative   │ │Technical │ │
│  │  │     65      │ │     45      │ │     25      │ │    15    │ │
│  │  │   (43%)     │ │   (30%)     │ │   (17%)     │ │  (10%)  │ │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              DISTRIBUCIÓN POR IA PROVIDER                  │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │  OpenAI: ████████████████████████████████████████ 120   │ │ │
│  │  │  (80%)                                                 │ │ │
│  │  │                                                        │ │ │
│  │  │  Anthropic: ████████████████ 30                       │ │ │
│  │  │  (20%)                                                 │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Configuración de Docker

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCKER COMPOSE SETUP                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  services:                                                      │
│    postulamatic_web:                                           │
│      build: .                                                  │
│      ports:                                                    │
│        - "8000:8000"                                          │
│      depends_on:                                               │
│        - redis                                                 │
│                                                                 │
│    redis:                                                      │
│      image: redis:7-alpine                                     │
│      ports:                                                    │
│        - "6379:6379"                                          │
│                                                                 │
│    worker:                                                     │
│      build: .                                                  │
│      command: celery -A postulamatic worker --loglevel=info   │
│      depends_on:                                               │
│        - redis                                                 │
│                                                                 │
│    beat:                                                       │
│      build: .                                                  │
│      command: celery -A postulamatic beat --loglevel=info     │
│      depends_on:                                               │
│        - redis                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚨 Flujo de Manejo de Errores

```
┌─────────────────────────────────────────────────────────────────┐
│                    ERROR HANDLING FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Error Detectado                                                │
│       │                                                         │
│       ▼                                                         │
│  ¿Es error temporal?                                            │
│       │                                                         │
│   ┌───┴───┐                                                     │
│   │  SÍ   │  NO                                                 │
│   │       │                                                     │
│   ▼       ▼                                                     │
│  Reintentar  Marcar como fallido                               │
│       │       │                                                 │
│       │       ▼                                                 │
│       │  Log error +                                             │
│       │  Notificar usuario                                      │
│       │       │                                                 │
│       │       ▼                                                 │
│       │  ¿Retry count < max?                                    │
│       │       │                                                 │
│       │   ┌───┴───┐                                             │
│       │   │  SÍ   │  NO                                         │
│       │   │       │                                             │
│       │   ▼       ▼                                             │
│       │  Wait + Retry  Fallar definitivamente                   │
│       │       │       │                                         │
│       │       ▼       ▼                                         │
│       │  Backoff exponencial  Log final error                   │
│       │       │       │                                         │
│       │       ▼       ▼                                         │
│       │  Ejecutar tarea  Enviar notificación                   │
│       │       │       │                                         │
│       │       ▼       ▼                                         │
│       │  ¿Éxito?     End                                        │
│       │       │                                                 │
│       │   ┌───┴───┐                                             │
│       │   │  SÍ   │  NO                                         │
│       │   │       │                                             │
│       │   ▼       ▼                                             │
│       │  Success  Continuar con retry                           │
│       │       │                                                 │
│       │       ▼                                                 │
│       │  Log success                                            │
│       │       │                                                 │
│       │       ▼                                                 │
│       │  End                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

**Nota**: Estos diagramas representan la arquitectura y flujos del Sistema de Envío Automático de Emails de PostulaMatic. Para más detalles técnicos, consultar la documentación principal en `EMAIL_AUTOMATION_SYSTEM.md`.
