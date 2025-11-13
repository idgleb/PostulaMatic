"""
Comando Django para probar el scraper stealth de DV Carreras.
"""

import asyncio

from django.core.management.base import BaseCommand

from matching.clients.dvcarreras_stealth import DVCarrerasStealth


class Command(BaseCommand):
    help = "Prueba el scraper stealth de DV Carreras"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            default=2,
            help="ID del usuario para probar (default: 2)",
        )
        parser.add_argument(
            "--headless", action="store_true", help="Ejecutar en modo headless"
        )

    def handle(self, *args, **options):
        user_id = options["user_id"]
        headless = options["headless"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Iniciando prueba del scraper stealth para usuario {user_id}..."
            )
        )

        # Ejecutar la prueba
        asyncio.run(self.test_stealth_scraper(user_id, headless))

    async def test_stealth_scraper(self, user_id: int, headless: bool):
        """Prueba el scraper stealth."""

        try:
            # Crear cliente stealth
            client = DVCarrerasStealth(user_id=user_id, headless=headless)

            self.stdout.write(
                self.style.SUCCESS(f"Cliente stealth creado para usuario {user_id}")
            )

            # Iniciar navegador
            self.stdout.write("Iniciando navegador...")
            if not await client.start():
                self.stdout.write(self.style.ERROR("Error iniciando navegador"))
                return

            self.stdout.write(self.style.SUCCESS("Navegador iniciado correctamente"))

            # Realizar login
            self.stdout.write("Realizando login...")
            if await client.login():
                self.stdout.write(self.style.SUCCESS("Login exitoso"))

                # Scrapear ofertas
                self.stdout.write("Scrapeando ofertas...")
                jobs = await client.scrape_job_board(max_pages=1)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Scraping completado: {len(jobs)} ofertas encontradas"
                    )
                )

                # Mostrar resultados
                for i, job in enumerate(jobs, 1):
                    self.stdout.write(f"\n--- Oferta {i} ---")
                    self.stdout.write(f'Título: {job.get("title", "N/A")}')
                    self.stdout.write(
                        f'Descripción: {job.get("description", "N/A")[:100]}...'
                    )
                    self.stdout.write(f'Email: {job.get("email_text", "N/A")}')

            else:
                self.stdout.write(self.style.ERROR("Login fallido"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error durante la prueba: {e}"))
            import traceback

            traceback.print_exc()

        finally:
            # Cerrar navegador
            try:
                await client.close()
                self.stdout.write("Navegador cerrado")
            except:
                pass
