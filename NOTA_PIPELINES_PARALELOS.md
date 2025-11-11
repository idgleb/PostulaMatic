# 📝 Nota: Pipelines Paralelos en GitHub Actions

## 🔍 ¿Por qué hay dos pipelines ejecutándose?

Cuando haces **múltiples commits y pushes** en poco tiempo, GitHub Actions ejecuta un pipeline por cada push.

### En este caso:
1. **Commit 1:** `f1fb046` - "Test: Verificar fix..." → **Pipeline #199**
2. **Commit 2:** `76fb556` - "Agregar documento..." → **Pipeline #200**

Ambos se ejecutan en paralelo porque ambos activan el workflow.

## ✅ ¿Está bien?

**Sí, está bien, pero no es óptimo:**

### Ventajas:
- ✅ Ambos pipelines verifican los cambios
- ✅ Si uno falla, el otro puede pasar
- ✅ No hay riesgo de datos o código

### Desventajas:
- ⚠️ Duplica recursos (CPU, tiempo)
- ⚠️ Ejecuta los mismos tests dos veces
- ⚠️ Puede saturar el servidor si hay muchos commits

## 🎯 Mejor Práctica

### Opción 1: Un Solo Commit (Recomendado)
```bash
# En lugar de:
git commit --allow-empty -m "Test: ..."
git push
git add archivo.md
git commit -m "Agregar documento"
git push

# Hacer:
git add archivo.md
git commit -m "Test: Verificar fix y agregar documento"
git push
```

### Opción 2: Usar `[skip ci]` o `[ci skip]`
Si necesitas hacer commits que no deben activar el pipeline:
```bash
git commit -m "Actualizar README [skip ci]"
```

### Opción 3: Amasar Commits (Squash)
Combinar múltiples commits antes de hacer push:
```bash
git rebase -i HEAD~2  # Combinar últimos 2 commits
# O usar: git commit --amend
```

## 📋 Para este Caso Específico

**No es necesario hacer nada.** Los dos pipelines se ejecutarán y:
- ✅ Verificarán que el fix funciona
- ✅ Si ambos pasan, confirma que todo está bien
- ✅ Si uno falla, revisa los logs para ver por qué

## 🔧 En el Futuro

Para evitar pipelines paralelos:
1. **Agrupa cambios relacionados** en un solo commit
2. **Haz push una vez** con todos los cambios
3. **Usa `[skip ci]`** para commits que no necesitan CI/CD

## ✅ Conclusión

**Está bien tener dos pipelines en paralelo**, pero para optimizar recursos, es mejor hacer un solo commit con todos los cambios relacionados.

