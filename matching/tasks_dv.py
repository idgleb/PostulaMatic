import logging
from celery import shared_task
import os
from datetime import datetime
import threading
import asyncio

from .models import UserProfile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def verify_dv_login_task(self, user_id: int, timeout_seconds: int = 90):
    """Verifica el login a INTRANET DAVINCI usando Playwright en un worker Celery.

    Retorna dict con success=True/False y mensaje. No bloquea el web worker.
    """
    try:
        # Marcar estado en progreso
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            profile.set_dv_connection_verified(None)  # in_progress
            profile.save(update_fields=["dv_connection_status"])
        except UserProfile.DoesNotExist:
            return {"success": False, "message": "Perfil no encontrado"}

        # Ejecutar verificación con Playwright de forma SINCRÓNICA (evita conflictos de event loop)
        from .clients.dvcarreras_playwright_simple import DVCarrerasPlaywrightSimple
        debug_paths = {}
        def do_sync_login():
            client = DVCarrerasPlaywrightSimple(
                username=profile.get_dv_username(),
                password=profile.get_dv_password(),
                log_callback=None,
                storage_state_path=os.path.join("media", "dv_sessions", f"{profile.user.username}.json"),
            )
            # Usa el método síncrono que gestiona su propio event loop
            return client.test_login()

        # Ejecutar en hilo separado para no bloquear
        result_container = {"success": False}

        def thread_target():
            try:
                res_success = do_sync_login()
                result_container["success"] = bool(res_success)
            except Exception as te:
                logger.error(f"Error en hilo de verificación DV: {te}")

        t = threading.Thread(target=thread_target, daemon=True)
        t.start()
        t.join(timeout_seconds)

        if t.is_alive():
            success = False
            debug_paths = {}
            logger.warning("Timeout verificando login DV")
        else:
            success = bool(result_container.get("success"))
            debug_paths = {}

        # Guardar resultado
        profile.set_dv_connection_verified(True if success else False)
        profile.save(update_fields=["dv_connection_status"])

        result = {
            "success": bool(success),
            "message": "Conexión verificada" if success else "Credenciales inválidas o timeout",
        }
        if not success and debug_paths:
            result.update(debug_paths)
            logger.info(f"DV debug paths: {debug_paths}")
        return result

    except Exception as e:
        logger.error(f"Error verificando login DV: {e}")
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            profile.set_dv_connection_verified(False)
            profile.save(update_fields=["dv_connection_status"])
        except Exception:
            pass
        return {"success": False, "message": str(e)}


