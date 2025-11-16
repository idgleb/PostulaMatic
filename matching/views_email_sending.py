"""
Vista para enviar CV personalizado por email con carta de presentación generada por IA.
"""

import json
import logging
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import JobPosting, UserCV, UserProfile

# PDF generation será manejado en el frontend con jsPDF


logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def send_cv_email(request):
    """
    Genera PDF del CV personalizado, carta de presentación con IA y envía email.
    """
    try:
        data = json.loads(request.body)
        cv_id = data.get("cv_id")
        job_id = data.get("job_id")
        cv_text = data.get("cv_text")
        pdf_base64 = data.get("pdf_base64")  # PDF generado en frontend

        if not all([cv_id, job_id, cv_text]):
            return JsonResponse(
                {"success": False, "error": "Faltan parámetros requeridos"}
            )

        # Obtener CV y Job
        user_cv = UserCV.objects.get(id=cv_id, user=request.user)
        job_posting = JobPosting.objects.get(id=job_id)

        # Verificar que el usuario tenga configuración SMTP
        try:
            user_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return JsonResponse(
                {
                    "success": False,
                    "error": "No tienes perfil configurado. Ve a /matching/perfil/ para configurar SMTP",
                }
            )

        if not user_profile.smtp_host or not user_profile.smtp_username:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Configuración SMTP incompleta. Ve a /matching/perfil/ para configurar tu cuenta de email",
                }
            )

        # Verificar que el puesto tenga email
        if not job_posting.email:
            return JsonResponse(
                {
                    "success": False,
                    "error": f'El puesto "{job_posting.title}" no tiene email de contacto',
                }
            )

        logger.info(f"📧 Iniciando envío de CV para puesto: {job_posting.title}")

        # 1. Convertir PDF de base64 a bytes
        import base64

        if pdf_base64:
            logger.info("📄 Usando PDF generado en frontend...")
            pdf_bytes = base64.b64decode(
                pdf_base64.split(",")[1] if "," in pdf_base64 else pdf_base64
            )
            pdf_buffer = BytesIO(pdf_bytes)
        else:
            logger.warning("⚠️ No se recibió PDF, email se enviará sin adjunto")
            pdf_buffer = None

        # 2. Generar carta de presentación con IA
        logger.info("🤖 Generando carta de presentación con IA...")
        from .services.email_generator import generate_cover_letter_with_ai

        # Desempaquetar tupla (texto, proveedor)
        cover_letter, actual_ai_provider = generate_cover_letter_with_ai(
            user_name=user_profile.user.get_full_name() or user_profile.user.username,
            job_title=job_posting.title,
            job_description=job_posting.description,
            cv_summary=cv_text[:500],  # Primeros 500 caracteres como resumen
            email_template="base",  # Por defecto usa BASE
        )
        logger.info(f"🤖 Proveedor IA usado: {actual_ai_provider}")

        # 3. Enviar email
        logger.info(f"📨 Enviando email a {job_posting.email}...")
        send_result = send_email_with_smtp(
            user_profile=user_profile,
            to_email=job_posting.email,
            subject=f"Postulación para {job_posting.title}",
            body=cover_letter,
            pdf_attachment=pdf_buffer,
            pdf_filename=f"CV_{user_profile.user.get_full_name().replace(' ', '_')}.pdf",
        )

        if send_result["success"]:
            logger.info("✅ Email enviado exitosamente")
            return JsonResponse(
                {
                    "success": True,
                    "message": f"CV enviado exitosamente a {job_posting.email}",
                }
            )
        else:
            logger.error(f"❌ Error enviando email: {send_result['error']}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Error enviando email: {send_result['error']}",
                }
            )

    except UserCV.DoesNotExist:
        return JsonResponse({"success": False, "error": "CV no encontrado"})
    except JobPosting.DoesNotExist:
        return JsonResponse({"success": False, "error": "Puesto no encontrado"})
    except Exception as e:
        logger.error(f"❌ Error en send_cv_email: {e}")
        return JsonResponse({"success": False, "error": f"Error inesperado: {str(e)}"})


def send_email_with_smtp(
    user_profile, to_email, subject, body, pdf_attachment, pdf_filename
):
    """Envía email usando la configuración SMTP del usuario."""
    import smtplib
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    try:
        # Crear mensaje
        msg = MIMEMultipart()
        msg["From"] = user_profile.smtp_username
        msg["To"] = to_email
        msg["Subject"] = subject

        # Agregar cuerpo
        msg.attach(MIMEText(body, "plain", "utf-8"))

        # Agregar PDF si existe
        if pdf_attachment:
            pdf_part = MIMEApplication(pdf_attachment.read(), _subtype="pdf")
            pdf_part.add_header(
                "Content-Disposition", "attachment", filename=pdf_filename
            )
            msg.attach(pdf_part)

        # Conectar y enviar
        logger.info(f"Conectando a {user_profile.smtp_host}:{user_profile.smtp_port}")

        if user_profile.smtp_use_tls and not user_profile.smtp_use_ssl:
            server = smtplib.SMTP(user_profile.smtp_host, user_profile.smtp_port)
            server.starttls()
        elif user_profile.smtp_use_ssl:
            server = smtplib.SMTP_SSL(user_profile.smtp_host, user_profile.smtp_port)
        else:
            server = smtplib.SMTP(user_profile.smtp_host, user_profile.smtp_port)

        # Desencriptar contraseña usando el método del modelo
        password = user_profile.get_smtp_password()

        server.login(user_profile.smtp_username, password)
        server.send_message(msg)
        server.quit()

        logger.info(f"✅ Email enviado exitosamente a {to_email}")
        return {"success": True}

    except Exception as e:
        logger.error(f"❌ Error enviando email: {e}")
        return {"success": False, "error": str(e)}
