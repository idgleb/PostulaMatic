"""
Comando simple para probar el login manual en DV Carreras.
"""

import os
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Prueba el login manual en DV Carreras"

    def handle(self, *args, **options):
        # Crear directorio para sesiones
        sessions_dir = Path("media/dv_sessions")
        sessions_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write("🚀 Comando de login manual asistido")
        self.stdout.write("📋 Para usar este comando:")
        self.stdout.write("1. Ejecuta: python manage.py dv_login_manual_assist")
        self.stdout.write("2. Resuelve el CAPTCHA manualmente en el navegador")
        self.stdout.write("3. Presiona Enter cuando estés en el dashboard")
        self.stdout.write("4. La sesión se guardará para uso futuro")
        self.stdout.write("")
        self.stdout.write(
            "💡 Después de esto, la verificación automática usará la sesión guardada"
        )

        # Mostrar usuarios disponibles
        users = User.objects.filter(userprofile__dv_username__isnull=False)
        if users.exists():
            self.stdout.write("\n👥 Usuarios con credenciales DV:")
            for user in users:
                dv_username = user.userprofile.dv_username
                session_file = sessions_dir / f"{dv_username}_session.json"
                has_session = "✅" if session_file.exists() else "❌"
                self.stdout.write(
                    f"  {has_session} {user.username} (DV: {dv_username})"
                )
        else:
            self.stdout.write("\n❌ No hay usuarios con credenciales DV configuradas")
