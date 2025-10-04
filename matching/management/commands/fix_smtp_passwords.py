"""
Comando para detectar y limpiar contraseñas SMTP corruptas.
"""

from django.core.management.base import BaseCommand
from matching.models import UserProfile
from matching.utils.encryption import credential_encryption


class Command(BaseCommand):
    help = "Detecta y limpia contraseñas SMTP corruptas"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo mostrar qué contraseñas están corruptas sin limpiarlas",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Limpiar contraseñas corruptas (las deja vacías para re-ingreso)",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        fix = options["fix"]

        if not dry_run and not fix:
            self.stdout.write(
                self.style.ERROR(
                    "Debes especificar --dry-run para ver o --fix para corregir"
                )
            )
            return

        # Obtener todos los perfiles con contraseña SMTP
        profiles_with_smtp = UserProfile.objects.exclude(
            smtp_password__isnull=True
        ).exclude(smtp_password="")

        self.stdout.write(
            f"Revisando {profiles_with_smtp.count()} perfiles con contraseña SMTP..."
        )

        corrupted_count = 0
        fixed_count = 0

        for profile in profiles_with_smtp:
            try:
                # Intentar desencriptar la contraseña
                decrypted_password = credential_encryption.decrypt(profile.smtp_password)
                
                # Si llegamos aquí, la contraseña está bien
                self.stdout.write(
                    f"✅ {profile.user.username}: Contraseña OK"
                )
                
            except Exception as e:
                # Contraseña corrupta
                corrupted_count += 1
                
                self.stdout.write(
                    self.style.WARNING(
                        f"❌ {profile.user.username}: Contraseña corrupta - {str(e)}"
                    )
                )

                if fix:
                    # Limpiar contraseña corrupta
                    profile.smtp_password = ""
                    profile.save()
                    fixed_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"🔧 {profile.user.username}: Contraseña limpiada"
                        )
                    )

        # Resumen
        self.stdout.write("\n" + "="*50)
        if dry_run:
            self.stdout.write(f"Contraseñas corruptas encontradas: {corrupted_count}")
            self.stdout.write(
                self.style.WARNING(
                    "Usa --fix para limpiar las contraseñas corruptas"
                )
            )
        else:
            self.stdout.write(f"Contraseñas corruptas encontradas: {corrupted_count}")
            self.stdout.write(f"Contraseñas limpiadas: {fixed_count}")
            if fixed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Los usuarios con contraseñas limpiadas deberán re-ingresar su contraseña SMTP"
                    )
                )
