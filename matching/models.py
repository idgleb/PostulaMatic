import logging
from django.contrib.auth.models import User
from django.db import models

from .utils.encryption import decrypt_credential, encrypt_credential

logger = logging.getLogger(__name__)


class UserProfile(models.Model):
    """Perfil extendido del usuario con configuración SMTP y credenciales dvcarreras."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=100, blank=True, null=True)

    # Configuración SMTP del remitente
    smtp_host = models.CharField(max_length=255, blank=True, null=True)
    smtp_port = models.IntegerField(default=587)
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)
    smtp_username = models.CharField(max_length=255, blank=True, null=True)
    smtp_password = models.TextField(
        blank=True, null=True
    )  # Encriptado automáticamente

    # Credenciales dvcarreras
    dv_username = models.CharField(
        max_length=255, blank=True, null=True
    )  # Usuario público (no encriptado)
    dv_password = models.TextField(blank=True, null=True)  # Encriptado automáticamente
    dv_connection_status = models.CharField(
        max_length=20,
        choices=[
            ("verified", "Verificado"),
            ("not_verified", "No Verificado"),
        ],
        default="not_verified",
        help_text="Estado de conexión a INTRANET DAVINCI",
    )

    # Configuración de matching y límites
    match_threshold = models.IntegerField(
        default=70, help_text="Umbral de coincidencia 0-100"
    )
    daily_limit = models.IntegerField(default=20, help_text="Límite diario de envíos")
    min_pause_seconds = models.IntegerField(
        default=20, help_text="Pausa mínima entre envíos"
    )
    max_pause_seconds = models.IntegerField(
        default=90, help_text="Pausa máxima entre envíos"
    )

    # Control de automatización
    is_active = models.BooleanField(
        default=False, help_text="Start/Stop del proceso automático"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        return f"{self.user.username} - {self.display_name or 'Sin nombre'}"

    # Métodos para manejar credenciales encriptadas

    def get_smtp_password(self):
        """Retorna la contraseña SMTP desencriptada."""
        if not self.smtp_password:
            return ""
        return decrypt_credential(self.smtp_password)

    def set_smtp_password(self, password):
        """Establece la contraseña SMTP encriptada."""
        if password:
            self.smtp_password = encrypt_credential(password)
        else:
            self.smtp_password = ""

    def get_dv_username(self):
        """Retorna el usuario DVCarreras (no encriptado)."""
        return self.dv_username or ""

    def set_dv_username(self, username):
        """Establece el usuario DVCarreras (no encriptado)."""
        self.dv_username = username or ""

    def get_dv_password(self):
        """Retorna la contraseña DVCarreras desencriptada."""
        if not self.dv_password:
            return ""
        return decrypt_credential(self.dv_password)

    def set_dv_password(self, password):
        """Establece la contraseña DVCarreras encriptada."""
        if password:
            self.dv_password = encrypt_credential(password)
        else:
            self.dv_password = ""

    def set_dv_connection_verified(self, verified=True):
        """Establece el estado de conexión DV."""
        if verified is True:
            self.dv_connection_status = "verified"
        elif verified is False:
            self.dv_connection_status = "not_verified"
        else:  # None o 'in_progress'
            self.dv_connection_status = "in_progress"

    def is_dv_connection_verified(self):
        """Verifica si la conexión DV está verificada."""
        return self.dv_connection_status == "verified"

    def is_dv_connection_in_progress(self):
        """Verifica si la conexión DV está en proceso."""
        return self.dv_connection_status == "in_progress"

    def save(self, *args, **kwargs):
        """Override save para manejar encriptación automática."""
        # Si los campos tienen valores nuevos, encriptarlos
        # (esto se manejará principalmente desde los formularios)
        super().save(*args, **kwargs)

    def clean(self):
        """Validar que no se usen TLS y SSL simultáneamente."""
        from django.core.exceptions import ValidationError

        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValidationError("No se puede usar TLS y SSL simultáneamente")


class UserCV(models.Model):
    """CV del usuario con texto parseado y skills detectadas."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cvs")
    original_file = models.FileField(
        upload_to="cvs/%Y/%m/%d/", help_text="Archivo PDF o DOCX original"
    )
    parsed_text = models.TextField(blank=True, help_text="Texto extraído del CV")
    skills = models.JSONField(
        default=dict, help_text="Datos de habilidades detectadas con confianza"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "CV de Usuario"
        verbose_name_plural = "CVs de Usuario"
        ordering = ["-created_at"]

    def __str__(self):
        return f"CV de {self.user.username} - {self.created_at.strftime('%d/%m/%Y')}"

    @property
    def skills_list(self):
        """Retorna lista simple de habilidades detectadas."""
        if isinstance(self.skills, dict) and "skills" in self.skills:
            return self.skills["skills"]
        return []

    @property
    def skills_count(self):
        """Retorna el número de habilidades detectadas."""
        return len(self.skills_list)

    @property
    def skills_categories(self):
        """Retorna las habilidades organizadas por categorías."""
        if isinstance(self.skills, dict) and "categories" in self.skills:
            return self.skills["categories"]
        return {}

    @property
    def is_processed(self):
        """Indica si el CV ha sido procesado."""
        return bool(
            self.parsed_text
        )  # Procesado si tiene texto extraído, independientemente de las habilidades


class ScrapingLog(models.Model):
    """Logs del proceso de scraping para persistencia y recuperación."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="scraping_logs"
    )
    task_id = models.CharField(max_length=255, help_text="ID de la tarea de Celery")
    message = models.TextField(help_text="Mensaje del log")
    log_type = models.CharField(
        max_length=20,
        choices=[
            ("info", "Información"),
            ("success", "Éxito"),
            ("error", "Error"),
            ("warning", "Advertencia"),
        ],
        default="info",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Log de Scraping"
        verbose_name_plural = "Logs de Scraping"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user.username} - {self.timestamp.strftime('%H:%M:%S')} - {self.message[:50]}"


class JobPosting(models.Model):
    """Ofertas de trabajo scraped de fuentes externas."""

    external_id = models.CharField(
        max_length=255, unique=True, help_text="ID único en la fuente externa"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="Descripción completa del puesto")
    email = models.EmailField(
        blank=True, help_text="Email de contacto (decodificado de Cloudflare)"
    )
    raw_html = models.TextField(blank=True, help_text="HTML crudo para debugging")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Oferta de Trabajo"
        verbose_name_plural = "Ofertas de Trabajo"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["external_id"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.email}"


class MatchScore(models.Model):
    """Score de coincidencia entre CV y oferta de trabajo."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="match_scores"
    )
    cv = models.ForeignKey(
        UserCV, on_delete=models.CASCADE, related_name="match_scores"
    )
    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="match_scores"
    )

    score = models.IntegerField(help_text="Score de coincidencia 0-100")
    details = models.JSONField(
        default=dict, help_text="Explicación detallada del score"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Score de Coincidencia"
        verbose_name_plural = "Scores de Coincidencia"
        ordering = ["-score", "-created_at"]
        unique_together = ["user", "cv", "job_posting"]
        indexes = [
            models.Index(fields=["user", "score"]),
            models.Index(fields=["score"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.job_posting.title} ({self.score}%)"

    @property
    def is_above_threshold(self):
        """Verifica si supera el umbral del usuario."""
        try:
            return self.score >= self.user.profile.match_threshold
        except UserProfile.DoesNotExist:
            return False


class ApplicationAttempt(models.Model):
    """Registro de intentos de postulación automática."""

    STATUS_CHOICES = [
        ("QUEUED", "En Cola"),
        ("SENT", "Enviado"),
        ("FAILED", "Fallido"),
    ]

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="application_attempts"
    )
    cv = models.ForeignKey(
        UserCV, on_delete=models.CASCADE, related_name="application_attempts"
    )
    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="application_attempts"
    )

    # Contenido del email generado
    email_subject = models.CharField(max_length=255)
    email_body = models.TextField()
    attachment_path = models.CharField(
        max_length=500, blank=True, help_text="Ruta al CV personalizado adjunto"
    )

    # Información del envío
    smtp_from = models.EmailField(help_text="Email remitente usado")
    smtp_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="QUEUED"
    )
    error_message = models.TextField(blank=True, help_text="Mensaje de error si falló")

    # Timestamps y reintentos
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Intento de Postulación"
        verbose_name_plural = "Intentos de Postulación"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "smtp_status"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["smtp_status"]),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.job_posting.title} ({self.smtp_status})"

    @property
    def is_successful(self):
        return self.smtp_status == "SENT"

    @property
    def is_failed(self):
        return self.smtp_status == "FAILED"

    @property
    def is_pending(self):
        return self.smtp_status == "QUEUED"


class EmailSentLog(models.Model):
    """Log de emails enviados para auditoría y estadísticas."""
    
    STATUS_CHOICES = [
        ('sent', 'Enviado'),
        ('failed', 'Fallido'),
        ('queued', 'En Cola'),
        ('retry', 'Reintento'),
    ]
    
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_logs"
    )
    cv = models.ForeignKey(
        UserCV, on_delete=models.CASCADE, related_name="email_logs"
    )
    job_posting = models.ForeignKey(
        JobPosting, on_delete=models.CASCADE, related_name="email_logs"
    )
    
    # Contenido del email
    email_subject = models.CharField(max_length=500)
    email_body = models.TextField()
    
    # Detalles del envío
    sent_to = models.EmailField()
    message_id = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='sent'
    )
    error_message = models.TextField(blank=True, null=True)
    
    # Metadatos
    task_id = models.CharField(max_length=255, blank=True, null=True)
    email_template = models.CharField(max_length=50, default='base')
    ai_provider = models.CharField(max_length=50, default='openai')
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log de Email Enviado"
        verbose_name_plural = "Logs de Emails Enviados"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["sent_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["task_id"]),
        ]
    
    def __str__(self):
        return f"{self.user.username} -> {self.job_posting.title} ({self.status}) - {self.sent_at.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def is_successful(self):
        return self.status == 'sent'
    
    @property
    def is_failed(self):
        return self.status == 'failed'
    
    @property
    def is_queued(self):
        return self.status == 'queued'
    
    @property
    def is_retry(self):
        return self.status == 'retry'


class AIConfiguration(models.Model):
    """Configuración global de proveedores de IA."""
    
    # OpenAI
    openai_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="API Key de OpenAI (sk-...)"
    )
    openai_model = models.CharField(
        max_length=100,
        default='gpt-3.5-turbo',
        help_text="Modelo de OpenAI a usar"
    )
    openai_enabled = models.BooleanField(
        default=False,
        help_text="Habilitar OpenAI"
    )
    
    # Anthropic
    anthropic_api_key = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="API Key de Anthropic (sk-ant-...)"
    )
    anthropic_model = models.CharField(
        max_length=100,
        default='claude-3-haiku-20240307',
        help_text="Modelo de Anthropic a usar"
    )
    anthropic_enabled = models.BooleanField(
        default=False,
        help_text="Habilitar Anthropic"
    )
    
    # Configuración general
    default_provider = models.CharField(
        max_length=20,
        choices=[
            ('openai', 'OpenAI'),
            ('anthropic', 'Anthropic'),
        ],
        default='openai',
        help_text="Proveedor por defecto"
    )
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de IA"
        verbose_name_plural = "Configuración de IA"
    
    def __str__(self):
        enabled_providers = []
        if self.openai_enabled:
            enabled_providers.append("OpenAI")
        if self.anthropic_enabled:
            enabled_providers.append("Anthropic")
        
        return f"IA Config - Proveedores: {', '.join(enabled_providers) or 'Ninguno'}"
    
    @classmethod
    def get_config(cls):
        """Obtiene la configuración actual, creándola si no existe."""
        config, created = cls.objects.get_or_create(pk=1)
        return config
    
    def get_openai_key(self):
        """Obtiene la API key de OpenAI encriptada."""
        if self.openai_enabled and self.openai_api_key:
            return self._decrypt_key(self.openai_api_key)
        return None
    
    def get_anthropic_key(self):
        """Obtiene la API key de Anthropic encriptada."""
        if self.anthropic_enabled and self.anthropic_api_key:
            return self._decrypt_key(self.anthropic_api_key)
        return None
    
    def set_openai_key(self, api_key):
        """Establece la API key de OpenAI encriptada."""
        if api_key:
            self.openai_api_key = self._encrypt_key(api_key)
            self.openai_enabled = True
        else:
            self.openai_api_key = ""
            self.openai_enabled = False
    
    def set_anthropic_key(self, api_key):
        """Establece la API key de Anthropic encriptada."""
        if api_key:
            self.anthropic_api_key = self._encrypt_key(api_key)
            self.anthropic_enabled = True
        else:
            self.anthropic_api_key = ""
            self.anthropic_enabled = False
    
    def _encrypt_key(self, key):
        """Encripta una API key."""
        try:
            from cryptography.fernet import Fernet
            import os
            
            # Obtener clave de encriptación
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                # Generar clave si no existe
                encryption_key = Fernet.generate_key().decode()
                logger.warning(f"Nueva clave de encriptación generada: {encryption_key}")
            
            f = Fernet(encryption_key.encode())
            return f.encrypt(key.encode()).decode()
            
        except ImportError:
            logger.warning("No se pudo importar el módulo de encriptación. Las credenciales permanecen sin encriptar.")
            return key
        except Exception as e:
            logger.error(f"Error encriptando clave: {e}")
            return key
    
    def _decrypt_key(self, encrypted_key):
        """Desencripta una API key."""
        try:
            from cryptography.fernet import Fernet
            import os
            
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                logger.error("No se encontró clave de encriptación")
                return None
            
            f = Fernet(encryption_key.encode())
            return f.decrypt(encrypted_key.encode()).decode()
            
        except ImportError:
            logger.warning("No se pudo importar el módulo de encriptación. Usando clave sin encriptar.")
            return encrypted_key
        except Exception as e:
            logger.error(f"Error desencriptando clave: {e}")
            return encrypted_key
    
    def get_available_providers(self):
        """Retorna los proveedores disponibles."""
        providers = []
        if self.openai_enabled and self.openai_api_key:
            providers.append('openai')
        if self.anthropic_enabled and self.anthropic_api_key:
            providers.append('anthropic')
        return providers
    
    def is_configured(self):
        """Verifica si al menos un proveedor está configurado."""
        return len(self.get_available_providers()) > 0
