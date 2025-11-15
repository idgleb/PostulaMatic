import asyncio
import logging

from django.core.management.base import BaseCommand

from matching.clients.dvcarreras_playwright_flaresolverr import (
    DVCarrerasPlaywrightFlareSolverr,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Prueba la funcionalidad de gestión de sesiones del cliente DV Carreras."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="Usuario para la prueba de sesión",
            default="19138087",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Contraseña para la prueba de sesión",
            default="test_password",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        self.stdout.write(
            self.style.SUCCESS("Iniciando prueba de gestión de sesiones...")
        )

        async def test_session_management():
            try:
                # Crear cliente con directorio de sesiones personalizado
                client = DVCarrerasPlaywrightFlareSolverr(
                    username=username,
                    password=password,
                    headless=True,
                    session_dir="media/test_sessions",
                )

                # Primera prueba: Login completo
                self.stdout.write("=== PRIMERA PRUEBA: Login completo ===")
                await client.start()

                login_result = await client.test_login()
                if login_result:
                    self.stdout.write(self.style.SUCCESS("✅ Login exitoso"))

                    # Verificar que se guardó la sesión
                    if client.session_file.exists():
                        self.stdout.write(
                            self.style.SUCCESS("✅ Sesión guardada correctamente")
                        )
                    else:
                        self.stdout.write(self.style.ERROR("❌ Sesión no se guardó"))
                else:
                    self.stdout.write(self.style.ERROR("❌ Login falló"))
                    return

                await client.close()

                # Segunda prueba: Usar sesión guardada
                self.stdout.write("\n=== SEGUNDA PRUEBA: Usar sesión guardada ===")
                client2 = DVCarrerasPlaywrightFlareSolverr(
                    username=username,
                    password=password,
                    headless=True,
                    session_dir="media/test_sessions",
                )

                await client2.start()

                # Intentar cargar sesión
                session_loaded = await client2.load_session()
                if session_loaded:
                    self.stdout.write(
                        self.style.SUCCESS("✅ Sesión cargada correctamente")
                    )

                    # Verificar validez
                    if await client2.test_session_validity():
                        self.stdout.write(
                            self.style.SUCCESS("✅ Sesión válida confirmada")
                        )
                    else:
                        self.stdout.write(self.style.WARNING("⚠️ Sesión no es válida"))
                else:
                    self.stdout.write(
                        self.style.WARNING("⚠️ No se pudo cargar la sesión")
                    )

                await client2.close()

                # Tercera prueba: Verificar archivos de sesión
                self.stdout.write("\n=== TERCERA PRUEBA: Verificar archivos ===")
                if client.session_file.exists():
                    import json

                    with open(client.session_file, "r") as f:
                        session_data = json.load(f)

                    self.stdout.write(f"Archivo de sesión: {client.session_file}")
                    self.stdout.write(f"Usuario: {session_data.get('username')}")
                    self.stdout.write(f"Guardado: {session_data.get('saved_at')}")
                    self.stdout.write(
                        f"Autenticado: {session_data.get('is_authenticated')}"
                    )
                    self.stdout.write(
                        f"Cookies: {len(session_data.get('cookies', []))}"
                    )

                    if client.cookies_file.exists():
                        self.stdout.write(
                            self.style.SUCCESS("✅ Archivo de cookies también existe")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING("⚠️ Archivo de cookies no existe")
                        )

                self.stdout.write(
                    self.style.SUCCESS("\n🎉 Prueba de gestión de sesiones completada")
                )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error durante la prueba: {e}"))

        asyncio.run(test_session_management())
