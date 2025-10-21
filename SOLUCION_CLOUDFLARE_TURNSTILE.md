# Solución para Cloudflare Turnstile en DV Carreras

## Problema Identificado

Cloudflare está bloqueando permanentemente el navegador automatizado de Playwright con Turnstile, que no se puede resolver automáticamente con 2Captcha porque usa un sitekey interno de Cloudflare.

## Solución Implementada

### 1. Login Manual Asistido (Una vez)

**Comando:** `python manage.py dv_login_manual_assist`

**Proceso:**
1. Abre un navegador visible (no headless)
2. Navega a la página de login de DV Carreras
3. El usuario resuelve el CAPTCHA manualmente
4. Una vez en el dashboard, presiona Enter
5. La sesión se guarda en `media/dv_sessions/<username>_session.json`

### 2. Reutilización de Sesión Guardada

**Funcionamiento:**
- La verificación automática ahora busca sesiones guardadas
- Si existe una sesión válida, la usa automáticamente
- Si la sesión expiró, procede con el login normal

### 3. Flujo de Verificación Mejorado

```
1. Verificar si existe sesión guardada
   ├─ Sí: Usar sesión guardada
   │   ├─ Válida: ✅ Login exitoso
   │   └─ Expirada: Proceder con login normal
   └─ No: Login normal
       ├─ Cloudflare Turnstile detectado
       │   ├─ Esperar verificación automática (60s)
       │   │   ├─ Exitosa: ✅ Login exitoso
       │   │   └─ Timeout: ❌ Fallo
       │   └─ Capturar para análisis
       └─ Continuar con login normal
```

## Archivos Modificados

### 1. `matching/clients/dvcarreras_playwright_simple.py`
- ✅ Agregado soporte para sesiones guardadas
- ✅ Método `test_login_with_session()`
- ✅ Detección mejorada de Turnstile
- ✅ Espera automática de verificación Cloudflare

### 2. `matching/tasks_dv.py`
- ✅ Verificación de sesiones guardadas
- ✅ Uso automático de sesiones válidas

### 3. `matching/management/commands/dv_login_manual_assist.py`
- ✅ Comando para login manual asistido
- ✅ Guardado automático de sesión

### 4. `matching/management/commands/dv_login_test.py`
- ✅ Comando de información y estado

## Cómo Usar

### 🎯 **Flujo Automático desde la Web (Recomendado)**

1. **Ve a `http://localhost:8000/matching/perfil/`**
2. **Configura tus credenciales DV** (usuario y contraseña)
3. **Pulsa "Conectar a DAVINCI"**
4. **Si aparece Cloudflare/CAPTCHA:**
   - El botón cambiará a **"Resolver CAPTCHA manualmente"**
   - Aparecerá una notificación explicativa
   - Haz clic en el botón para abrir navegador
   - Resuelve el CAPTCHA manualmente
   - La sesión se guarda automáticamente
5. **Verificaciones posteriores son automáticas** (usan la sesión guardada)

### 🔧 **Flujo Manual (Comando)**

```bash
# Paso 1: Login Manual (Solo una vez)
python manage.py dv_login_manual_assist

# Paso 2: Verificar Estado
python manage.py dv_login_test
```

## Beneficios

1. **✅ Bypass de Cloudflare:** El usuario resuelve el CAPTCHA una sola vez
2. **✅ Automatización:** Las verificaciones posteriores son automáticas
3. **✅ Persistencia:** La sesión se mantiene entre reinicios
4. **✅ Fallback:** Si la sesión expira, vuelve al login normal
5. **✅ Debug:** Capturas automáticas para análisis

## Próximos Pasos

Si Cloudflare sigue bloqueando permanentemente:

1. **Rotación de IPs:** Usar servicios de proxy rotativos
2. **Browser Fingerprinting:** Mejorar la simulación del navegador
3. **API Alternative:** Buscar APIs alternativas si están disponibles
4. **Captcha Solving:** Integrar servicios de resolución de CAPTCHA más avanzados

## Estado Actual

- ✅ **Login manual asistido:** Implementado
- ✅ **Reutilización de sesión:** Implementado  
- ✅ **Detección de Turnstile:** Implementado
- ✅ **Espera automática:** Implementado
- ✅ **Integración web:** Implementado
- ✅ **Detección automática de CAPTCHA:** Implementado
- ✅ **Notificaciones informativas:** Implementado
- ⏳ **Testing:** En progreso

## Comandos de Testing

```bash
# Ver estado de usuarios y sesiones
python manage.py dv_login_test

# Login manual asistido
python manage.py dv_login_manual_assist

# Ver logs del worker
docker logs postulamatic-worker-1 --tail 100

# Reiniciar worker
docker compose restart worker
```
