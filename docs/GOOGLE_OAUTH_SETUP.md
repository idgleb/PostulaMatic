# Configuración de Google OAuth para PostulaMatic

## 📋 Pasos para Configurar Google OAuth

### 1. Crear Proyecto en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la API de Google+ (o Google Identity)

### 2. Configurar OAuth Consent Screen

1. En el menú lateral, ve a **APIs & Services** > **OAuth consent screen**
2. Selecciona **External** (para usuarios fuera de tu organización)
3. Completa la información requerida:
   - **App name**: PostulaMatic
   - **User support email**: tu-email@dominio.com
   - **Developer contact information**: tu-email@dominio.com

### 3. Crear Credenciales OAuth

1. Ve a **APIs & Services** > **Credentials**
2. Haz clic en **+ CREATE CREDENTIALS** > **OAuth client ID**
3. Selecciona **Web application**
4. Configura las URLs autorizadas:
   - **Authorized JavaScript origins**:
     - `http://localhost:8000` (desarrollo)
     - `https://postulamatic.app` (producción)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/accounts/google/login/callback/` (desarrollo)
     - `https://postulamatic.app/accounts/google/login/callback/` (producción)

### 4. Obtener Client ID y Client Secret

Después de crear las credenciales, obtendrás:
- **Client ID**: Algo como `123456789-abcdefghijklmnop.apps.googleusercontent.com`
- **Client Secret**: Una cadena de texto larga

### 5. Configurar Variables de Entorno

Agrega estas variables a tu archivo `.env`:

```bash
# Google OAuth
GOOGLE_OAUTH_CLIENT_ID=tu_client_id_aqui
GOOGLE_OAUTH_CLIENT_SECRET=tu_client_secret_aqui
```

### 6. Actualizar Configuración de Django

En `postulamatic/settings.py`, agrega:

```python
# Google OAuth settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
        'APP': {
            'client_id': env('GOOGLE_OAUTH_CLIENT_ID', default=''),
            'secret': env('GOOGLE_OAUTH_CLIENT_SECRET', default=''),
        }
    }
}
```

### 7. Actualizar Provider en Base de Datos

Ejecuta en el shell de Django:

```python
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
import os

site = Site.objects.get(id=1)
google_app = SocialApp.objects.get(provider='google')
google_app.client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '')
google_app.secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', '')
google_app.save()
```

### 8. Actualizar Dominio del Sitio

```python
from django.contrib.sites.models import Site
site = Site.objects.get(id=1)
site.domain = 'postulamatic.app'  # o localhost:8000 para desarrollo
site.name = 'PostulaMatic'
site.save()
```

## 🔧 URLs Disponibles

- **Login con Google**: `/accounts/google/login/`
- **Callback de Google**: `/accounts/google/login/callback/`
- **Logout**: `/accounts/logout/`

## 🎨 Templates Actualizados

Los templates `login.html` y `register.html` ahora incluyen:
- Botón "Continuar con Google" en login
- Botón "Registrarse con Google" en registro
- Estilos CSS consistentes con el diseño del sitio

## 🚀 Estado Actual

- ✅ django-allauth instalado y configurado
- ✅ Migraciones aplicadas
- ✅ Templates actualizados con botones de Google
- ✅ Provider de Google creado en base de datos
- ⏳ **Pendiente**: Configurar credenciales reales de Google OAuth

## 📝 Notas Importantes

1. **Desarrollo vs Producción**: Asegúrate de configurar las URLs correctas según el entorno
2. **Dominio del Sitio**: Actualiza el dominio en la tabla `sites` de Django
3. **Variables de Entorno**: Nunca commites las credenciales reales al repositorio
4. **Testing**: Prueba primero en localhost antes de desplegar a producción
