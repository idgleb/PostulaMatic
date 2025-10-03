# 🚀 Guía de Despliegue - PostulaMatic

## 📋 Prerequisitos

### En el Servidor:
- Docker y Docker Compose instalados
- Git configurado
- PostgreSQL (si no usas contenedor)
- Redis (si no usas contenedor)

### Variables de Entorno Requeridas:
```bash
# Django
SECRET_KEY=tu_secret_key_muy_seguro
DEBUG=False
ALLOWED_HOSTS=tu_dominio.com,www.tu_dominio.com

# Base de datos
DATABASE_URL=postgresql://usuario:password@localhost:5432/postulamatic_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Encriptación (IMPORTANTE: Usar la misma clave en todos los entornos)
ENCRYPTION_KEY=f9c7e79694bd5c9e353d26fdbce8a2e06f10a14a86cab7a553fb207f977d8108
```

## 🚀 Despliegue Automatizado

### Opción 1: Script Automatizado (Recomendado)
```bash
# 1. Clonar el repositorio
git clone https://github.com/idgleb/PostulaMatic.git
cd PostulaMatic

# 2. Configurar variables de entorno
cp env.production.example .env
nano .env  # Editar con tus valores reales

# 3. Hacer ejecutable y ejecutar el script de despliegue
chmod +x deploy.sh
./deploy.sh
```

### Opción 2: Comandos Manuales
```bash
# 1. Actualizar código
git pull origin master

# 2. Detener contenedores
docker-compose down

# 3. Reconstruir con nuevas dependencias
docker-compose build --no-cache

# 4. Iniciar servicios
docker-compose up -d

# 5. Aplicar migraciones
docker-compose exec postulamatic_web python manage.py migrate

# 6. Recopilar archivos estáticos
docker-compose exec postulamatic_web python manage.py collectstatic --noinput
```

## 🔍 Verificación Post-Despliegue

```bash
# Ejecutar script de verificación
chmod +x verify_deployment.sh
./verify_deployment.sh
```

### Verificaciones Manuales:
1. **Servicio Web**: http://tu-dominio.com
2. **Admin Django**: http://tu-dominio.com/admin/
3. **Logs**: `docker-compose logs -f`
4. **Estado Contenedores**: `docker-compose ps`

## 🔧 Dependencias Nuevas Instaladas

### Python Packages:
- `cryptography` - Encriptación de credenciales
- `playwright` - Scraping con navegador
- `django-celery-beat` - Tareas programadas
- `redis` - Colas de tareas

### Playwright Navegadores:
```bash
# Se instalan automáticamente en el Dockerfile
RUN playwright install --with-deps
```

## 🗄️ Migraciones de Base de Datos

### Nuevas Migraciones:
1. `0003_encrypt_existing_credentials.py` - Encripta credenciales existentes
2. `0004_userprofile_dv_connection_status.py` - Agrega estado de conexión DV

### Verificar Migraciones:
```bash
docker-compose exec postulamatic_web python manage.py showmigrations
```

## 🔐 Configuración de Encriptación

### Generar Nueva Clave (si es necesario):
```bash
python -c "import os; print('ENCRYPTION_KEY=' + os.urandom(32).hex())"
```

### ⚠️ IMPORTANTE:
- **NUNCA** cambies la clave de encriptación en producción si ya tienes datos
- La misma clave debe usarse en desarrollo y producción
- Mantén la clave segura y respaldada

## 📊 Servicios que Deben Funcionar

### Contenedores Requeridos:
1. **postulamatic_web** - Aplicación Django
2. **worker** - Celery Worker para tareas en background
3. **beat** - Celery Beat para tareas programadas
4. **redis** - Cola de mensajes

### Verificar Servicios:
```bash
# Estado general
docker-compose ps

# Logs específicos
docker-compose logs postulamatic_web
docker-compose logs worker
docker-compose logs beat
docker-compose logs redis
```

## 🚨 Solución de Problemas

### Error: "ENCRYPTION_KEY not set"
```bash
# Verificar que .env existe y tiene la variable
cat .env | grep ENCRYPTION_KEY
```

### Error: "Playwright browsers not installed"
```bash
# Reinstalar navegadores
docker-compose exec postulamatic_web playwright install --with-deps
```

### Error: "Database connection failed"
```bash
# Verificar DATABASE_URL en .env
# Verificar que PostgreSQL está corriendo
docker-compose exec postulamatic_web python manage.py check --database default
```

### Error: "Redis connection failed"
```bash
# Verificar Redis
docker-compose exec redis redis-cli ping
```

## 📝 Logs y Monitoreo

### Ver Logs en Tiempo Real:
```bash
docker-compose logs -f
```

### Logs Específicos:
```bash
docker-compose logs -f postulamatic_web
docker-compose logs -f worker
```

### Reiniciar Servicio:
```bash
docker-compose restart postulamatic_web
```

## 🔄 Actualizaciones Futuras

Para futuras actualizaciones:
1. `git pull origin master`
2. `./deploy.sh` (o comandos manuales)
3. `./verify_deployment.sh`

## 📞 Soporte

Si encuentras problemas:
1. Revisar logs: `docker-compose logs -f`
2. Verificar variables de entorno
3. Ejecutar script de verificación
4. Revisar esta documentación
