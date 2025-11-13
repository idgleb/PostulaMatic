"""
Comando para login manual asistido en DV Carreras.
Permite al usuario resolver el CAPTCHA manualmente una vez y guarda la sesión para reutilizar.
"""

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from matching.clients.dvcarreras_playwright_flaresolverr import (
    DVCarrerasPlaywrightFlareSolverr,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Login manual asistido para DV Carreras - resolver CAPTCHA una vez"

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="Username del usuario (si no se especifica, usa el usuario por defecto)",
        )

    def handle(self, *args, **options):
        username = options.get("username")

        if not username:
            # Usar el primer usuario disponible
            user = User.objects.first()
            if not user:
                raise CommandError("No hay usuarios en la base de datos")
            username = user.userprofile.dv_username
            if not username:
                raise CommandError("El usuario no tiene configurado dv_username")

        self.stdout.write(
            f"🚀 Iniciando login manual asistido para usuario: {username}"
        )
        self.stdout.write(
            "📋 Este comando abrirá un navegador donde podrás resolver el CAPTCHA manualmente"
        )
        self.stdout.write("⏳ Una vez resuelto, la sesión se guardará para uso futuro")

        # Crear directorio para sesiones
        sessions_dir = Path("media/dv_sessions")
        sessions_dir.mkdir(parents=True, exist_ok=True)

        # Ejecutar login manual
        asyncio.run(self._manual_login(username, sessions_dir))

    async def _manual_login(self, username, sessions_dir):
        """Ejecuta el login manual con navegador visible."""
        try:
            # Obtener contraseña del usuario
            user = User.objects.get(userprofile__dv_username=username)
            password = user.userprofile.get_dv_password()

            if not password:
                raise CommandError(
                    f"Usuario {username} no tiene contraseña DV configurada"
                )

            # Crear cliente Playwright en modo headful (visible)
            client = DVCarrerasPlaywrightFlareSolverr(
                username, password, headless=False
            )

            self.stdout.write("🌐 Abriendo navegador...")
            await client.start(headless=False)  # Modo visible

            try:
                self.stdout.write("📝 Navegando a la página de login...")
                await client.page.goto("https://dvcarreras.davinci.edu.ar/login.html")

                self.stdout.write(
                    "⏳ Esperando a que resuelvas el CAPTCHA manualmente..."
                )
                self.stdout.write(
                    "💡 Una vez que veas la página de dashboard, presiona Enter aquí..."
                )

                # Esperar input del usuario
                input(
                    "Presiona Enter cuando hayas resuelto el CAPTCHA y estés en el dashboard..."
                )

                # Verificar que estamos en el dashboard
                current_url = client.page.url
                page_title = await client.page.title()

                self.stdout.write(f"📍 URL actual: {current_url}")
                self.stdout.write(f"📄 Título: {page_title}")

                # Guardar estado de la sesión
                session_file = sessions_dir / f"{username}_session.json"
                storage_state = await client.context.storage_state()

                with open(session_file, "w") as f:
                    json.dump(storage_state, f, indent=2)

                self.stdout.write(f"💾 Sesión guardada en: {session_file}")
                self.stdout.write("✅ Login manual completado exitosamente!")
                self.stdout.write(
                    "🔄 Ahora puedes usar la verificación automática normal"
                )

                # Actualizar estado del usuario
                user.userprofile.set_dv_connection_verified(True)
                user.userprofile.save(update_fields=["dv_connection_status"])

                self.stdout.write("✅ Estado de conexión DV actualizado a 'verificado'")

            finally:
                await client.close()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error durante login manual: {e}"))
            raise CommandError(f"Login manual falló: {e}")
