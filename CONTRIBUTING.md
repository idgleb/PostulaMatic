# 🤝 Guía de Contribución a PostulaMatic

¡Gracias por tu interés en contribuir a PostulaMatic! Este documento te guiará a través del proceso.

---

## 📋 Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [¿Cómo puedo contribuir?](#cómo-puedo-contribuir)
- [Proceso de Desarrollo](#proceso-de-desarrollo)
- [Estándares de Código](#estándares-de-código)
- [Estructura de Commits](#estructura-de-commits)
- [Tests](#tests)
- [Documentación](#documentación)

---

## 📜 Código de Conducta

Este proyecto y todos los participantes están gobernados por nuestro Código de Conducta. Al participar, se espera que mantengas este código. Por favor reporta comportamientos inaceptables a [idgleb646807@gmail.com](mailto:idgleb646807@gmail.com).

---

## 🚀 ¿Cómo puedo contribuir?

### 🐛 Reportar Bugs

Antes de crear un issue de bug, por favor:

1. **Verifica** que el bug no haya sido reportado previamente
2. **Reúne información** sobre el bug:
   - Versión de Python y Django
   - Sistema operativo
   - Pasos para reproducir
   - Comportamiento esperado vs. actual
   - Screenshots si aplica

**Template de Bug Report:**
```markdown
### Descripción del Bug
[Descripción clara y concisa]

### Pasos para Reproducir
1. Ir a '...'
2. Hacer clic en '...'
3. Scroll hasta '...'
4. Ver error

### Comportamiento Esperado
[Lo que debería pasar]

### Screenshots
[Si aplica]

### Entorno
- OS: [ej. Ubuntu 22.04]
- Python: [ej. 3.12.1]
- Django: [ej. 5.2.6]
- Docker: [ej. 24.0.5]
```

### 💡 Sugerir Mejoras

Las sugerencias de features son bienvenidas! Por favor:

1. **Describe** el problema actual que la feature resolvería
2. **Explica** la solución propuesta
3. **Detalla** casos de uso
4. **Considera** alternativas

**Template de Feature Request:**
```markdown
### Problema a Resolver
[Descripción del problema]

### Solución Propuesta
[Cómo lo resolverías]

### Alternativas Consideradas
[Otras opciones que consideraste]

### Información Adicional
[Contexto, screenshots, etc.]
```

### 🔧 Pull Requests

1. **Fork** el repositorio
2. Crea una **rama feature** desde `master`:
   ```bash
   git checkout -b feature/nombre-descriptivo
   ```
3. **Implementa** tu cambio
4. **Agrega tests** si aplica
5. **Verifica** que los tests pasen
6. **Formatea** el código con Black e isort
7. **Commit** con mensajes descriptivos
8. **Push** a tu fork
9. Abre un **Pull Request**

---

## 🛠️ Proceso de Desarrollo

### 1. Setup del Entorno

```bash
# Clonar tu fork
git clone https://github.com/TU-USUARIO/PostulaMatic.git
cd PostulaMatic

# Agregar upstream remote
git remote add upstream https://github.com/idgleb/PostulaMatic.git

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Configurar variables de entorno
cp .env.example .env
nano .env  # Completar con tus claves

# Ejecutar migraciones
docker-compose up -d redis
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Iniciar servidor de desarrollo
python manage.py runserver
```

### 2. Mantener tu Fork Actualizado

```bash
# Obtener últimos cambios del upstream
git fetch upstream

# Mergear cambios a tu rama master
git checkout master
git merge upstream/master

# Pushear a tu fork
git push origin master
```

### 3. Trabajar en una Feature

```bash
# Crear rama desde master actualizado
git checkout master
git pull upstream master
git checkout -b feature/mi-nueva-feature

# Hacer cambios...

# Agregar archivos
git add .

# Commit con mensaje descriptivo
git commit -m "feat: agregar validacion de email personalizada"

# Push a tu fork
git push origin feature/mi-nueva-feature
```

---

## 📝 Estándares de Código

### Python Style Guide

Seguimos **PEP 8** con las siguientes herramientas:

#### **Black** (Formateo)
```bash
# Formatear todo el proyecto
black --line-length 88 .

# Formatear archivo específico
black matching/views.py

# Verificar sin modificar
black --check .
```

#### **isort** (Ordenamiento de Imports)
```bash
# Ordenar imports
isort .

# Verificar sin modificar
isort --check-only .
```

Configuración en `pyproject.toml`:
```toml
[tool.black]
line-length = 88
target-version = ['py312']

[tool.isort]
profile = "black"
line_length = 88
known_first_party = ["matching", "postulamatic"]
```

#### **Ruff** (Linting)
```bash
# Lint todo el proyecto
ruff check .

# Auto-fix errores simples
ruff check --fix .
```

### Convenciones de Nomenclatura

- **Variables y funciones:** `snake_case`
- **Clases:** `PascalCase`
- **Constantes:** `UPPER_SNAKE_CASE`
- **Archivos:** `snake_case.py`
- **Modelos Django:** `PascalCase` (singular)
- **URLs:** `kebab-case`

### Docstrings

Usar formato **Google Style**:

```python
def calculate_match_score(cv_skills: List[str], job_skills: List[str]) -> int:
    """
    Calcula el score de coincidencia entre un CV y un puesto.

    Args:
        cv_skills: Lista de habilidades del CV.
        job_skills: Lista de habilidades requeridas por el puesto.

    Returns:
        Score de 0 a 100 indicando el nivel de coincidencia.

    Raises:
        ValueError: Si las listas están vacías.

    Example:
        >>> calculate_match_score(["Python", "Django"], ["Python", "Flask"])
        50
    """
    # Implementación...
```

---

## 📋 Estructura de Commits

Seguimos **Conventional Commits**:

### Formato
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Tipos

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `feat` | Nueva funcionalidad | `feat(matching): agregar algoritmo de matching semantico` |
| `fix` | Corrección de bug | `fix(scraper): corregir decodificacion de emails Cloudflare` |
| `docs` | Documentación | `docs(readme): actualizar guia de instalacion` |
| `style` | Formateo, punto y coma | `style: aplicar Black a todos los archivos` |
| `refactor` | Refactorización | `refactor(cv_parser): simplificar logica de extraccion` |
| `test` | Agregar/modificar tests | `test(matching): agregar tests para ATS matcher` |
| `chore` | Tareas de mantenimiento | `chore(deps): actualizar Django a 5.2.7` |
| `perf` | Mejora de performance | `perf(scraper): optimizar consultas de BD` |

### Ejemplos de Commits

✅ **Buenos:**
```
feat(email): agregar soporte para templates HTML
fix(scraper): manejar timeout en login DV
docs(contributing): agregar guia de commits
```

❌ **Malos:**
```
update stuff
fix bug
cambios
WIP
```

### Commit Message Completo

```
feat(matching): implementar matching semantico con embeddings

- Agregar servicio de embeddings con OpenAI
- Calcular similitud coseno entre CV y puesto
- Combinar score de keywords con score semantico
- Agregar tests unitarios

Closes #42
```

---

## 🧪 Tests

### Ejecutar Tests

```bash
# Todos los tests
python manage.py test

# Tests de una app específica
python manage.py test matching

# Tests de un módulo específico
python manage.py test matching.tests.test_services

# Con cobertura
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html
```

### Escribir Tests

**Ubicación:** `matching/tests/`

```python
from django.test import TestCase
from matching.services.ats_matcher import calculate_match_score


class ATSMatcherTestCase(TestCase):
    """Tests para el servicio de matching ATS."""

    def setUp(self):
        """Setup común para todos los tests."""
        self.cv_skills = ["Python", "Django", "PostgreSQL"]
        self.job_skills = ["Python", "Django", "React"]

    def test_perfect_match(self):
        """Test con match perfecto (100%)."""
        score = calculate_match_score(
            cv_skills=["Python", "Django"],
            job_skills=["Python", "Django"]
        )
        self.assertEqual(score, 100)

    def test_partial_match(self):
        """Test con match parcial."""
        score = calculate_match_score(
            cv_skills=self.cv_skills,
            job_skills=self.job_skills
        )
        self.assertGreater(score, 0)
        self.assertLess(score, 100)

    def test_no_match(self):
        """Test sin coincidencias."""
        score = calculate_match_score(
            cv_skills=["Python"],
            job_skills=["Java"]
        )
        self.assertEqual(score, 0)
```

### Cobertura Mínima

- **Nueva funcionalidad:** 80% de cobertura
- **Servicios críticos:** 90% de cobertura
- **Views:** 70% de cobertura

---

## 📚 Documentación

### Actualizar Documentación

Si tu PR introduce:

- **Nueva funcionalidad** → Actualizar README.md y docs/
- **Cambios en API** → Actualizar documentación de API
- **Nuevos settings** → Actualizar .env.example
- **Cambios en modelos** → Actualizar diagrama de BD

### Documentación de Código

```python
# ✅ Bueno: Código auto-explicativo con docstring
def send_personalized_email(user: User, job: JobPosting) -> bool:
    """
    Envía un email personalizado a una oferta de trabajo.

    Genera una carta de presentación con IA y envía el email
    desde la cuenta SMTP del usuario.

    Args:
        user: Usuario que postula.
        job: Oferta de trabajo.

    Returns:
        True si el email se envió exitosamente, False en caso contrario.
    """
    # Implementación...
```

```python
# ❌ Malo: Código confuso que requiere comentarios
def proc(u, j):  # Procesa usuario y job
    # Obtener config
    c = u.profile
    # Generar email
    e = gen_email(u, j)  # Genera con IA
    # Enviar
    return send(e)
```

---

## 🔍 Revisión de Pull Requests

### Checklist para PR

Antes de abrir tu PR, verifica:

- [ ] El código sigue los estándares de estilo (Black, isort, Ruff)
- [ ] Los tests pasan
- [ ] Se agregaron tests para nueva funcionalidad
- [ ] La documentación está actualizada
- [ ] Los commits siguen Conventional Commits
- [ ] No hay conflictos con `master`
- [ ] El PR tiene una descripción clara
- [ ] Se referencian issues relacionados

### Template de Pull Request

```markdown
## Descripción
[Descripción clara de los cambios]

## Tipo de Cambio
- [ ] Bug fix (cambio no-breaking que corrige un issue)
- [ ] Nueva feature (cambio no-breaking que agrega funcionalidad)
- [ ] Breaking change (fix o feature que causa que funcionalidad existente no funcione)
- [ ] Documentación

## ¿Cómo se ha testeado?
[Describe los tests que ejecutaste]

## Checklist
- [ ] Mi código sigue el style guide del proyecto
- [ ] He revisado mi propio código
- [ ] He comentado mi código en áreas difíciles
- [ ] He actualizado la documentación
- [ ] Mis cambios no generan nuevos warnings
- [ ] He agregado tests que prueban mi fix/feature
- [ ] Tests unitarios nuevos y existentes pasan localmente

## Screenshots (si aplica)
[Agregar screenshots]

## Issues Relacionados
Closes #[issue_number]
```

---

## 🎨 Estándares de UI/UX

### Frontend (Django Templates)

- **Bootstrap 5** para componentes
- **Alpine.js** o **HTMX** para interactividad ligera
- **Mobile-first** design
- **Accesibilidad** (ARIA labels, contrast ratios)

### Buenas Prácticas

- Validación tanto en frontend como backend
- Mensajes de error claros y accionables
- Feedback visual para acciones (spinners, toasts)
- Responsive en todos los dispositivos

---

## 🚀 Proceso de Release

### Versionado Semántico

Seguimos [SemVer](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

- **MAJOR:** Breaking changes
- **MINOR:** Nueva funcionalidad (backward-compatible)
- **PATCH:** Bug fixes (backward-compatible)

### Crear un Release

```bash
# Actualizar versión en __init__.py
echo "__version__ = '1.2.0'" > postulamatic/__init__.py

# Commit y tag
git add .
git commit -m "chore(release): v1.2.0"
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin master --tags
```

---

## 🆘 ¿Necesitas Ayuda?

- 📖 **Documentación:** [docs/](docs/)
- 💬 **Issues:** [GitHub Issues](https://github.com/idgleb/PostulaMatic/issues)
- 📧 **Email:** idgleb646807@gmail.com

---

## 🙏 Agradecimientos

¡Gracias por contribuir a PostulaMatic! Cada contribución, por pequeña que sea, hace que el proyecto sea mejor para todos.

---

<div align="center">

**⭐ Si este proyecto te ayudó, dale una estrella en GitHub! ⭐**

[🏠 Volver al README](README.md)

</div>

