"""
Servicio de lock global para scraping.
Garantiza que solo un scraping pueda ejecutarse a la vez en todo el sistema.
"""

import logging
from typing import Optional, Dict, Any
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)

# Claves de cache
SCRAPING_LOCK_KEY = "global_scraping_lock"
SCRAPING_LOCK_TIMEOUT = 7200  # 2 horas máximo (por si algo falla y no se libera)

# Información adicional del scraping activo
SCRAPING_INFO_KEY = "global_scraping_info"


class ScrapingLockService:
    """
    Servicio para gestionar el lock global de scraping.
    Usa Redis/cache de Django para garantizar exclusividad entre workers.
    """

    @staticmethod
    def acquire_lock(
        task_id: str, user_id: Optional[int] = None, source: str = "manual"
    ) -> bool:
        """
        Intenta adquirir el lock global de scraping.

        Args:
            task_id: ID de la tarea de Celery
            user_id: ID del usuario que inició el scraping (opcional)
            source: Origen del scraping ('manual', 'scheduled')

        Returns:
            True si se adquirió el lock, False si ya existe otro scraping activo
        """
        try:
            # cache.add() solo crea la clave si NO existe (atómico en Redis)
            lock_acquired = cache.add(
                SCRAPING_LOCK_KEY, task_id, timeout=SCRAPING_LOCK_TIMEOUT
            )

            if lock_acquired:
                # Guardar información adicional del scraping
                info = {
                    "task_id": task_id,
                    "user_id": user_id,
                    "source": source,
                    "started_at": timezone.now().isoformat(),
                }
                cache.set(SCRAPING_INFO_KEY, info, timeout=SCRAPING_LOCK_TIMEOUT)

                logger.info(
                    f"🔒 Lock de scraping adquirido: task={task_id}, user={user_id}, source={source}"
                )
                return True
            else:
                existing_task_id = cache.get(SCRAPING_LOCK_KEY)
                logger.warning(f"⚠️ Lock de scraping ya existe: task={existing_task_id}")
                return False

        except Exception as e:
            logger.error(f"❌ Error al adquirir lock de scraping: {e}")
            return False

    @staticmethod
    def release_lock(task_id: str) -> bool:
        """
        Libera el lock global de scraping.
        Solo libera si el task_id coincide con el lock actual (seguridad).

        Args:
            task_id: ID de la tarea que quiere liberar el lock

        Returns:
            True si se liberó, False si no era el dueño del lock
        """
        try:
            current_lock = cache.get(SCRAPING_LOCK_KEY)

            if current_lock == task_id:
                cache.delete(SCRAPING_LOCK_KEY)
                cache.delete(SCRAPING_INFO_KEY)
                logger.info(f"🔓 Lock de scraping liberado: task={task_id}")
                return True
            else:
                logger.warning(
                    f"⚠️ Intento de liberar lock sin ser dueño: task={task_id}, lock_actual={current_lock}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Error al liberar lock de scraping: {e}")
            return False

    @staticmethod
    def force_release_lock() -> bool:
        """
        Libera el lock forzosamente (solo para emergencias o limpieza admin).

        Returns:
            True si se liberó
        """
        try:
            cache.delete(SCRAPING_LOCK_KEY)
            cache.delete(SCRAPING_INFO_KEY)
            logger.warning("⚠️ Lock de scraping liberado FORZOSAMENTE")
            return True
        except Exception as e:
            logger.error(f"❌ Error al liberar lock forzosamente: {e}")
            return False

    @staticmethod
    def get_active_scraping() -> Optional[Dict[str, Any]]:
        """
        Obtiene información del scraping activo (si existe).

        Returns:
            Dict con información del scraping activo, o None si no hay ninguno
        """
        try:
            task_id = cache.get(SCRAPING_LOCK_KEY)
            if not task_id:
                return None

            info = cache.get(SCRAPING_INFO_KEY)
            if info:
                return info
            else:
                # Si existe el lock pero no la info, crear info básica
                return {
                    "task_id": task_id,
                    "user_id": None,
                    "source": "unknown",
                    "started_at": None,
                }

        except Exception as e:
            logger.error(f"❌ Error al obtener scraping activo: {e}")
            return None

    @staticmethod
    def is_locked() -> bool:
        """
        Verifica si hay un scraping activo.

        Returns:
            True si hay un scraping en curso, False si no
        """
        try:
            return cache.get(SCRAPING_LOCK_KEY) is not None
        except Exception as e:
            logger.error(f"❌ Error al verificar lock: {e}")
            return False

    @staticmethod
    def get_lock_task_id() -> Optional[str]:
        """
        Obtiene el task_id del scraping activo.

        Returns:
            Task ID del scraping activo, o None si no hay ninguno
        """
        try:
            return cache.get(SCRAPING_LOCK_KEY)
        except Exception as e:
            logger.error(f"❌ Error al obtener task_id del lock: {e}")
            return None


# Instancia global del servicio
scraping_lock = ScrapingLockService()
