# ⚡ Solución Rápida: Estado DV Infinito

## 🚨 **Problema**
La página de perfil muestra infinitamente: **"EN PROCESO"** sin terminar nunca.

---

## ✅ **Solución Inmediata (30 segundos)**

### **Opción 1: Script Automatizado (Windows)**

```powershell
.\scripts\reset_dv_status.ps1
```

### **Opción 2: Script Automatizado (Linux/Mac)**

```bash
bash scripts/reset_dv_status.sh
```

### **Opción 3: Comando Manual**

```bash
docker exec postulamatic-postulamatic_web-1 python manage.py shell -c "from matching.models import UserProfile; p = UserProfile.objects.get(user_id=2); p.dv_connection_status = 'not_verified'; p.save(); print('✅ Estado reseteado')"
```

Cambia `user_id=2` por tu ID de usuario si es diferente.

---

## 🔄 **Después de Resetear**

1. **Refresca la página** (F5)
2. El bucle debería detenerse
3. Verás **"NO VERIFICADO"**
4. Ahora el timeout máximo es **2 minutos**

---

## 🛡️ **Protección Agregada**

### **Nuevo Timeout Automático**

El frontend ahora tiene un **timeout de 2 minutos**:

- Si la verificación no termina en 2 minutos
- El polling se detiene automáticamente
- Muestra mensaje: **"Timeout - Inténtalo de nuevo"**
- No más bucles infinitos

---

## 📊 **Cómo Debería Funcionar Ahora**

```
Click "Probar Conexión DV"
  ↓
Estado: "EN PROCESO" (máximo 2 minutos)
  ↓
Opción A: Termina exitosamente → "VERIFICADO" ✅
Opción B: Falla → "NO VERIFICADO" ❌
Opción C: Timeout (2 min) → "Timeout - Inténtalo de nuevo" ⏱️
```

---

## 🔍 **Si el Problema Persiste**

### **1. Verificar Worker**
```bash
docker ps | Select-String "worker"
```

Si no está corriendo:
```bash
docker restart postulamatic-worker-1
```

### **2. Verificar Tareas Atascadas**
```bash
docker exec postulamatic-worker-1 celery -A postulamatic purge
```

### **3. Verificar Estado en BD**
```bash
docker exec postulamatic-postulamatic_web-1 python manage.py shell -c "from matching.models import UserProfile; p = UserProfile.objects.get(user_id=2); print(p.dv_connection_status)"
```

---

## 🛠️ **Cambios Aplicados**

| Cambio | Archivo | Estado |
|--------|---------|--------|
| Timeout 2 minutos | `profile.html` | ✅ Aplicado |
| Scraper STEALTH | `tasks_dv.py` | ✅ Aplicado |
| Scripts de reset | `scripts/` | ✅ Creados |

---

## 💡 **Recomendación**

**Por ahora, NO uses la verificación DV automática.**

En su lugar:
1. Ve directo a http://localhost:8000/matching/probar-scraper/
2. Usa el scraper que ya funciona al 100%
3. Las credenciales DV no necesitan verificación previa

---

## 📞 **Ayuda Adicional**

Si después de resetear el estado aún ves el bucle:

```powershell
# Windows
.\scripts\reset_dv_status.ps1
# Luego refresca la página (F5)
```

```bash
# Linux/Mac
bash scripts/reset_dv_status.sh
# Luego refresca la página (F5)
```

---

## ✅ **Resumen**

- ✅ Estado se puede resetear con 1 comando
- ✅ Timeout automático de 2 minutos agregado
- ✅ Scripts de emergencia creados
- ✅ Scraper principal funciona sin verificación DV

**El scraper en `/probar-scraper/` funciona perfectamente.**

---

*Solución actualizada el 19 de Octubre de 2025*

