"""
Tarea Celery para envío masivo de emails con CV personalizado.
"""

import logging
import time
from io import BytesIO

from celery import shared_task
from django.contrib.auth.models import User

from .models import EmailSentLog, JobPosting, UserCV, UserProfile
from .services.cv_personalizer import CVPersonalizationService
from .services.email_generator import generate_cover_letter_with_ai

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def send_bulk_emails_task(
    self,
    user_id,
    job_ids,
    cv_id=None,
    email_template="base",
    ai_provider="openai",
    batch_size=5,
    delay_between_batches=300,
):
    """
    Envía emails masivos a múltiples puestos con CV personalizado.

    Args:
        user_id: ID del usuario
        job_ids: Lista de IDs de puestos
        cv_id: ID del CV a usar (opcional, usa el más reciente si no se especifica)
        email_template: Template de email a usar
        ai_provider: Proveedor de IA primario (openai o anthropic)
        batch_size: Tamaño del lote
        delay_between_batches: Delay en segundos entre lotes
    """
    logger.info(f"📧 Iniciando envío masivo para usuario {user_id}")
    logger.info(
        f"📋 Total puestos: {len(job_ids)}, Lote: {batch_size}, Delay: {delay_between_batches}s"
    )

    try:
        # Obtener usuario
        user = User.objects.get(id=user_id)

        # Obtener CV específico o el más reciente
        if cv_id:
            try:
                user_cv = UserCV.objects.get(id=cv_id, user=user)
                cv_name = (
                    user_cv.original_file.name.split("/")[-1]
                    if user_cv.original_file
                    else f"CV #{cv_id}"
                )
                logger.info(f"📄 Usando CV especificado: {cv_name} (ID: {cv_id})")
            except UserCV.DoesNotExist:
                logger.error(f"❌ CV {cv_id} no encontrado para usuario {user_id}")
                return {"success": False, "error": f"CV con ID {cv_id} no encontrado"}
        else:
            user_cv = UserCV.objects.filter(user=user).order_by("-created_at").first()
            if user_cv:
                cv_name = (
                    user_cv.original_file.name.split("/")[-1]
                    if user_cv.original_file
                    else f"CV #{user_cv.id}"
                )
                logger.info(f"📄 Usando CV más reciente: {cv_name}")

        if not user_cv:
            logger.error(f"❌ Usuario {user_id} no tiene CV")
            return {"success": False, "error": "Usuario no tiene CV"}

        # Obtener perfil del usuario
        try:
            user_profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            logger.error(f"❌ Usuario {user_id} no tiene perfil")
            return {"success": False, "error": "Usuario no tiene perfil configurado"}

        # Verificar configuración SMTP
        if not user_profile.smtp_host or not user_profile.smtp_username:
            logger.error(f"❌ Usuario {user_id} no tiene SMTP configurado")
            return {"success": False, "error": "Configuración SMTP incompleta"}

        # Dividir en lotes
        total_jobs = len(job_ids)
        batches = [
            job_ids[i : i + batch_size] for i in range(0, total_jobs, batch_size)
        ]

        logger.info(f"📦 Dividido en {len(batches)} lotes")

        results = {"total": total_jobs, "sent": 0, "failed": 0, "batches_processed": 0}

        # Procesar cada lote
        for batch_num, batch_job_ids in enumerate(batches, 1):
            logger.info(
                f"📦 Procesando lote {batch_num}/{len(batches)} ({len(batch_job_ids)} puestos)"
            )

            for job_id in batch_job_ids:
                try:
                    # Obtener puesto
                    job_posting = JobPosting.objects.get(id=job_id)
                    logger.info(f"📄 Procesando puesto: {job_posting.title}")

                    # Verificar que tenga email
                    if not job_posting.email:
                        logger.warning(
                            f"⚠️ Puesto {job_posting.title} sin email, saltando"
                        )
                        results["failed"] += 1
                        _create_email_log(
                            user=user,
                            cv=user_cv,
                            job_posting=job_posting,
                            status="failed",
                            error_message="Puesto sin email de contacto",
                            task_id=self.request.id,
                            email_template=email_template,
                            ai_provider=ai_provider,
                        )
                        continue

                    # 1. Personalizar CV
                    logger.info(f"🤖 Personalizando CV para {job_posting.title}")
                    personalizer = CVPersonalizationService()

                    # Usar la firma correcta del servicio unificado
                    personalization_result = personalizer.personalize_cv_for_job(
                        user_cv=user_cv,
                        job_posting=job_posting,
                        user_profile=None,  # Opcional, podría pasarse si se necesita
                    )

                    if not personalization_result.get("success"):
                        logger.error(
                            f"❌ Error personalizando CV: {personalization_result.get('error')}"
                        )
                        results["failed"] += 1
                        _create_email_log(
                            user=user,
                            cv=user_cv,
                            job_posting=job_posting,
                            status="failed",
                            error_message=f"Error personalizando CV: {personalization_result.get('error')}",
                            task_id=self.request.id,
                            email_template=email_template,
                            ai_provider=ai_provider,
                        )
                        continue

                    # El servicio retorna el CV como estructura JSON, lo convertimos a texto
                    personalized_cv = personalization_result["personalized_cv"]
                    cv_text = _format_cv_as_text(personalized_cv)

                    # 2. Extraer nombre del CV si está disponible
                    user_name = _extract_name_from_cv(user, user_cv)
                    logger.info(f"👤 Nombre detectado: {user_name}")

                    # 3. Generar PDF del CV
                    logger.info(f"📄 Generando PDF del CV")
                    pdf_buffer = _generate_cv_pdf_simple(cv_text, user_name)

                    # 4. Generar carta de presentación con IA
                    logger.info(
                        f"✍️ Generando carta de presentación con IA (template: {email_template})"
                    )
                    cover_letter, actual_ai_provider = generate_cover_letter_with_ai(
                        user_name=user_name,
                        job_title=job_posting.title,
                        job_description=job_posting.description,
                        cv_summary=cv_text[:500],
                        email_template=email_template,
                    )
                    logger.info(
                        f"🤖 Proveedor IA usado realmente: {actual_ai_provider}"
                    )

                    # 4. Enviar email
                    logger.info(f"📨 Enviando email a {job_posting.email}")
                    send_result = _send_email_with_smtp(
                        user_profile=user_profile,
                        to_email=job_posting.email,
                        subject=f"Postulación para {job_posting.title}",
                        body=cover_letter,
                        pdf_attachment=pdf_buffer,
                        pdf_filename=f"CV_{user_name.replace(' ', '_')}.pdf",
                    )

                    if send_result["success"]:
                        logger.info(
                            f"✅ Email enviado exitosamente a {job_posting.email}"
                        )
                        results["sent"] += 1
                        _create_email_log(
                            user=user,
                            cv=user_cv,
                            job_posting=job_posting,
                            status="sent",
                            sent_to=job_posting.email,
                            email_subject=f"Postulación para {job_posting.title}",
                            email_body=cover_letter,
                            task_id=self.request.id,
                            email_template=email_template,
                            ai_provider=actual_ai_provider,  # Usar el proveedor real, no el solicitado
                            pdf_buffer=pdf_buffer,
                        )
                    else:
                        logger.error(f"❌ Error enviando email: {send_result['error']}")
                        results["failed"] += 1
                        _create_email_log(
                            user=user,
                            cv=user_cv,
                            job_posting=job_posting,
                            status="failed",
                            error_message=send_result["error"],
                            task_id=self.request.id,
                            email_template=email_template,
                            ai_provider=ai_provider,
                        )

                except JobPosting.DoesNotExist:
                    logger.error(f"❌ Puesto {job_id} no encontrado")
                    results["failed"] += 1
                except Exception as e:
                    logger.error(f"❌ Error procesando puesto {job_id}: {e}")
                    results["failed"] += 1

            results["batches_processed"] += 1

            # Delay entre lotes (excepto en el último)
            if batch_num < len(batches):
                logger.info(
                    f"⏱️ Esperando {delay_between_batches}s antes del siguiente lote..."
                )
                time.sleep(delay_between_batches)

        logger.info(
            f"✅ Envío masivo completado: {results['sent']} enviados, {results['failed']} fallidos"
        )

        return {"success": True, "results": results}

    except User.DoesNotExist:
        logger.error(f"❌ Usuario {user_id} no encontrado")
        return {"success": False, "error": "Usuario no encontrado"}
    except Exception as e:
        logger.error(f"❌ Error en envío masivo: {e}")
        return {"success": False, "error": str(e)}


def _format_cv_as_text(cv_dict):
    """
    Convierte el CV estructurado (formato del servicio unificado) a texto plano.
    Coincide con el formato usado en cv_personalization_test.html
    """
    lines = []

    # Header del CV
    header = cv_dict.get("header", {})
    full_name = header.get("full_name", "NOMBRE APELLIDO")
    city = header.get("city", "Ciudad")
    country = header.get("country", "País")
    phone = header.get("phone", "")
    email = header.get("email", "")
    links = header.get("links", {})
    linkedin = links.get("linkedin", "")
    github = links.get("github", "")
    portfolio = links.get("portfolio", "")
    target_title = header.get("target_title", "TÍTULO / ROL OBJETIVO")

    # Nombre
    lines.append(full_name)

    # Línea de contacto
    contact_parts = [f"{city}, {country}"]
    if phone:
        contact_parts.append(phone)
    if email:
        contact_parts.append(email)
    if linkedin:
        contact_parts.append(f"LinkedIn: {linkedin}")
    if github:
        contact_parts.append(f"GitHub: {github}")
    if portfolio:
        contact_parts.append(f"Portfolio: {portfolio}")

    lines.append(" | ".join(contact_parts))
    lines.append("")
    lines.append(target_title)
    lines.append("")

    # RESUMEN
    summary = cv_dict.get("summary", "")
    if summary:
        lines.append("RESUMEN")
        lines.append(summary)
        lines.append("")

    # COMPETENCIAS
    skills = cv_dict.get("skills", [])
    if skills:
        lines.append("COMPETENCIAS")
        lines.append(" · ".join(skills))
        lines.append("")

    # EXPERIENCIA
    experience = cv_dict.get("experience", [])
    if experience:
        lines.append("EXPERIENCIA")
        for exp in experience:
            company = exp.get("company", "EMPRESA")
            role = exp.get("role", "Cargo")
            exp_city = exp.get("city", "Ciudad")
            exp_country = exp.get("country", "País")
            start_date = exp.get("start_date", "")
            end_date = exp.get("end_date")
            context = exp.get("context", "")
            bullets = exp.get("bullets", [])

            # Manejar end_date correctamente (None -> "Presente")
            if end_date is None or end_date == "None" or end_date == "":
                end_date = "Presente"

            date_range = f" | {start_date} – {end_date}" if start_date else ""
            lines.append(f"{company} | {role} — {exp_city}, {exp_country}{date_range}")
            if context:
                lines.append(f"Contexto: {context}")
            for bullet in bullets:
                lines.append(f"• {bullet}")
            lines.append("")

    # PROYECTOS
    projects = cv_dict.get("projects", [])
    if projects:
        lines.append("PROYECTOS")
        for proj in projects:
            name = proj.get("name", "Proyecto")
            role = proj.get("role", "")
            tools = proj.get("tools", [])
            bullet = proj.get("bullet", "")
            url = proj.get("url", "")

            tools_str = ", ".join(tools) if tools else ""
            proj_header = f"{name}"
            if role:
                proj_header += f" | {role}"
            if tools_str:
                proj_header += f" | {tools_str}"

            lines.append(proj_header)
            if bullet:
                lines.append(f"• {bullet}")
            if url:
                lines.append(f"Enlace: {url}")
            lines.append("")

    # EDUCACIÓN
    education = cv_dict.get("education", [])
    if education:
        lines.append("EDUCACIÓN")
        for edu in education:
            degree = edu.get("degree", "")
            institution = edu.get("institution", "")
            edu_city = edu.get("city", "")
            edu_country = edu.get("country", "")

            if degree and institution:  # Solo mostrar si hay datos reales
                location = f" | {edu_city}" if edu_city else ""
                lines.append(f"{degree} — {institution}{location}")
        lines.append("")

    # IDIOMAS
    languages = cv_dict.get("languages", [])
    if languages:
        lines.append("IDIOMAS")
        for lang in languages:
            language = lang.get("language", "")
            level = lang.get("level", "")
            if language and level:
                lines.append(f"{language} ({level})")
        lines.append("")

    # EXTRAS
    extras = cv_dict.get("extras", {})
    if extras:
        availability = extras.get("availability", "")
        awards = extras.get("awards", [])
        volunteering = extras.get("volunteering", [])
        work_permit = extras.get("work_permit", [])

        if availability or awards or volunteering or work_permit:
            lines.append("EXTRAS")
            if availability:
                lines.append(availability)
            for award in awards:
                lines.append(award)
            for vol in volunteering:
                lines.append(vol)
            for perm in work_permit:
                lines.append(perm)
            lines.append("")

    return "\n".join(lines)


def _generate_cv_pdf_simple(cv_text, user_name):
    """Genera un PDF simple del CV usando ReportLab."""
    from io import BytesIO

    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    try:
        # Crear buffer en memoria
        buffer = BytesIO()

        # Crear documento PDF
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        # Estilos
        styles = getSampleStyleSheet()

        # Estilo para texto normal
        normal_style = ParagraphStyle(
            "CustomNormal",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            fontName="Helvetica",
        )

        # Estilo para encabezados
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=12,
            leading=16,
            textColor="#333333",
            fontName="Helvetica-Bold",
            spaceAfter=6,
        )

        # Construir contenido
        story = []

        # Procesar el texto línea por línea
        lines = cv_text.split("\n")

        for line in lines:
            line = line.strip()

            if not line:
                # Línea vacía = espacio
                story.append(Spacer(1, 0.1 * inch))
                continue

            # Detectar secciones (palabras en mayúsculas)
            if line.isupper() and len(line) > 3:
                # Es un encabezado de sección
                story.append(Spacer(1, 0.15 * inch))
                story.append(Paragraph(line, heading_style))
                story.append(Spacer(1, 0.05 * inch))
            else:
                # Texto normal
                # Escapar caracteres especiales para XML
                line = (
                    line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                )
                story.append(Paragraph(line, normal_style))

        # Generar PDF
        doc.build(story)

        # Obtener contenido del buffer
        buffer.seek(0)
        logger.info(f"✅ PDF generado exitosamente: {len(buffer.getvalue())} bytes")
        return buffer

    except Exception as e:
        logger.error(f"❌ Error generando PDF: {e}")
        return None


def _extract_name_from_cv(user, user_cv):
    """
    Extrae el nombre del usuario desde el CV parseado.
    Busca en las primeras 5 líneas del CV un nombre (máximo 4 palabras).

    Args:
        user: Usuario de Django
        user_cv: Objeto UserCV

    Returns:
        str: Nombre extraído o fallback al username
    """
    # Fallback por defecto
    default_name = user.get_full_name() or user.username

    if not user_cv or not user_cv.parsed_text:
        return default_name

    # Buscar nombre en las primeras líneas
    first_lines = user_cv.parsed_text.split("\n")[:5]

    for line in first_lines:
        # Limpiar la línea (quitar # y espacios)
        clean_line = line.strip().replace("#", "").strip()

        # Verificar que sea un nombre válido:
        # - No vacío
        # - Máximo 4 palabras (nombre completo típico)
        # - No es un título de sección (como "DESARROLLADOR")
        # - Contiene al menos una letra mayúscula
        if (
            clean_line
            and len(clean_line.split()) <= 4
            and not clean_line.isupper()
            and any(c.isupper() for c in clean_line)
        ):
            return clean_line

    return default_name


def _send_email_with_smtp(
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

        # Desencriptar contraseña
        password = user_profile.get_smtp_password()

        server.login(user_profile.smtp_username, password)
        server.send_message(msg)
        server.quit()

        logger.info(f"✅ Email enviado exitosamente a {to_email}")
        return {"success": True}

    except Exception as e:
        logger.error(f"❌ Error enviando email: {e}")
        return {"success": False, "error": str(e)}


def _create_email_log(
    user,
    cv,
    job_posting,
    status,
    sent_to="",
    email_subject="",
    email_body="",
    error_message="",
    task_id="",
    email_template="base",
    ai_provider="openai",
    pdf_buffer=None,
):
    """Crea un registro de email enviado."""
    import os

    from django.core.files.base import ContentFile

    try:
        email_log = EmailSentLog.objects.create(
            user=user,
            cv=cv,
            job_posting=job_posting,
            email_subject=email_subject or f"Postulación para {job_posting.title}",
            email_body=email_body or "",
            sent_to=sent_to or job_posting.email or "",
            status=status,
            error_message=error_message,
            task_id=task_id,
            email_template=email_template,
            ai_provider=ai_provider,
        )

        # Guardar el PDF personalizado si se proporcionó
        if pdf_buffer and status == "sent":
            try:
                # Generar nombre de archivo único
                job_title_safe = "".join(
                    c
                    for c in (job_posting.title if job_posting else "puesto")[:30]
                    if c.isalnum() or c in (" ", "-", "_")
                ).strip()
                filename = f"CV_{user.username}_{job_title_safe}_{email_log.id}.pdf"

                # Guardar el PDF
                pdf_buffer.seek(0)  # Volver al inicio del buffer
                email_log.personalized_cv_file.save(
                    filename, ContentFile(pdf_buffer.read()), save=True
                )
                logger.info(f"📎 PDF personalizado guardado: {filename}")
            except Exception as pdf_error:
                logger.error(f"⚠️ Error guardando PDF personalizado: {pdf_error}")

        logger.info(f"📝 Log de email creado: {status}")
    except Exception as e:
        logger.error(f"❌ Error creando log de email: {e}")
