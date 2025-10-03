# 🔐 Configuración de GitHub Secrets para Despliegue Automático

## 📋 Secrets Requeridos en GitHub

Para que el despliegue automático funcione, necesitas configurar los siguientes secrets en tu repositorio de GitHub:

### 1. SSH_PRIVATE_KEY
**Descripción:** Clave privada SSH para conectarse al servidor

**Cómo obtenerla:**
```bash
# En tu servidor (178.156.188.95), ejecutar:
ssh-keygen -t ed25519 -C "deploy@github-actions"
cat ~/.ssh/id_ed25519  # Copiar el contenido completo
```

**Configurar en GitHub:**
1. Ve a tu repositorio en GitHub
2. Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `SSH_PRIVATE_KEY`
5. Value: Contenido completo de la clave privada

### 2. (Opcional) DATABASE_URL
**Descripción:** URL de conexión a la base de datos PostgreSQL

**Formato:**
```
postgresql://usuario:password@localhost:5432/postulamatic_db
```

### 3. (Opcional) ENCRYPTION_KEY
**Descripción:** Clave de encriptación para credenciales sensibles

**Valor por defecto (ya incluido en el proyecto):**
```
f9c7e79694bd5c9e353d26fdbce8a2e06f10a14a86cab7a553fb207f977d8108
```

## 🚀 Pasos para Configurar

### Paso 1: Generar Clave SSH en el Servidor
```bash
# Conectarse al servidor
ssh deploy@178.156.188.95

# Generar nueva clave SSH
ssh-keygen -t ed25519 -C "deploy@github-actions"
# Presionar Enter para usar ubicación por defecto
# Presionar Enter para no usar passphrase

# Mostrar la clave privada
cat ~/.ssh/id_ed25519
```

### Paso 2: Configurar Autorización en el Servidor
```bash
# En el servidor, agregar la clave pública al authorized_keys
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys

# Asegurar permisos correctos
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### Paso 3: Configurar Secret en GitHub
1. Ve a: `https://github.com/idgleb/PostulaMatic/settings/secrets/actions`
2. Click "New repository secret"
3. Name: `SSH_PRIVATE_KEY`
4. Value: Contenido completo de `~/.ssh/id_ed25519` del servidor

### Paso 4: Probar Conexión
```bash
# En tu máquina local, probar conexión
ssh -i ~/.ssh/jetinnohetzner_ed25519 deploy@178.156.188.95 "echo 'Conexión SSH exitosa'"
```

## 🔧 Configuración del Servidor

### Verificar Docker y Docker Compose
```bash
# En el servidor
docker --version
docker-compose --version
```

### Configurar Variables de Entorno
```bash
# En el servidor, crear archivo .env
cd /home/deploy/PostulaMatic
cp env.production.example .env
nano .env  # Editar con valores reales
```

### Variables Críticas en .env:
```bash
SECRET_KEY=tu_secret_key_muy_seguro
DEBUG=False
ALLOWED_HOSTS=178.156.188.95,tu_dominio.com
DATABASE_URL=postgresql://usuario:password@localhost:5432/postulamatic_db
REDIS_URL=redis://localhost:6379/0
ENCRYPTION_KEY=f9c7e79694bd5c9e353d26fdbce8a2e06f10a14a86cab7a553fb207f977d8108
```

## 🎯 Activación del Despliegue Automático

### Opción 1: Push a Master (Automático)
```bash
# Cualquier push a la rama master activará el despliegue
git push origin master
```

### Opción 2: Ejecución Manual
1. Ve a: `https://github.com/idgleb/PostulaMatic/actions`
2. Click en "Deploy to Production Server"
3. Click "Run workflow"

## 📊 Monitoreo del Despliegue

### Ver Logs de GitHub Actions
1. Ve a: `https://github.com/idgleb/PostulaMatic/actions`
2. Click en el workflow que se está ejecutando
3. Click en el job "deploy"
4. Ver logs en tiempo real

### Ver Logs del Servidor
```bash
# Conectarse al servidor
ssh deploy@178.156.188.95

# Ver logs de Docker
docker-compose logs -f

# Ver estado de contenedores
docker-compose ps
```

## 🚨 Solución de Problemas

### Error: "Permission denied (publickey)"
- Verificar que la clave SSH está configurada correctamente
- Verificar que la clave pública está en `~/.ssh/authorized_keys`
- Verificar permisos: `chmod 600 ~/.ssh/authorized_keys`

### Error: "No such file or directory"
- Verificar que el directorio `/home/deploy/PostulaMatic` existe
- El workflow creará el directorio automáticamente si no existe

### Error: "Docker not found"
- Instalar Docker y Docker Compose en el servidor
- Agregar el usuario `deploy` al grupo `docker`

### Error: "Environment variables not set"
- Verificar que el archivo `.env` existe en el servidor
- Verificar que contiene todas las variables requeridas

## ✅ Verificación Final

Una vez configurado, el flujo debería ser:

1. **Push a master** → GitHub Actions se activa
2. **Tests pasan** → Deploy al servidor
3. **Servidor actualizado** → Aplicación funcionando
4. **Verificación automática** → Servicios OK

Para verificar que todo funciona:
```bash
# Verificar que la aplicación responde
curl http://178.156.188.95:8000/

# Ver logs de GitHub Actions
# Ir a: https://github.com/idgleb/PostulaMatic/actions
```
