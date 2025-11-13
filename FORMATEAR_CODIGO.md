# 🔧 Formatear Código con Black

## 📋 Problema

GitHub Actions está fallando porque hay 77 archivos que necesitan ser formateados con Black.

## ✅ Solución

### Opción 1: Ejecutar Black Localmente (Recomendado)

Si tienes Black instalado localmente:

```bash
# Instalar Black si no lo tienes
pip install black

# Formatear todos los archivos
black --line-length 88 .

# Verificar cambios
git status

# Hacer commit
git add .
git commit -m "Format: Aplicar formateo Black a todos los archivos"
git push origin master
```

### Opción 2: Dejar que GitHub Actions lo Formatee

GitHub Actions ejecutará Black automáticamente, pero fallará si hay errores de sintaxis.

**Ya se corrigieron los errores de sintaxis en:**
- `matching/tasks_advanced_backup.py` (línea 51)
- `matching/tasks_backup.py` (línea 205)

### Opción 3: Configurar Pre-commit Hook

Para evitar este problema en el futuro, puedes configurar un pre-commit hook:

```bash
# Instalar pre-commit
pip install pre-commit

# Crear .pre-commit-config.yaml (si no existe)
# Agregar configuración de Black

# Instalar hooks
pre-commit install
```

## 📝 Nota

Los archivos `tasks_advanced_backup.py` y `tasks_backup.py` tenían código deprecado que causaba errores de sintaxis. Se comentó el código problemático para que Black pueda parsear los archivos correctamente.

