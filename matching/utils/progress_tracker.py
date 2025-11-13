"""
Sistema de seguimiento de progreso para procesamiento de CVs.
Permite actualizar y consultar el estado del procesamiento en tiempo real.
"""

import logging
import uuid
from datetime import datetime

from django.core.cache import cache

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Rastrea el progreso del procesamiento de un CV."""

    STEPS = [
        {"id": "upload", "label": "📤 Subiendo archivo", "status": "pending"},
        {
            "id": "temp_file",
            "label": "💾 Guardando archivo temporal",
            "status": "pending",
        },
        {
            "id": "pdf_to_images",
            "label": "🖼️ Convirtiendo PDF a imágenes",
            "status": "pending",
        },
        {
            "id": "openai_vision",
            "label": "🤖 Extrayendo texto con OpenAI",
            "status": "pending",
        },
        {
            "id": "anthropic_vision",
            "label": "🔄 Fallback a Anthropic",
            "status": "pending",
        },
        {
            "id": "skills_extraction",
            "label": "🎯 Extrayendo habilidades",
            "status": "pending",
        },
        {
            "id": "db_save",
            "label": "💾 Guardando en base de datos",
            "status": "pending",
        },
        {"id": "complete", "label": "✅ Procesamiento completado", "status": "pending"},
    ]

    def __init__(self, progress_id=None):
        """
        Inicializa el tracker de progreso.

        Args:
            progress_id: ID único para este proceso. Si no se provee, se genera uno nuevo.
        """
        self.progress_id = progress_id or str(uuid.uuid4())
        self.cache_key = f"cv_progress_{self.progress_id}"
        self.cache_timeout = 600  # 10 minutos

        # Inicializar progreso si no existe
        if not cache.get(self.cache_key):
            self._initialize_progress()

    def _initialize_progress(self):
        """Inicializa el estado del progreso."""
        progress_data = {
            "progress_id": self.progress_id,
            "current_step": 0,
            "total_steps": len(self.STEPS),
            "steps": [step.copy() for step in self.STEPS],
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed": False,
            "error": None,
            "warning": None,
        }
        cache.set(self.cache_key, progress_data, self.cache_timeout)
        logger.info(f"✅ Progress tracker inicializado: {self.progress_id}")

    def update_step(self, step_id, status, message=None, details=None):
        """
        Actualiza el estado de un paso específico.

        Args:
            step_id: ID del paso a actualizar
            status: Nuevo estado ('pending', 'in_progress', 'completed', 'skipped', 'error')
            message: Mensaje adicional (opcional)
            details: Detalles adicionales (opcional)
        """
        progress_data = cache.get(self.cache_key)
        if not progress_data:
            logger.warning(f"⚠️ Progress data no encontrado para {self.progress_id}")
            return

        # Buscar el paso y actualizarlo
        for i, step in enumerate(progress_data["steps"]):
            if step["id"] == step_id:
                step["status"] = status
                if message:
                    step["message"] = message
                if details:
                    step["details"] = details

                # Actualizar current_step si el paso está en progreso o completado
                if status in ["in_progress", "completed"]:
                    progress_data["current_step"] = i + 1

                break

        progress_data["updated_at"] = datetime.now().isoformat()
        cache.set(self.cache_key, progress_data, self.cache_timeout)

        logger.info(
            f"📊 Progress actualizado [{self.progress_id}]: {step_id} -> {status}"
        )

    def set_error(self, error_message, step_id=None):
        """
        Marca el proceso como fallido.

        Args:
            error_message: Mensaje de error
            step_id: ID del paso donde ocurrió el error (opcional)
        """
        progress_data = cache.get(self.cache_key)
        if not progress_data:
            return

        progress_data["error"] = error_message
        progress_data["completed"] = True
        progress_data["updated_at"] = datetime.now().isoformat()

        if step_id:
            self.update_step(step_id, "error", error_message)

        cache.set(self.cache_key, progress_data, self.cache_timeout)
        logger.error(
            f"❌ Progress marcado como error [{self.progress_id}]: {error_message}"
        )

    def set_warning(self, warning_message):
        """
        Agrega un mensaje de advertencia.

        Args:
            warning_message: Mensaje de advertencia
        """
        progress_data = cache.get(self.cache_key)
        if not progress_data:
            return

        progress_data["warning"] = warning_message
        progress_data["updated_at"] = datetime.now().isoformat()
        cache.set(self.cache_key, progress_data, self.cache_timeout)
        logger.warning(f"⚠️ Progress warning [{self.progress_id}]: {warning_message}")

    def set_complete(self, success_message=None):
        """
        Marca el proceso como completado exitosamente.

        Args:
            success_message: Mensaje de éxito (opcional)
        """
        progress_data = cache.get(self.cache_key)
        if not progress_data:
            return

        progress_data["completed"] = True
        progress_data["current_step"] = len(self.STEPS)
        progress_data["updated_at"] = datetime.now().isoformat()

        # Marcar el último paso como completado
        if progress_data["steps"]:
            progress_data["steps"][-1]["status"] = "completed"
            if success_message:
                progress_data["steps"][-1]["message"] = success_message

        cache.set(self.cache_key, progress_data, self.cache_timeout)
        logger.info(f"✅ Progress completado [{self.progress_id}]")

    def get_progress(self):
        """
        Obtiene el estado actual del progreso.

        Returns:
            dict: Datos del progreso o None si no existe
        """
        return cache.get(self.cache_key)

    def cleanup(self):
        """Limpia los datos del progreso del caché."""
        cache.delete(self.cache_key)
        logger.info(f"🧹 Progress limpiado [{self.progress_id}]")
