import asyncio
import logging
import os
import threading
from datetime import datetime

from celery import shared_task

from .models import UserProfile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0)
def verify_dv_login_manual_task(self, user_id: int, timeout_seconds: int = 300):
    """Tarea para login manual asistido desde la web."""
    try:
        # Obtener perfil del usuario
        try:
            profile = UserProfile.objects.get(user_id=user_id)
        except UserProfile.DoesNotExist:
            return {"success": False, "message": "Perfil no encontrado"}

        # Marcar estado en progreso
        profile.set_dv_connection_verified(None)
        profile.save(update_fields=["dv_connection_status"])

        # Ejecutar login manual con navegador visible (usando FlareSolverr)
        import asyncio
        import json
        from pathlib import Path

        from .clients.dvcarreras_playwright_flaresolverr import \
            DVCarrerasPlaywrightFlareSolverr

        def do_manual_login():
            client = DVCarrerasPlaywrightFlareSolverr(
                username=profile.get_dv_username(),
                password=profile.get_dv_password(),
                headless=False,  # Navegador visible para login manual
            )

            # Ejecutar login manual
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                return loop.run_until_complete(client.test_login())
            finally:
                loop.close()

        # Ejecutar en hilo separado
        result_container = {"success": False, "message": "Error desconocido"}

        def thread_target():
            try:
                success = do_manual_login()
                if success:
                    result_container["success"] = True
                    result_container["message"] = "Login manual completado exitosamente"
                else:
                    result_container["success"] = False
                    result_container["message"] = "Login manual falló"
            except Exception as te:
                logger.error(f"Error en hilo de login manual DV: {te}")
                result_container["success"] = False
                result_container["message"] = f"Error en login manual: {str(te)}"

        # Ejecutar con timeout
        thread = threading.Thread(target=thread_target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            logger.warning("Timeout login manual DV")
            result_container["success"] = False
            result_container["message"] = "Timeout en login manual"

        # Actualizar estado del usuario
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            if result_container["success"]:
                profile.set_dv_connection_verified(True)
            else:
                profile.set_dv_connection_verified(False)
            profile.save(update_fields=["dv_connection_status"])
        except UserProfile.DoesNotExist:
            pass

        return result_container

    except Exception as e:
        logger.error(f"Error en verify_dv_login_manual_task: {e}")
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            profile.set_dv_connection_verified(False)
            profile.save(update_fields=["dv_connection_status"])
        except UserProfile.DoesNotExist:
            pass
        return {"success": False, "message": f"Error: {str(e)}"}


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

        # Ejecutar verificación con STEALTH (undetected-chromedriver) de forma SINCRÓNICA
        from .clients.dvcarreras_stealth import DVCarrerasStealth

        debug_paths = {}

        def do_sync_login():
            """Ejecuta el flujo async del cliente Stealth en un event loop propio."""
            import asyncio as _asyncio

            async def _run():
                client = DVCarrerasStealth(
                    user_id=user_id,
                    headless=True,
                )
                try:
                    await client.start()
                    ok = await client.login()
                    return bool(ok)
                finally:
                    try:
                        await client.close()
                    except Exception:
                        pass

            loop = _asyncio.new_event_loop()
            try:
                _asyncio.set_event_loop(loop)
                return loop.run_until_complete(_run())
            finally:
                loop.close()

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

        # Guardar resultado (refrescar instancia antes de guardar)
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            profile.set_dv_connection_verified(True if success else False)
            profile.save(update_fields=["dv_connection_status"])
            logger.info(
                f"Estado DV actualizado para usuario {user_id}: {'verified' if success else 'failed'}"
            )
        except Exception as save_error:
            logger.error(f"Error guardando estado DV: {save_error}")

        # Determinar mensaje basado en el resultado
        if success:
            message = "Conexión verificada con scraper STEALTH"
        elif t.is_alive():
            message = "Timeout en la verificación. Intenta nuevamente."
        else:
            message = "No se pudo verificar la conexión. Verifica tus credenciales."

        result = {
            "success": bool(success),
            "message": message,
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
