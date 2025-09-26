# PostulaMatic — PRD (Project Requirements Doc)

## Resumen
Sistema Django que: (1) permite a usuarios subir CV, (2) extrae habilidades con IA, (3) hace login en https://dvcarreras.davinci.edu.ar/login.html con credenciales del usuario y scrapea ofertas en https://dvcarreras.davinci.edu.ar/job_board-0.html, (4) calcula un score de coincidencia configurable, y (5) envía postulaciones por email (desde la cuenta que el usuario indique) con texto y CV personalizados por IA. Dashboard con tarjetas de postulaciones y detalle completo. Envíos limitados por día y con pausas aleatorias para reducir riesgo de bloqueo.

## Stack
- Backend: Python 3.12, Django
- BD: SQLite en dev, Postgres recomendado prod
- Front: Django templates + HTMX (opcional) + Tailwind (opcional)
- Scraping: requests/requests-html + BeautifulSoup (o Playwright si hiciera falta)
- IA: OpenAI API (o pluggable) para extracción de skills + redacción email + CV dinámico
- Correo: SMTP (usuario aporta credenciales) o API de proveedor (opcional)

## Flujo principal
1) Usuario se registra/inicia sesión.
2) Sube CV (PDF/DOCX). Se guarda y se parsea → `skills`, `experience`, `education`.
3) Carga credenciales DV Carreras (usuario/contraseña) y correo remitente (SMTP).
4) Define umbral de match (0–100) y límites de envío (p.ej. 10/día; pausa 60–180s).
5) Pulsa **Start** → job de background:
    - Login a `login.html` (con sesión).
    - Scrapea `job_board-0.html` y perfiles `job_profile-*.html`.
    - Normaliza ofertas → `JobPosting`.
    - Matching CV vs oferta → `score`.
    - Si `score >= umbral`: genera email con IA + CV adaptado y envía (respetando rate-limit).
    - Registra `Application` y actualiza dashboard.

## Scraper: detalles DOM (basado en HTML provisto)
- `job_board-0.html` lista ofertas en `<table class="striped">` con `<tr>` por oferta.
- Título: `<strong>…</strong>`
- Descripción breve: `<small>…</small>`
- Link a detalle: `<a href="job_profile-*.html">`
- Emails están ofuscados por Cloudflare: `<a class="__cf_email__" data-cfemail="…">` + script `/cdn-cgi/scripts/.../email-decode.min.js`. **Debemos decodificar data-cfemail en Python** (algoritmo XOR con la primera byte como key).
- Filtro por carrera: `<select id="filter_career">` (podemos ignorar al inicio).

> Nota: el acceso requiere login. Usar sesión persistente (cookies). Respetar TOS y obtener consentimiento explícito del usuario para usar sus credenciales.

## Modelos (Django)
- `UserProfile(user OneToOne)`:
    - `dv_username`, `dv_password` (cifrados en reposo)
    - `smtp_host`, `smtp_port`, `smtp_user`, `smtp_password`, `smtp_use_tls`, `smtp_use_ssl`
    - `from_name`, `from_email`
    - `match_threshold` (int 0–100), `daily_limit` (int), `min_pause_s` (int), `max_pause_s` (int)
- `CVUpload(user FK)`: archivo, texto extraído, `skills[]`, `parsed_ok`, `created_at`
- `JobPosting`: `source="dvcarreras"`, `external_id` (hash del link), `title`, `summary`, `email_list[]`, `url`, `raw_html`, `posted_at`
- `Application`: `user FK`, `job FK`, `score`, `status` (queued/sent/failed), `sent_at`, `email_to`, `email_subject`, `email_body`, `cv_variant_path`, `error_text`
- `EmailTemplate`: prompts IA (plantilla base parametrizable por usuario)
- `RunLog`: auditoría de scraping/envíos (timestamps, latencias, errores)

## Tareas asíncronas
- Cola de trabajos (al inicio: gestión con cron/background thread; luego Celery + Redis).
- Jobs: `scrape_jobs`, `match_jobs`, `generate_email_and_cv`, `send_email`.

## Lógica de matching (v1)
- Extraer `skills` de CV y de oferta (IA o heurística).
- Score = combinación de (skills overlap + keywords + seniority). Normalizar 0–100.
- Umbral configurable en `UserProfile.match_threshold`.

## Personalización de email y CV (v1)
- Prompt IA (plantilla) con: título oferta, puntos clave de requisitos y highlights del CV.
- Adjuntar CV base o versión “ligera” (PDF) con secciones reordenadas (v1: cover letter en cuerpo del mail, CV fijo).
- **No** envíes URLs privadas del usuario a IA.

## Rate limiting y anti-bloqueo
- `daily_limit` por usuario.
- Pausas aleatorias `uniform(min_pause_s, max_pause_s)` entre emails.
- User-Agent rotatorio y `Retry-After` si aparece.
- Respetar robots.txt si corresponde (y términos del sitio).

## Variables de entorno (ejemplos)
- `DJANGO_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
- `OPENAI_API_KEY` (u otro proveedor)
- `EMAIL_DEFAULT_FROM` (fallback)
- `SCRAPER_TIMEOUT=20`, `SCRAPER_RETRY=3`

## Seguridad
- Cifrar campos sensibles (Fernet/AES) o usar KMS/Secrets en prod.
- Nunca loggear contraseñas/token.
- Validar tamaño/virus al subir CV (clamd opcional).
- Separar workers del web server.

## Dashboard (v1)
- Tarjetas con: título, score, fecha envío/estado.
- Detalle: oferta completa, correo generado, adjunto usado, logs, reintentos.

## Hitos (milestones)
1) Modelos + subida de CV + extracción de texto/habilidades.
2) Login + scraping básico (lista + detalle + decode `data-cfemail`).
3) Matching + panel de pruebas manuales.
4) Envío SMTP con rate limit + templates IA (texto).
5) Dashboard + reintentos + logs.
6) Celery/Redis (si hace falta escala) + hardening.

## Criterio de aceptación v1
- Usuario puede subir CV, guardar SMTP + credenciales DV, fijar umbral, iniciar y ver resultados (>=1 envío simulado en dev).
- Scraper baja al menos 10 ofertas, decodifica emails y normaliza datos.
- Matching produce score consistente.
- Envío respeta límites y registra aplicaciones.

