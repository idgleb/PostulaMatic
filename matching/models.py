from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
# from django_cryptography.fields import encrypt  # Problemas de compatibilidad
import json


class UserProfile(models.Model):
    """Perfil extendido del usuario con configuración SMTP y credenciales dvcarreras."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=100, blank=True, null=True)
    
    # Configuración SMTP del remitente
    smtp_host = models.CharField(max_length=255, blank=True, null=True)
    smtp_port = models.IntegerField(default=587)
    smtp_use_tls = models.BooleanField(default=True)
    smtp_use_ssl = models.BooleanField(default=False)
    smtp_username = models.CharField(max_length=255, blank=True, null=True)
    smtp_password = models.TextField(blank=True, null=True)  # TODO: Encriptar en aplicación
    
    # Credenciales dvcarreras
    dv_username = models.CharField(max_length=255, blank=True, null=True)  # TODO: Encriptar en aplicación
    dv_password = models.TextField(blank=True, null=True)  # TODO: Encriptar en aplicación
    
    # Configuración de matching y límites
    match_threshold = models.IntegerField(default=70, help_text="Umbral de coincidencia 0-100")
    daily_limit = models.IntegerField(default=20, help_text="Límite diario de envíos")
    min_pause_seconds = models.IntegerField(default=20, help_text="Pausa mínima entre envíos")
    max_pause_seconds = models.IntegerField(default=90, help_text="Pausa máxima entre envíos")
    
    # Control de automatización
    is_active = models.BooleanField(default=False, help_text="Start/Stop del proceso automático")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
    
    def __str__(self):
        return f"{self.user.username} - {self.display_name or 'Sin nombre'}"
    
    def clean(self):
        """Validar que no se usen TLS y SSL simultáneamente."""
        from django.core.exceptions import ValidationError
        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValidationError("No se puede usar TLS y SSL simultáneamente")


class UserCV(models.Model):
    """CV del usuario con texto parseado y skills detectadas."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cvs')
    original_file = models.FileField(upload_to='cvs/%Y/%m/%d/', help_text="Archivo PDF o DOCX original")
    parsed_text = models.TextField(blank=True, help_text="Texto extraído del CV")
    skills = models.JSONField(default=dict, help_text="Datos de habilidades detectadas con confianza")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "CV de Usuario"
        verbose_name_plural = "CVs de Usuario"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"CV de {self.user.username} - {self.created_at.strftime('%d/%m/%Y')}"
    
    @property
    def skills_list(self):
        """Retorna lista simple de habilidades detectadas."""
        if isinstance(self.skills, dict) and 'skills' in self.skills:
            return self.skills['skills']
        return []
    
    @property
    def skills_count(self):
        """Retorna el número de habilidades detectadas."""
        return len(self.skills_list)
    
    @property
    def skills_categories(self):
        """Retorna las habilidades organizadas por categorías."""
        if isinstance(self.skills, dict) and 'categories' in self.skills:
            return self.skills['categories']
        return {}
    
    @property
    def is_processed(self):
        """Indica si el CV ha sido procesado."""
        return bool(self.parsed_text) and bool(self.skills_list)


class ScrapingLog(models.Model):
    """Logs del proceso de scraping para persistencia y recuperación."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='scraping_logs')
    task_id = models.CharField(max_length=255, help_text="ID de la tarea de Celery")
    message = models.TextField(help_text="Mensaje del log")
    log_type = models.CharField(max_length=20, choices=[
        ('info', 'Información'),
        ('success', 'Éxito'),
        ('error', 'Error'),
        ('warning', 'Advertencia')
    ], default='info')
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Log de Scraping"
        verbose_name_plural = "Logs de Scraping"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user.username} - {self.timestamp.strftime('%H:%M:%S')} - {self.message[:50]}"


class JobPosting(models.Model):
    """Ofertas de trabajo scraped de fuentes externas."""
    external_id = models.CharField(max_length=255, unique=True, help_text="ID único en la fuente externa")
    title = models.CharField(max_length=255)
    description = models.TextField(help_text="Descripción completa del puesto")
    email = models.EmailField(blank=True, help_text="Email de contacto (decodificado de Cloudflare)")
    raw_html = models.TextField(blank=True, help_text="HTML crudo para debugging")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Oferta de Trabajo"
        verbose_name_plural = "Ofertas de Trabajo"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.email}"


class MatchScore(models.Model):
    """Score de coincidencia entre CV y oferta de trabajo."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='match_scores')
    cv = models.ForeignKey(UserCV, on_delete=models.CASCADE, related_name='match_scores')
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='match_scores')
    
    score = models.IntegerField(help_text="Score de coincidencia 0-100")
    details = models.JSONField(default=dict, help_text="Explicación detallada del score")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Score de Coincidencia"
        verbose_name_plural = "Scores de Coincidencia"
        ordering = ['-score', '-created_at']
        unique_together = ['user', 'cv', 'job_posting']
        indexes = [
            models.Index(fields=['user', 'score']),
            models.Index(fields=['score']),
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
        ('QUEUED', 'En Cola'),
        ('SENT', 'Enviado'),
        ('FAILED', 'Fallido'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='application_attempts')
    cv = models.ForeignKey(UserCV, on_delete=models.CASCADE, related_name='application_attempts')
    job_posting = models.ForeignKey(JobPosting, on_delete=models.CASCADE, related_name='application_attempts')
    
    # Contenido del email generado
    email_subject = models.CharField(max_length=255)
    email_body = models.TextField()
    attachment_path = models.CharField(max_length=500, blank=True, help_text="Ruta al CV personalizado adjunto")
    
    # Información del envío
    smtp_from = models.EmailField(help_text="Email remitente usado")
    smtp_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='QUEUED')
    error_message = models.TextField(blank=True, help_text="Mensaje de error si falló")
    
    # Timestamps y reintentos
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Intento de Postulación"
        verbose_name_plural = "Intentos de Postulación"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'smtp_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['smtp_status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} -> {self.job_posting.title} ({self.smtp_status})"
    
    @property
    def is_successful(self):
        return self.smtp_status == 'SENT'
    
    @property
    def is_failed(self):
        return self.smtp_status == 'FAILED'
    
    @property
    def is_pending(self):
        return self.smtp_status == 'QUEUED'

