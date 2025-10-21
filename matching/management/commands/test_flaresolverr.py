"""
Comando para probar la conexión con FlareSolverr.
"""
from django.core.management.base import BaseCommand
from matching.services.flaresolverr_client import test_flaresolverr_connection


class Command(BaseCommand):
    help = "Prueba la conexión con FlareSolverr"

    def handle(self, *args, **options):
        self.stdout.write("Probando conexión con FlareSolverr...")
        
        result = test_flaresolverr_connection()
        
        if result["success"]:
            self.stdout.write(
                self.style.SUCCESS(f"✅ {result['message']}")
            )
            self.stdout.write(f"Respuesta: {result['response']}")
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ {result['message']}")
            )

