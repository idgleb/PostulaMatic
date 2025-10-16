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

        # Ejecutar verificación con Playwright asincrónico
        import asyncio
        from .clients.dvcarreras_playwright_simple import (
            DVCarrerasPlaywrightSimple,
        )

        async def run_check():
            debug_paths = {}
            async with DVCarrerasPlaywrightSimple(
                username=profile.get_dv_username(),
                password=profile.get_dv_password(),
                storage_state_path=os.path.join("media", "dv_sessions", f"{profile.user.username}.json"),
            ) as client:
                success_login = await client.login()
                if not success_login:
                    # Capturar evidencia de la página actual
                    try:
                        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        base_dir = os.path.join("media", "debug", "dv_login", ts)
                        os.makedirs(base_dir, exist_ok=True)
                        screenshot_path = os.path.join(base_dir, "login.png")
                        html_path = os.path.join(base_dir, "login.html")
                        try:
                            await client.page.screenshot(path=screenshot_path, full_page=True)
                            debug_paths["screenshot_path"] = screenshot_path
                        except Exception as se:
                            logger.warning(f"No se pudo guardar screenshot: {se}")
                        try:
                            content = await client.page.content()
                            with open(html_path, "w", encoding="utf-8") as f:
                                f.write(content)
                            debug_paths["html_path"] = html_path
                        except Exception as he:
                            logger.warning(f"No se pudo guardar HTML: {he}")
                    except Exception as de:
                        logger.warning(f"Error preparando directorios de debug: {de}")
                return success_login, debug_paths

        # Ejecutar Playwright en un hilo separado para evitar conflictos de event loop
        result_container = {"success": False, "debug_paths": {}}

        def thread_target():
            try:
                res_success, res_debug = asyncio.run(run_check())
                result_container["success"] = res_success
                result_container["debug_paths"] = res_debug
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
            debug_paths = result_container.get("debug_paths") or {}

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


