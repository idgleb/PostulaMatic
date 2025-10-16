import logging
from celery import shared_task

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
            async with DVCarrerasPlaywrightSimple(
                username=profile.get_dv_username(),
                password=profile.get_dv_password(),
            ) as client:
                return await client.login()

        try:
            success = asyncio.run(asyncio.wait_for(run_check(), timeout=timeout_seconds))
        except asyncio.TimeoutError:
            success = False
            logger.warning("Timeout verificando login DV")

        # Guardar resultado
        profile.set_dv_connection_verified(True if success else False)
        profile.save(update_fields=["dv_connection_status"])

        return {
            "success": bool(success),
            "message": "Conexión verificada" if success else "Credenciales inválidas o timeout",
        }

    except Exception as e:
        logger.error(f"Error verificando login DV: {e}")
        try:
            profile = UserProfile.objects.get(user_id=user_id)
            profile.set_dv_connection_verified(False)
            profile.save(update_fields=["dv_connection_status"])
        except Exception:
            pass
        return {"success": False, "message": str(e)}


