import os
import asyncio
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from matching.clients.dvcarreras_playwright_flaresolverr import (
    DVCarrerasPlaywrightFlareSolverr,
)


class Command(BaseCommand):
    help = "Abre un navegador Playwright (modo visible) para que el usuario resuelva Cloudflare/CAPTCHA y guardamos storage_state."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Usuario Django (dueño del perfil)")
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Ruta del storage_state.json (por defecto media/dv_sessions/<user>.json)",
        )

    def handle(self, *args, **options):
        django_username = options["username"]

        try:
            user = User.objects.get(username=django_username)
            profile = user.profile
        except Exception as e:
            raise CommandError(f"Usuario/perfil no encontrado: {e}")

        out_path = options["output"] or os.path.join(
            "media", "dv_sessions", f"{user.username}.json"
        )
        Path(os.path.dirname(out_path)).mkdir(parents=True, exist_ok=True)

        async def run():
            client = DVCarrerasPlaywrightFlareSolverr(
                username=profile.get_dv_username(),
                password=profile.get_dv_password(),
                log_callback=None,
            )
            # Iniciar en headful
            await client.start()
            # Reabrir browser en headful (simple: cerrar y lanzar no headless)
            # Para simplicidad, usamos el contexto ya creado y navegamos al login.
            await client.page.context.tracing.start(screenshots=True)
            await client.page.goto(client.LOGIN_URL)
            self.stdout.write(self.style.WARNING("Resuelve el CAPTCHA y logueate manualmente. Cierra la pestaña cuando termine."))
            # Esperar hasta que cambie de URL fuera de login
            await client.page.wait_for_function("() => !window.location.href.includes('login')", timeout=0)
            await client.save_storage_state(out_path)
            await client.close()

        asyncio.run(run())

        self.stdout.write(self.style.SUCCESS(f"storage_state guardado en {out_path}"))


