import asyncio
import json
import logging

from django.core.management.base import BaseCommand

from matching.clients.dvcarreras_playwright_flaresolverr import \
    DVCarrerasPlaywrightFlareSolverr

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Prueba simple de la funcionalidad de sesiones guardadas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username", type=str, help="Usuario para la prueba", default="19138087"
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Contraseña para la prueba",
            default="test_password",
        )

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        self.stdout.write(
            self.style.SUCCESS("🧪 Prueba Simple de Sesiones DV Carreras")
        )

        async def test_simple():
            try:
                # Crear cliente
                client = DVCarrerasPlaywrightFlareSolverr(
                    username=username,
                    password=password,
                    headless=True,
                    session_dir="media/sessions",
                )

                # Iniciar navegador
                await client.start()

                # Intentar cargar sesión existente
                self.stdout.write("\n📂 Verificando sesión guardada...")
                session_loaded = await client.load_session()

                if session_loaded:
                    self.stdout.write(
                        self.style.SUCCESS("✅ Sesión cargada desde archivo")
                    )

                    # Verificar si el archivo existe
                    if client.session_file.exists():
                        with open(client.session_file, "r") as f:
                            session_data = json.load(f)

                        self.stdout.write(f"📄 Archivo: {client.session_file}")
                        self.stdout.write(f"👤 Usuario: {session_data.get('username')}")
                        self.stdout.write(
                            f"⏰ Guardado: {session_data.get('saved_at')}"
                        )
                        self.stdout.write(
                            f"🔐 Autenticado: {session_data.get('is_authenticated')}"
                        )
                        self.stdout.write(
                            f"🍪 Cookies: {len(session_data.get('cookies', []))}"
                        )

                        # Mostrar cookies importantes
                        cookies = session_data.get("cookies", [])
                        for cookie in cookies:
                            if cookie.get("name") in ["cf_clearance", "PHPSESSID"]:
                                self.stdout.write(
                                    f"  🍪 {cookie['name']}: {cookie['value'][:20]}..."
                                )

                    # Intentar validar sesión
                    self.stdout.write("\n🔍 Validando sesión...")
                    is_valid = await client.test_session_validity()

                    if is_valid:
                        self.stdout.write(
                            self.style.SUCCESS(
                                "✅ Sesión válida - ¡funciona perfectamente!"
                            )
                        )
                        self.stdout.write(
                            self.style.SUCCESS(
                                "🚀 Las sesiones guardadas están funcionando correctamente"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                "⚠️ Sesión no válida - puede necesitar nuevo login"
                            )
                        )

                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "⚠️ No hay sesión guardada - se requiere login completo"
                        )
                    )
                    self.stdout.write(
                        "💡 Haz login una vez desde la interfaz web para crear la sesión"
                    )

                await client.close()

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

        asyncio.run(test_simple())

        self.stdout.write("\n📋 Instrucciones para probar:")
        self.stdout.write("1. Ve a http://localhost:8000/matching/perfil/")
        self.stdout.write("2. Haz clic en 'Conectar a DAVINCI' (primera vez)")
        self.stdout.write("3. Espera a que se complete el login")
        self.stdout.write("4. Ejecuta este comando nuevamente para verificar la sesión")
