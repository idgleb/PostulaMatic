# 🚀 Cómo Aumentar CPU en Servidor Hetzner

## 🔍 Situación Actual

- **Servidor:** CPX11 Jetinno-PostulaMatic
- **CPU:** 1 vCPU (al 100-200% de uso)
- **ID:** #104714948
- **IP:** 178.156.188.95

## ✅ Opción 1: Escalar desde la Consola Web (Más Fácil)

### Pasos:

1. **Ir a la Consola de Hetzner:**
   - https://console.hetzner.cloud/
   - Seleccionar el proyecto "jetinno,PostulaMatic"

2. **Seleccionar el Servidor:**
   - Ir a "Servers" → "CPX11 Jetinno-PostulaMatic"

3. **Ir a la Pestaña "Rescale":**
   - En la barra de pestañas, hacer clic en "Rescale"

4. **Seleccionar Nuevo Tipo de Servidor:**
   - **CPX11** → 1 vCPU, 2 GB RAM (actual)
   - **CPX21** → 2 vCPU, 4 GB RAM ⭐ **Recomendado**
   - **CPX31** → 3 vCPU, 8 GB RAM
   - **CPX41** → 4 vCPU, 16 GB RAM
   - **CPX51** → 8 vCPU, 32 GB RAM

5. **Confirmar el Rescale:**
   - El servidor se reiniciará automáticamente
   - ⚠️ **IMPORTANTE:** El servidor estará offline durante unos minutos

### ⚠️ Advertencias:

- **El servidor se reiniciará** (downtime de 2-5 minutos)
- **La IP no cambia** (se mantiene igual)
- **Los datos se mantienen** (no se pierden)
- **El precio aumenta** según el nuevo tipo

## ✅ Opción 2: Usar la API de Hetzner (Avanzado)

### Instalar CLI de Hetzner:

```bash
# Instalar hcloud CLI
# En Windows (PowerShell):
# Descargar desde: https://github.com/hetznercloud/cli/releases

# O usar Chocolatey:
choco install hcloud-cli

# O usar Scoop:
scoop install hcloud
```

### Configurar API Token:

1. **Obtener API Token:**
   - Ir a: https://console.hetzner.cloud/projects
   - Seleccionar el proyecto
   - Ir a "Security" → "API Tokens"
   - Crear nuevo token o usar uno existente

2. **Configurar CLI:**
   ```bash
   hcloud context create postulamatic
   # Ingresar el API token cuando se solicite
   ```

### Escalar el Servidor:

```bash
# Ver servidores disponibles
hcloud server list

# Ver tipos de servidor disponibles
hcloud server-type list

# Escalar el servidor (ejemplo: a CPX21)
hcloud server resize --type cpx21 "CPX11 Jetinno-PostulaMatic"

# O por ID:
hcloud server resize --type cpx21 104714948
```

## 📊 Comparación de Tipos de Servidor

| Tipo | vCPU | RAM | Precio/mes (aprox) | Uso Recomendado |
|------|------|-----|-------------------|-----------------|
| **CPX11** | 1 | 2 GB | ~€4 | Desarrollo, bajo tráfico |
| **CPX21** | 2 | 4 GB | ~€8 | ⭐ **Producción pequeña** |
| **CPX31** | 3 | 8 GB | ~€16 | Producción media |
| **CPX41** | 4 | 16 GB | ~€32 | Producción alta |
| **CPX51** | 8 | 32 GB | ~€64 | Producción muy alta |

## 🎯 Recomendación para PostulaMatic

### Para el Uso Actual:

**CPX21 (2 vCPU, 4 GB RAM)** es una buena opción porque:
- ✅ **Doble CPU** → Resuelve el problema de 100% de uso
- ✅ **Doble RAM** → Mejor rendimiento para Django + Docker
- ✅ **Precio razonable** → ~€8/mes
- ✅ **Suficiente** para la mayoría de aplicaciones Django

### Si el Tráfico Aumenta:

- **CPX31** (3 vCPU, 8 GB RAM) si necesitas más recursos
- **CPX41** (4 vCPU, 16 GB RAM) para alto tráfico

## 📋 Pasos Recomendados

### 1. Preparar el Servidor (Antes del Rescale)

```bash
# Conectarse al servidor
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95

# Verificar uso actual
htop
# O
docker stats

# Hacer backup de datos importantes (si es necesario)
cd /home/deploy/apps/postulamatic
docker compose down
# (Los datos en volúmenes Docker se mantienen)
```

### 2. Escalar desde la Consola

1. Ir a: https://console.hetzner.cloud/
2. Servers → CPX11 Jetinno-PostulaMatic
3. Pestaña "Rescale"
4. Seleccionar "CPX21" (2 vCPU, 4 GB RAM)
5. Confirmar

### 3. Esperar el Rescale

- ⏱️ Tiempo estimado: **2-5 minutos**
- El servidor se reiniciará automáticamente
- La IP no cambia

### 4. Verificar Después del Rescale

```bash
# Conectarse nuevamente
ssh -i ~/.ssh/postulamatic_win_ed25519 deploy@178.156.188.95

# Verificar CPU
nproc  # Debe mostrar 2 (en lugar de 1)

# Verificar RAM
free -h  # Debe mostrar ~4GB

# Reiniciar servicios Docker
cd /home/deploy/apps/postulamatic
docker compose up -d

# Verificar que todo funciona
docker ps
curl -I https://postulamatic.app
```

## ⚠️ Consideraciones Importantes

### Antes de Escalar:

1. **Verificar el Uso Real:**
   - ¿Es uso constante o picos?
   - ¿Hay procesos que consumen mucho CPU?
   - ¿Se puede optimizar el código en lugar de escalar?

2. **Revisar Procesos:**
   ```bash
   # Ver qué consume CPU
   top
   # O
   docker stats
   ```

3. **Optimizar Primero (si es posible):**
   - Optimizar queries de base de datos
   - Reducir procesos en background
   - Optimizar configuración de Docker

### Después de Escalar:

1. **Monitorear el Uso:**
   - Verificar que el CPU baje
   - Verificar que los servicios funcionen correctamente

2. **Ajustar Configuración:**
   - Ajustar workers de Gunicorn si es necesario
   - Ajustar workers de Celery si es necesario

## 🔧 Comandos Útiles

```bash
# Ver CPU actual
nproc

# Ver uso de CPU
htop
# O
top

# Ver uso de Docker
docker stats

# Ver procesos que consumen más CPU
ps aux --sort=-%cpu | head -10

# Ver uso de memoria
free -h

# Ver información del sistema
lscpu
```

## 📝 Notas

- **El rescale es reversible** (puedes volver a CPX11 si es necesario)
- **El precio se calcula por horas** (no necesitas pagar el mes completo)
- **Los datos se mantienen** (no se pierden en el rescale)
- **La IP no cambia** (se mantiene la misma)

## ✅ Resumen Rápido

1. Ir a: https://console.hetzner.cloud/
2. Servers → CPX11 Jetinno-PostulaMatic
3. Pestaña "Rescale"
4. Seleccionar "CPX21" (2 vCPU, 4 GB RAM)
5. Confirmar y esperar 2-5 minutos
6. Verificar que todo funciona

¡Listo! El servidor tendrá más CPU y debería resolver el problema de uso al 100%.

