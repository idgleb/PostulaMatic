# 🍪 SOLUCIÓN: "Cookie omitida (dominio no válido)"

## 📊 **PROBLEMA IDENTIFICADO:**

### ❌ **Síntoma:**
```
⚠️ Cookie 'cf_clearance' omitida (dominio no válido)
⚠️ Cookie 'PHPSESSID' omitida (dominio no válido)
Sesión guardada expirada, se requiere nuevo login
```

### 🔍 **Causa raíz:**
**Las cookies se guardan con dominios que el navegador no puede cargar posteriormente.**

---

## 🎯 **DIAGNÓSTICO COMPLETO:**

### ✅ **Lo que estaba BIEN:**
- **Cookies presentes**: `PHPSESSID` y `cf_clearance` guardadas
- **Dominios guardados**: `.davinci.edu.ar` y `dvcarreras.davinci.edu.ar`
- **Tiempo válido**: Solo 6 minutos de antigüedad

### ❌ **El problema real:**
**Incompatibilidad de dominios entre guardado y carga**:
- **Al guardar**: Dominios como `.davinci.edu.ar` y `dvcarreras.davinci.edu.ar`
- **Al cargar**: El navegador rechaza estos dominios como "inválidos"

---

## ✅ **SOLUCIÓN IMPLEMENTADA:**

### 🔄 **1. Normalización al guardar cookies:**
```python
# ANTES (PROBLEMÁTICO):
cookies = self.driver.get_cookies()  # Dominios variables

# AHORA (NORMALIZADO):
normalized_cookies = []
for cookie in cookies:
    normalized_cookie = cookie.copy()
    
    # Normalizar dominio para dvcarreras
    if 'dvcarreras.davinci.edu.ar' in cookie.get('domain', ''):
        normalized_cookie['domain'] = 'dvcarreras.davinci.edu.ar'
    elif '.davinci.edu.ar' in cookie.get('domain', ''):
        normalized_cookie['domain'] = '.davinci.edu.ar'
    
    # Asegurar que el path sea válido
    if not normalized_cookie.get('path'):
        normalized_cookie['path'] = '/'
    
    normalized_cookies.append(normalized_cookie)
```

### 🔄 **2. Carga inteligente con fallback:**
```python
# Intentar cargar cookie tal como está
try:
    self.driver.add_cookie(cookie)
    # ✅ Éxito
except Exception:
    # Si falla, intentar con dominios normalizados
    domains_to_try = [
        'dvcarreras.davinci.edu.ar',
        '.davinci.edu.ar',
        '.dvcarreras.davinci.edu.ar'
    ]
    
    for domain in domains_to_try:
        try:
            normalized_cookie['domain'] = domain
            self.driver.add_cookie(normalized_cookie)
            # ✅ Éxito con dominio normalizado
            break
        except Exception:
            continue
```

---

## 🛠️ **CAMBIOS REALIZADOS:**

### **1. Guardado normalizado** (Líneas 370-385):
- **Normaliza dominios** antes de guardar
- **Asegura paths válidos** (`/` por defecto)
- **Mantiene compatibilidad** con diferentes formatos

### **2. Carga inteligente** (Líneas 439-478):
- **Intenta cargar** cookie original primero
- **Fallback automático** con dominios normalizados
- **Múltiples intentos** con diferentes dominios
- **Logs detallados** de cada intento

### **3. Debugging mejorado**:
- **Logs de cada cookie** individualmente
- **Dominios probados** en caso de fallo
- **Resultado final** con contadores precisos

---

## 📈 **BENEFICIOS:**

✅ **Compatibilidad mejorada**: Maneja diferentes formatos de dominio  
✅ **Fallback automático**: Intenta múltiples dominios si falla  
✅ **Logs informativos**: Muestra exactamente qué está pasando  
✅ **Robustez**: No falla por diferencias menores en dominios  
✅ **Normalización**: Cookies guardadas con formato consistente  

---

## 🚀 **PRÓXIMA PRUEBA:**

### **Paso 1: Sesión limpia** ✅
```bash
# Sesión anterior eliminada
rm media/sessions/user_2_stealth_session.json
```

### **Paso 2: Probar scraping**
1. Ir a: `http://localhost:8000/matching/probar-scraper/`
2. Hacer scraping
3. **Primera vez**: Debería hacer login completo y guardar con dominios normalizados
4. **Segunda vez**: Debería cargar cookies exitosamente ✅

### **Paso 3: Verificar logs esperados**
```
✅ Cookie 'cf_clearance' cargada exitosamente
✅ Cookie 'PHPSESSID' cargada exitosamente
✅ Sesión cargada: 2 cookies activas
✅ Sesión válida - no redirigido a login
```

---

## 🔧 **HERRAMIENTAS DE DIAGNÓSTICO:**

### **Script de diagnóstico actualizado:**
```bash
python scripts/diagnostico_sesion.py
```

**Ahora muestra:**
- Dominios normalizados de las cookies
- Compatibilidad con diferentes formatos
- Paths válidos asegurados

---

## 📝 **RESUMEN:**

| Aspecto | Antes | Ahora |
|---------|-------|-------|
| **Guardado** | Dominios variables | Dominios normalizados |
| **Carga** | Un intento, falla si no coincide | Múltiples intentos con fallback |
| **Compatibilidad** | Rígida | Flexible con múltiples formatos |
| **Debugging** | Básico | Detallado con cada intento |
| **Robustez** | Frágil | Resistente a variaciones |

---

## 🎊 **RESULTADO ESPERADO:**

**Antes:**
```
⚠️ Cookie 'cf_clearance' omitida (dominio no válido)
⚠️ Cookie 'PHPSESSID' omitida (dominio no válido)
Sesión guardada expirada, se requiere nuevo login
```

**Ahora:**
```
✅ Cookie 'cf_clearance' cargada exitosamente
✅ Cookie 'PHPSESSID' cargada exitosamente
✅ Sesión cargada: 2 cookies activas
✅ Sesión válida - no redirigido a login
```

**¡El scraper ahora debería reutilizar sesiones correctamente sin problemas de dominio!** 🎯✨

