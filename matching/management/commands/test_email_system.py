"""
Comando para probar el sistema de envío de emails automáticos.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from matching.models import UserCV, JobPosting, EmailSentLog
from matching.tasks_email import (
    send_personalized_email_task,
    send_bulk_emails_task,
    process_matching_and_send_emails_task,
)


class Command(BaseCommand):
    help = "Prueba el sistema de envío de emails automáticos"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            help="ID del usuario para probar",
        )
        parser.add_argument(
            "--test-type",
            type=str,
            choices=["single", "bulk", "auto-matching"],
            default="single",
            help="Tipo de prueba a realizar",
        )
        parser.add_argument(
            "--email-template",
            type=str,
            default="base",
            help="Template de email a usar",
        )
        parser.add_argument(
            "--ai-provider",
            type=str,
            choices=["openai", "anthropic"],
            default="openai",
            help="Proveedor de IA a usar",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🚀 Iniciando prueba del sistema de emails...")
        )

        # Obtener usuario
        user_id = options["user_id"]
        if not user_id:
            # Usar el primer usuario disponible
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR("❌ No hay usuarios en el sistema"))
                return
        else:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"❌ Usuario con ID {user_id} no encontrado")
                )
                return

        self.stdout.write(f"👤 Usuario: {user.username} ({user.email})")

        # Verificar que el usuario tiene CV
        user_cv = UserCV.objects.filter(user=user).first()
        if not user_cv:
            self.stdout.write(self.style.ERROR("❌ El usuario no tiene CV"))
            return

        self.stdout.write(f"📄 CV: {user_cv.id} (creado: {user_cv.created_at})")

        # Verificar que hay puestos de trabajo
        job_count = JobPosting.objects.count()
        if job_count == 0:
            self.stdout.write(
                self.style.ERROR("❌ No hay puestos de trabajo en el sistema")
            )
            return

        self.stdout.write(f"💼 Puestos disponibles: {job_count}")

        test_type = options["test_type"]
        email_template = options["email_template"]
        ai_provider = options["ai_provider"]

        self.stdout.write(
            f"🔧 Configuración: {test_type}, template: {email_template}, IA: {ai_provider}"
        )

        # Ejecutar prueba según el tipo
        if test_type == "single":
            self.test_single_email(user, user_cv, email_template, ai_provider)
        elif test_type == "bulk":
            self.test_bulk_emails(user, user_cv, email_template, ai_provider)
        elif test_type == "auto-matching":
            self.test_auto_matching(user, user_cv, email_template, ai_provider)

        self.stdout.write(self.style.SUCCESS("✅ Prueba completada"))

    def test_single_email(self, user, user_cv, email_template, ai_provider):
        """Prueba envío de email individual."""
        self.stdout.write("\n📧 Probando envío de email individual...")

        # Obtener un puesto de trabajo
        job_posting = JobPosting.objects.first()
        self.stdout.write(f"🎯 Puesto: {job_posting.title}")

        # Enviar tarea
        task_result = send_personalized_email_task.delay(
            user_id=user.id,
            cv_id=user_cv.id,
            job_id=job_posting.id,
            email_template=email_template,
            ai_provider=ai_provider,
        )

        self.stdout.write(f"🔄 Tarea enviada: {task_result.id}")
        self.stdout.write("⏳ Esperando resultado...")

        # Esperar resultado (máximo 60 segundos)
        try:
            result = task_result.get(timeout=60)
            if result["success"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Email enviado exitosamente: {result["message"]}'
                    )
                )
            else:
                self.stdout.write(self.style.ERROR(f'❌ Error: {result["error"]}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error esperando resultado: {e}"))

    def test_bulk_emails(self, user, user_cv, email_template, ai_provider):
        """Prueba envío de emails masivos."""
        self.stdout.write("\n📧 Probando envío de emails masivos...")

        # Obtener algunos puestos de trabajo
        job_postings = JobPosting.objects.all()[:5]  # Máximo 5 para la prueba
        job_ids = [job.id for job in job_postings]

        self.stdout.write(f"🎯 Puestos: {len(job_ids)}")

        # Enviar tarea
        task_result = send_bulk_emails_task.delay(
            user_id=user.id,
            job_ids=job_ids,
            email_template=email_template,
            ai_provider=ai_provider,
            batch_size=2,  # Pequeño para la prueba
            delay_between_batches=10,  # Corto para la prueba
        )

        self.stdout.write(f"🔄 Tarea enviada: {task_result.id}")
        self.stdout.write("⏳ Esperando resultado...")

        # Esperar resultado (máximo 120 segundos)
        try:
            result = task_result.get(timeout=120)
            if result["success"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Emails masivos enviados: {result["message"]}'
                    )
                )
                self.stdout.write(
                    f'📊 Total: {result["total_jobs"]}, Exitosos: {result["successful_queued"]}, Fallidos: {result["failed"]}'
                )
            else:
                self.stdout.write(self.style.ERROR(f'❌ Error: {result["error"]}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error esperando resultado: {e}"))

    def test_auto_matching(self, user, user_cv, email_template, ai_provider):
        """Prueba matching automático."""
        self.stdout.write("\n🤖 Probando matching automático...")

        # Enviar tarea
        task_result = process_matching_and_send_emails_task.delay(
            user_id=user.id,
            min_match_score=50,  # Bajo para la prueba
            email_template=email_template,
            ai_provider=ai_provider,
        )

        self.stdout.write(f"🔄 Tarea enviada: {task_result.id}")
        self.stdout.write("⏳ Esperando resultado...")

        # Esperar resultado (máximo 120 segundos)
        try:
            result = task_result.get(timeout=120)
            if result["success"]:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Matching automático completado: {result["message"]}'
                    )
                )
                self.stdout.write(f'📊 Puestos procesados: {result["total_jobs"]}')
            else:
                self.stdout.write(self.style.ERROR(f'❌ Error: {result["error"]}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error esperando resultado: {e}"))

    def show_statistics(self, user):
        """Muestra estadísticas del usuario."""
        self.stdout.write("\n📊 Estadísticas del usuario:")

        # Emails enviados
        total_emails = EmailSentLog.objects.filter(user=user).count()
        successful_emails = EmailSentLog.objects.filter(
            user=user, status="sent"
        ).count()
        failed_emails = EmailSentLog.objects.filter(user=user, status="failed").count()

        self.stdout.write(f"📧 Total emails: {total_emails}")
        self.stdout.write(f"✅ Exitosos: {successful_emails}")
        self.stdout.write(f"❌ Fallidos: {failed_emails}")

        if total_emails > 0:
            success_rate = (successful_emails / total_emails) * 100
            self.stdout.write(f"📈 Tasa de éxito: {success_rate:.1f}%")

        # Emails de hoy
        today = timezone.now().date()
        today_emails = EmailSentLog.objects.filter(
            user=user, sent_at__date=today
        ).count()

        self.stdout.write(f"📅 Emails hoy: {today_emails}")
