import json
import logging
import os

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from matching.tasks_dv import verify_dv_login_task

from .forms import (CVUploadForm, DVCredentialsForm, EmailConfigForm,
                    MatchingConfigForm, SMTPConfigForm)
from .models import (EmailSentLog, JobPosting, MatchScore, ScrapingLog, UserCV,
                     UserProfile)
from .services.cv_parser import cv_parser
from .services.skills_extractor import skills_extractor
from .utils.log_capture import cleanup_log_capture, setup_log_capture

# from .tasks import scrape_dvcarreras_jobs  # Comentado para usar Playwright

logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    """Dashboard principal del usuario."""

    from django.utils import timezone

    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]

    # Estadísticas básicas
    today = timezone.now().date()

    # Contar emails enviados hoy
    emails_sent_today = EmailSentLog.objects.filter(
        user=request.user, sent_at__date=today
    ).count()

    # Contar emails fallidos
    emails_failed = EmailSentLog.objects.filter(
        user=request.user, status="failed"
    ).count()

    stats = {
        "total_cvs": UserCV.objects.filter(user=request.user).count(),
        "total_matches": MatchScore.objects.filter(user=request.user).count(),
        "emails_sent_today": emails_sent_today,
        "emails_failed": emails_failed,
    }

    # Obtener ofertas recientes y matches para mostrar en el dashboard
    recent_jobs = JobPosting.objects.all().order_by("-created_at")[:5]
    recent_matches = MatchScore.objects.filter(user=request.user).order_by(
        "-created_at"
    )[:5]

    context = {
        "title": "Dashboard",
        "profile": user_profile,
        "stats": stats,
        "recent_jobs": recent_jobs,
        "recent_matches": recent_matches,
    }
    return render(request, "matching/dashboard.html", context)


@login_required
def profile_view(request):
    """Vista para editar perfil de usuario."""
    # Forzar consulta fresca para obtener el estado actualizado
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    # Refrescar desde la base de datos para obtener el estado más reciente
    profile.refresh_from_db()

    # Crear formularios separados
    smtp_form = SMTPConfigForm(instance=profile)
    dv_form = DVCredentialsForm(instance=profile)
    matching_form = MatchingConfigForm(instance=profile)
    email_form = EmailConfigForm(instance=profile)

    if request.method == "POST":
        section = request.POST.get("section")

        # Verificar si es petición AJAX
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

        if section == "smtp":
            smtp_form = SMTPConfigForm(request.POST, instance=profile)
            if smtp_form.is_valid():
                smtp_form.save()
                if is_ajax:
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Configuración SMTP y nombre para mostrar guardados correctamente. Los emails se enviarán desde tu cuenta configurada.",
                        }
                    )
                else:
                    messages.success(
                        request,
                        "Configuración SMTP y nombre para mostrar guardados correctamente.",
                    )
            else:
                if is_ajax:
                    # Obtener errores específicos del formulario
                    errors = []
                    for field, field_errors in smtp_form.errors.items():
                        for error in field_errors:
                            errors.append(f"{field}: {error}")

                    return JsonResponse(
                        {
                            "success": False,
                            "message": f'❌ Error en la configuración SMTP: {"; ".join(errors)}',
                        }
                    )
        elif section == "dv":
            dv_form = DVCredentialsForm(request.POST, instance=profile)
            if dv_form.is_valid():
                dv_form.save()
                # Establecer estado "en proceso" al guardar credenciales
                profile.set_dv_connection_verified(None)  # None = in_progress
                profile.save()
                if is_ajax:
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Credenciales INTRANET DAVINCI guardadas correctamente. El sistema podrá acceder a las ofertas de trabajo.",
                        }
                    )
                else:
                    messages.success(
                        request,
                        "Credenciales INTRANET DAVINCI guardadas correctamente.",
                    )
            else:
                if is_ajax:
                    # Obtener errores específicos del formulario
                    errors = []
                    for field, field_errors in dv_form.errors.items():
                        for error in field_errors:
                            errors.append(f"{field}: {error}")

                    return JsonResponse(
                        {
                            "success": False,
                            "message": f'❌ Error en las credenciales INTRANET DAVINCI: {"; ".join(errors)}',
                        }
                    )
        elif section == "matching":
            # Leer el valor ANTES de crear el formulario para evitar que Django lo modifique
            old_threshold = profile.match_threshold
            logger.info(
                f"Matching form - old_threshold (ANTES de crear formulario): {old_threshold}"
            )

            matching_form = MatchingConfigForm(request.POST, instance=profile)
            logger.info(f"Matching form - POST data: {request.POST}")
            logger.info(f"Matching form - Form is_valid: {matching_form.is_valid()}")
            if matching_form.errors:
                logger.info(f"Matching form - Form errors: {matching_form.errors}")

            if matching_form.is_valid():
                # Leer el nuevo valor ANTES de guardar
                new_threshold = matching_form.cleaned_data["match_threshold"]
                logger.info(f"Matching form - new_threshold: {new_threshold}")
                logger.info(
                    f"Matching form - ¿Cambió umbral?: {old_threshold != new_threshold}"
                )

                matching_form.save()

                if old_threshold != new_threshold:
                    try:
                        # Importar tarea de recálculo
                        from .tasks import recalculate_matches_for_user

                        # Ejecutar recálculo en background
                        task = recalculate_matches_for_user.delay(request.user.id)

                        logger.info(
                            f"Recálculo de matches iniciado para usuario {request.user.id} (task: {task.id})"
                        )

                        if is_ajax:
                            return JsonResponse(
                                {
                                    "success": True,
                                    "message": f"✅ Configuración guardada y recálculo iniciado. Umbral cambiado de {old_threshold}% a {new_threshold}%.",
                                    "recalculation_started": True,
                                    "task_id": task.id,
                                }
                            )
                        else:
                            messages.success(
                                request,
                                f"✅ Configuración guardada y recálculo iniciado. Umbral cambiado de {old_threshold}% a {new_threshold}%.",
                            )
                    except Exception as e:
                        logger.error(
                            f"Error iniciando recálculo para usuario {request.user.id}: {e}"
                        )
                        if is_ajax:
                            return JsonResponse(
                                {
                                    "success": True,
                                    "message": "✅ Configuración guardada. ⚠️ Error al iniciar recálculo automático.",
                                    "recalculation_started": False,
                                }
                            )
                        else:
                            messages.warning(
                                request,
                                "✅ Configuración guardada. ⚠️ Error al iniciar recálculo automático.",
                            )
                else:
                    # Umbral no cambió
                    if is_ajax:
                        return JsonResponse(
                            {
                                "success": True,
                                "message": "✅ Configuración de matching guardada correctamente.",
                                "recalculation_started": False,
                            }
                        )
                    else:
                        messages.success(
                            request,
                            "✅ Configuración de matching guardada correctamente.",
                        )
            else:
                if is_ajax:
                    # Obtener errores específicos del formulario
                    errors = []
                    for field, field_errors in matching_form.errors.items():
                        for error in field_errors:
                            errors.append(f"{field}: {error}")

                    return JsonResponse(
                        {
                            "success": False,
                            "message": f'❌ Error en la configuración de matching: {"; ".join(errors)}',
                        }
                    )
        elif section == "email":
            email_form = EmailConfigForm(request.POST, instance=profile)
            if email_form.is_valid():
                email_form.save()
                if is_ajax:
                    return JsonResponse(
                        {
                            "success": True,
                            "message": "Configuración de envíos de emails guardada correctamente.",
                        }
                    )
                else:
                    messages.success(
                        request,
                        "Configuración de envíos de emails guardada correctamente.",
                    )
            else:
                if is_ajax:
                    # Obtener errores específicos del formulario
                    errors = []
                    for field, field_errors in email_form.errors.items():
                        for error in field_errors:
                            errors.append(f"{field}: {error}")

                    return JsonResponse(
                        {
                            "success": False,
                            "message": f'❌ Error en la configuración de envíos: {"; ".join(errors)}',
                        }
                    )

    context = {
        "smtp_form": smtp_form,
        "dv_form": dv_form,
        "matching_form": matching_form,
        "email_form": email_form,
        "profile": profile,
        "title": "Mi Perfil",
    }
    return render(request, "matching/profile.html", context)


@login_required
def get_cv_progress(request, progress_id):
    """Vista AJAX para consultar el progreso del procesamiento de un CV."""
    from django.core.cache import cache

    # Leer directamente del cache sin inicializar
    cache_key = f"cv_progress_{progress_id}"
    progress_data = cache.get(cache_key)

    if not progress_data:
        return JsonResponse(
            {"success": False, "error": "Progreso no encontrado"}, status=404
        )

    return JsonResponse({"success": True, "progress": progress_data})


@login_required
@require_http_methods(["POST"])
def cancel_cv_task(request):
    """Vista AJAX para cancelar una tarea de procesamiento de CV."""
    import json

    from celery.result import AsyncResult
    from django.core.cache import cache

    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")
        progress_id = data.get("progress_id")

        if not task_id:
            return JsonResponse({"success": False, "error": "task_id no proporcionado"})

        logger.info(f"🛑 Cancelando tarea de CV: {task_id}")

        # Revocar la tarea de Celery
        AsyncResult(task_id).revoke(terminate=True, signal="SIGKILL")

        # Si tenemos progress_id, actualizar el progreso para marcar como cancelado
        if progress_id:
            cache_key = f"cv_progress_{progress_id}"
            progress_data = cache.get(cache_key)

            if progress_data:
                # Marcar como completado con error
                progress_data["completed"] = True
                progress_data["error"] = "Procesamiento cancelado por el usuario"

                # Actualizar todos los pasos "in_progress" a "error"
                for step in progress_data.get("steps", []):
                    if step.get("status") == "in_progress":
                        step["status"] = "error"
                        step["message"] = "Cancelado"

                cache.set(cache_key, progress_data, 600)
                logger.info(
                    f"📊 Progreso actualizado para {progress_id}: marcado como cancelado"
                )

        logger.info(f"✅ Tarea {task_id} cancelada exitosamente")

        return JsonResponse(
            {"success": True, "message": "Tarea cancelada exitosamente"}
        )

    except Exception as e:
        logger.error(f"❌ Error cancelando tarea: {e}")
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def upload_cv_view(request):
    """Vista AJAX para subir CV con parsing automático."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Método no permitido"})

    # Solo manejar requests AJAX
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse(
            {"success": False, "message": "Solo se permiten requests AJAX"}
        )

    form = CVUploadForm(request.POST, request.FILES)
    if form.is_valid():
        print(
            "🔍 UPLOAD: Formulario válido, iniciando procesamiento"
        )  # Print para debugging
        try:
            import os
            import uuid

            from django.conf import settings

            from matching.tasks import process_cv_async
            from matching.utils.progress_tracker import ProgressTracker

            # Crear tracker de progreso
            progress_tracker = ProgressTracker()
            progress_id = progress_tracker.progress_id
            progress_tracker.update_step("upload", "completed", "Archivo recibido")

            uploaded_file = form.cleaned_data.get("original_file")
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()

            # Guardar archivo en directorio temporal dentro de MEDIA_ROOT (compartido entre contenedores)
            progress_tracker.update_step(
                "temp_file", "in_progress", "Guardando archivo temporal"
            )
            temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
            os.makedirs(temp_dir, exist_ok=True)

            # Generar nombre único para el archivo temporal
            temp_filename = f"{uuid.uuid4()}{file_ext}"
            temp_file_path = os.path.join(temp_dir, temp_filename)

            # Guardar el archivo
            with open(temp_file_path, "wb+") as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            progress_tracker.update_step(
                "temp_file", "completed", f"Archivo guardado: {temp_filename}"
            )

            # Lanzar tarea de Celery en background
            logger.info(
                f"🚀 Lanzando tarea asíncrona para procesar CV: {uploaded_file.name}"
            )
            logger.info(f"📁 Archivo temporal: {temp_file_path}")
            task = process_cv_async.delay(
                user_id=request.user.id,
                file_path=temp_file_path,
                original_filename=uploaded_file.name,
                progress_id=progress_id,
            )

            # Devolver respuesta inmediata con progress_id y task_id
            return JsonResponse(
                {
                    "success": True,
                    "message": "CV recibido, procesando en background...",
                    "progress_id": progress_id,
                    "task_id": task.id,  # ID de la tarea de Celery para poder cancelarla
                    "processing": True,  # Indica que el procesamiento está en curso
                }
            )

        except Exception as e:
            logger.error(f"❌ Error iniciando procesamiento de CV: {e}")
            return JsonResponse(
                {"success": False, "error": f"Error iniciando procesamiento: {str(e)}"}
            )

    # Si el formulario no es válido
    return JsonResponse(
        {"success": False, "message": "Formulario inválido", "errors": form.errors}
    )


@login_required
def upload_cv_view_OLD_SYNC(request):
    """Vista AJAX para subir CV con parsing automático (VERSIÓN SÍNCRONA ORIGINAL)."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Método no permitido"})

    # Solo manejar requests AJAX
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return JsonResponse(
            {"success": False, "message": "Solo se permiten requests AJAX"}
        )

    form = CVUploadForm(request.POST, request.FILES)
    if form.is_valid():
        print(
            "🔍 UPLOAD: Formulario válido, iniciando procesamiento"
        )  # Print para debugging
        # No crear registro en BD aún. Guardamos el archivo a un temporal y solo
        # creamos el `UserCV` si el parseo con IA fue exitoso.
        try:
            import os
            import tempfile

            from matching.utils.progress_tracker import ProgressTracker

            # Crear tracker de progreso
            progress_tracker = ProgressTracker()
            progress_tracker.update_step("upload", "completed", "Archivo recibido")

            uploaded_file = form.cleaned_data.get("original_file")
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()

            # Persistir a archivo temporal para pasar ruta al parser
            progress_tracker.update_step(
                "temp_file", "in_progress", "Guardando archivo temporal"
            )
            tmp_path = None
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                for chunk in uploaded_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            progress_tracker.update_step(
                "temp_file",
                "completed",
                f"Archivo guardado: {os.path.basename(tmp_path)}",
            )

            file_path = tmp_path

            # Verificar que el formato es soportado
            if cv_parser.is_supported(file_path):
                logger.info("Procesando CV inmediatamente (pre-guardado)")
                print(
                    "🔍 UPLOAD: Procesando CV inmediatamente (pre-guardado)"
                )  # Print para debugging

                # Configurar captura de logs
                log_capture_instance = setup_log_capture()
                log_capture_instance.add_log(
                    "INFO",
                    f"🚀 Iniciando procesamiento de CV: {uploaded_file.name}",
                    "Inicio",
                )
                captured_logs = []  # Inicializar variable

                try:
                    # Extraer texto del archivo
                    progress_tracker.update_step(
                        "pdf_to_images", "in_progress", "Convirtiendo PDF a imágenes"
                    )
                    parse_result = cv_parser.parse_cv(
                        file_path, progress_tracker=progress_tracker
                    )
                    parsed_text = parse_result["text"]
                    warning_message = parse_result.get("warning_message", "")

                    # Obtener logs capturados
                    captured_logs = log_capture_instance.get_logs()
                    cleanup_log_capture()

                    # Verificar que el texto no esté vacío (error de IA)
                    if not parsed_text or parsed_text.strip() == "":
                        error_msg = "❌ Error de IA: No se pudo extraer texto del CV. Verifica la configuración de IA."
                        logger.error(error_msg)
                        return JsonResponse(
                            {
                                "success": False,
                                "error": error_msg,
                                "error_type": "ai_error",
                                "logs": captured_logs,
                            }
                        )

                    # Procesar todos los archivos sin validación previa
                    progress_tracker.update_step(
                        "skills_extraction",
                        "in_progress",
                        "Extrayendo habilidades del texto",
                    )
                    skills_data = skills_extractor.extract_skills(parsed_text)
                    progress_tracker.update_step(
                        "skills_extraction",
                        "completed",
                        f"{len(skills_data.get('skills', []))} habilidades detectadas",
                    )

                    # Crear y guardar el CV AHORA (post-éxito de IA)
                    progress_tracker.update_step(
                        "db_save", "in_progress", "Guardando CV en base de datos"
                    )
                    from .models import UserCV

                    cv = UserCV(user=request.user)
                    # Resetear puntero del archivo para poder guardarlo
                    try:
                        uploaded_file.seek(0)
                    except Exception:
                        pass
                    cv.original_file.save(uploaded_file.name, uploaded_file, save=False)
                    cv.parsed_text = parsed_text
                    cv.skills = skills_data
                    cv.save()
                    progress_tracker.update_step(
                        "db_save", "completed", f"CV guardado con ID: {cv.id}"
                    )

                    logger.info(f"CV procesado: {cv.skills_count} skills detectadas")

                    # Iniciar recálculo automático en background (sin modal)
                    try:
                        from .tasks import recalculate_matches_for_user

                        task = recalculate_matches_for_user.delay(request.user.id)
                        logger.info(
                            f"Recálculo automático iniciado en background después de subir CV para usuario {request.user.id} (task: {task.id})"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error iniciando recálculo automático después de subir CV: {e}"
                        )

                    # Marcar progreso como completado
                    progress_tracker.set_complete(
                        f"CV procesado exitosamente: {cv.skills_count} habilidades"
                    )
                    if warning_message:
                        progress_tracker.set_warning(warning_message)

                    # Construir respuesta de éxito
                    success_message = (
                        f'CV "{cv.original_file.name}" subido y procesado exitosamente.'
                    )
                    if warning_message:
                        success_message += f"\n\n{warning_message}"

                    # Limpiar temporal
                    try:
                        if file_path and os.path.exists(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass

                    return JsonResponse(
                        {
                            "success": True,
                            "message": success_message,
                            "skills_count": cv.skills_count,
                            "warning_message": warning_message,
                            "logs": captured_logs,
                            "progress_id": progress_tracker.progress_id,
                        }
                    )

                except Exception as e:
                    logger.error(f"Error procesando CV: {e}")
                    logger.error(f"🔍 TIPO DE ERROR: {type(e)}")
                    logger.error(f"🔍 ERROR COMPLETO: {str(e)}")

                    # Marcar progreso como fallido
                    progress_tracker.set_error(str(e))

                    # Obtener logs capturados antes de limpiar
                    captured_logs = log_capture_instance.get_logs()
                    cleanup_log_capture()

                    # Si es un error de IA, devolver error específico
                    if "Error de IA" in str(e):
                        logger.error(
                            f"🔴 ERROR DE IA DETALLADO ENVIADO AL FRONTEND: {str(e)}"
                        )
                        # Limpiar temporal
                        try:
                            if file_path and os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception:
                            pass

                        return JsonResponse(
                            {
                                "success": False,
                                "error": str(e),
                                "error_type": "ai_error",
                                "logs": captured_logs,
                                "progress_id": progress_tracker.progress_id,
                            }
                        )
                    else:
                        logger.error(f"🔴 ERROR GENERAL ENVIADO AL FRONTEND: {str(e)}")
                        # Limpiar temporal
                        try:
                            if file_path and os.path.exists(file_path):
                                os.remove(file_path)
                        except Exception:
                            pass

                        return JsonResponse(
                            {
                                "success": False,
                                "error": f"Error procesando el archivo: {str(e)}",
                                "error_type": "processing_error",
                                "logs": captured_logs,
                                "progress_id": progress_tracker.progress_id,
                            }
                        )
            else:
                logger.warning("Formato no soportado en subida")
                try:
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                except Exception:
                    pass
                return JsonResponse(
                    {
                        "success": False,
                        "message": "CV subido, pero el formato no es soportado para parsing automático.",
                    }
                )

        except Exception as e:
            logger.error(f"Error procesando CV subido: {e}")
            return JsonResponse(
                {"success": False, "message": f"Error procesando el CV: {str(e)}"}
            )
    else:
        # Errores de validación del formulario
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"Error en {field}: {error}")

        return JsonResponse({"success": False, "message": "; ".join(error_messages)})


@login_required
def cv_list_view(request):
    """Lista de CVs del usuario."""
    user_cvs = UserCV.objects.filter(user=request.user).order_by("-created_at")

    # COMENTADO: Procesamiento automático de CVs deshabilitado para evitar problemas de memoria
    # Los CVs se procesan solo cuando se suben, no al cargar la lista
    # for cv in user_cvs:
    #     logger.info(f"CV {cv.id}: skills={cv.skills}, skills_count={cv.skills_count}")
    #     if not cv.skills or cv.skills_count == 0:
    #         try:
    #             from matching.services.cv_parser import CVParser
    #             from matching.services.skills_extractor import SkillsExtractor
    #
    #             # Parsear el CV si no está parseado
    #             if not cv.parsed_text:
    #                 parser = CVParser()
    #                 parsed_text = parser.parse_cv(cv.original_file.path)
    #                 if parsed_text:
    #                     cv.parsed_text = parsed_text
    #                     cv.save()
    #
    #             # Extraer habilidades si hay texto parseado
    #             if cv.parsed_text:
    #                 extractor = SkillsExtractor()
    #                 skills_data = extractor.extract_skills(cv.parsed_text)
    #                 cv.skills = skills_data
    #                 cv.save()
    #
    #                 # Calcular skills_count después de guardar
    #                 skills_count = len(skills_data.get("skills", []))
    #                 logger.info(
    #                     f"CV {cv.id} procesado: {skills_count} skills detectadas"
    #                 )
    #
    #         except Exception as e:
    #             logger.error(f"Error procesando CV {cv.id}: {e}")
    #             # Continuar con el siguiente CV

    # Calcular total de habilidades
    total_skills = sum(cv.skills_count for cv in user_cvs)

    context = {"user_cvs": user_cvs, "total_skills": total_skills, "title": "Mis CVs"}
    return render(request, "matching/cv_list.html", context)


@login_required
@require_http_methods(["DELETE"])
def delete_cv_view(request, cv_id):
    """Eliminar CV (AJAX)."""
    cv = get_object_or_404(UserCV, id=cv_id, user=request.user)
    cv_name = cv.original_file.name

    # Eliminar archivo físico antes de eliminar el registro
    try:
        if cv.original_file and cv.original_file.path:
            if os.path.exists(cv.original_file.path):
                os.remove(cv.original_file.path)
                logger.info(f"Archivo físico eliminado: {cv.original_file.path}")
            else:
                logger.warning(f"Archivo físico no encontrado: {cv.original_file.path}")
    except Exception as e:
        logger.error(f"Error eliminando archivo físico {cv.original_file.path}: {e}")

    # Eliminar registro de la base de datos
    cv.delete()

    # Iniciar recálculo automático en background (sin modal)
    try:
        from .tasks import recalculate_matches_for_user

        task = recalculate_matches_for_user.delay(request.user.id)
        logger.info(
            f"Recálculo automático iniciado en background después de eliminar CV para usuario {request.user.id} (task: {task.id})"
        )
    except Exception as e:
        logger.error(
            f"Error iniciando recálculo automático después de eliminar CV: {e}"
        )

    return JsonResponse(
        {
            "success": True,
            "message": f'CV "{cv_name}" eliminado correctamente.',
        }
    )


@login_required
@require_http_methods(["DELETE"])
def delete_all_cvs_view(request):
    """Eliminar todos los CVs del usuario (AJAX)."""
    try:
        # Obtener todos los CVs del usuario
        user_cvs = UserCV.objects.filter(user=request.user)
        cv_count = user_cvs.count()

        if cv_count == 0:
            return JsonResponse(
                {"success": False, "message": "No tienes CVs para eliminar"}
            )

        # Eliminar archivos físicos antes de eliminar registros
        files_deleted = 0
        for cv in user_cvs:
            try:
                if cv.original_file and cv.original_file.path:
                    if os.path.exists(cv.original_file.path):
                        os.remove(cv.original_file.path)
                        files_deleted += 1
                        logger.info(
                            f"Archivo físico eliminado: {cv.original_file.path}"
                        )
                    else:
                        logger.warning(
                            f"Archivo físico no encontrado: {cv.original_file.path}"
                        )
            except Exception as e:
                logger.error(
                    f"Error eliminando archivo físico {cv.original_file.path}: {e}"
                )

        # Eliminar todos los CVs de la base de datos
        user_cvs.delete()

        # Iniciar recálculo automático en background (sin modal)
        try:
            from .tasks import recalculate_matches_for_user

            task = recalculate_matches_for_user.delay(request.user.id)
            logger.info(
                f"Recálculo automático iniciado en background después de eliminar todos los CVs para usuario {request.user.id} (task: {task.id})"
            )
        except Exception as e:
            logger.error(
                f"Error iniciando recálculo automático después de eliminar todos los CVs: {e}"
            )

        return JsonResponse(
            {
                "success": True,
                "message": f"Todos los CVs eliminados correctamente ({cv_count} registros, {files_deleted} archivos).",
            }
        )

    except Exception as e:
        logger.error(
            f"Error eliminando todos los CVs del usuario {request.user.id}: {e}"
        )
        return JsonResponse(
            {"success": False, "message": "Error interno al eliminar los CVs"},
            status=500,
        )


@login_required
def recalculation_modal_partial_view(request):
    """Vista para servir el modal de recálculo como partial."""
    return render(request, "matching/partials/recalculation_modal.html")


@login_required
def start_recalculation_view(request):
    """Vista AJAX para iniciar recálculo manual de matches."""
    if request.method != "POST":
        return JsonResponse(
            {"success": False, "message": "Método no permitido"}, status=405
        )

    try:
        from .tasks import recalculate_matches_for_user

        # Obtener razón del recálculo
        reason = request.POST.get("reason", "manual")

        # Ejecutar recálculo en background
        task = recalculate_matches_for_user.delay(request.user.id)

        logger.info(
            f"Recálculo manual iniciado para usuario {request.user.id} (task: {task.id}, reason: {reason})"
        )

        return JsonResponse(
            {
                "success": True,
                "message": f"Recálculo iniciado ({reason})",
                "task_id": task.id,
            }
        )
    except Exception as e:
        logger.error(
            f"Error iniciando recálculo manual para usuario {request.user.id}: {e}"
        )
        return JsonResponse(
            {"success": False, "message": f"Error iniciando recálculo: {str(e)}"},
            status=500,
        )


@login_required
def matching_recalculation_status_view(request, task_id):
    """Vista AJAX para verificar el estado del recálculo de matches."""
    try:
        from celery.result import AsyncResult

        # Obtener resultado de la tarea
        task_result = AsyncResult(task_id)

        if task_result.state == "PENDING":
            response = {
                "success": True,
                "state": task_result.state,
                "status": "Esperando...",
                "progress": 0,
            }
        elif task_result.state == "PROGRESS":
            response = {
                "success": True,
                "state": task_result.state,
                "status": task_result.info.get("current_step", "Procesando..."),
                "progress_info": task_result.info.get("progress_info", ""),
                "progress": task_result.info.get("progress_percentage", 0),
            }
        elif task_result.state == "SUCCESS":
            result = task_result.result
            logger.info(
                f"Matching recalculation status - task_id: {task_id}, result: {result}"
            )
            response = {
                "success": True,
                "state": task_result.state,
                "status": "Recálculo completado",
                "progress": 100,
                "result": result,
            }
        elif task_result.state == "FAILURE":
            response = {
                "success": False,
                "state": task_result.state,
                "status": "Error en recálculo",
                "error": str(task_result.info),
            }
        else:
            response = {
                "success": False,
                "state": task_result.state,
                "status": f"Estado desconocido: {task_result.state}",
            }

        return JsonResponse(response)

    except Exception as e:
        logger.error(f"Error verificando estado de recálculo {task_id}: {e}")
        return JsonResponse(
            {"success": False, "error": f"Error verificando estado: {str(e)}"}
        )


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def test_scraper_view(request):
    """Vista para probar el scraper de dvcarreras. Solo accesible para administradores."""
    if request.method == "POST":
        try:
            profile = UserProfile.objects.get(user=request.user)

            if not profile.dv_username or not profile.dv_password:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "message": "Debes configurar las credenciales de dvcarreras primero.",
                        }
                    )
                messages.error(
                    request, "Debes configurar las credenciales de dvcarreras primero."
                )
                return redirect("profile")

            # ============================================================
            # 🔒 LOCK GLOBAL: Verificar si ya hay un scraping en curso
            # ============================================================
            from .services.scraping_lock import scraping_lock

            active_scraping = scraping_lock.get_active_scraping()
            if active_scraping:
                task_id = active_scraping.get("task_id")
                source = active_scraping.get("source", "unknown")
                started_at = active_scraping.get("started_at", "desconocido")

                message = f"Ya hay un scraping en curso (iniciado {source} a las {started_at})"

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "task_id": task_id,
                            "message": message,
                            "locked": True,
                        }
                    )
                messages.warning(request, message)
                return redirect("test_scraper")

            # Iniciar tarea de scraping con STEALTH usando rotación automática
            from django.core.cache import cache

            from .tasks_stealth import scrape_dvcarreras_jobs_stealth

            # Llamar sin user_id para usar rotación automática de credenciales
            # Pasar requesting_user_id para que los logs se guarden también para el usuario actual
            task = scrape_dvcarreras_jobs_stealth.delay(
                user_id=None, requesting_user_id=request.user.id
            )

            # Guardar task_id en cache para que todos los admins lo vean (legacy, ahora usa lock)
            cache.set("current_scraping_task_id", task.id, timeout=3600)  # 1 hora

            # Solo devolver el task_id, sin mensajes
            return JsonResponse(
                {
                    "success": True,
                    "task_id": task.id,
                }
            )

        except UserProfile.DoesNotExist:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": "No tienes perfil configurado."}
                )
            messages.error(request, "No tienes perfil configurado.")
            return redirect("profile")
        except Exception as e:
            logger.error(f"Error iniciando scraping: {e}")
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {"success": False, "message": f"Error iniciando scraping: {str(e)}"}
                )
            messages.error(request, f"Error iniciando scraping: {str(e)}")

    # Obtener estadísticas básicas
    try:
        profile = UserProfile.objects.get(user=request.user)
        has_credentials = bool(profile.dv_username and profile.dv_password)
        credentials_verified = (
            profile.is_dv_connection_verified() if has_credentials else False
        )
        credentials_in_progress = (
            profile.is_dv_connection_in_progress() if has_credentials else False
        )
    except UserProfile.DoesNotExist:
        has_credentials = False
        credentials_verified = False
        credentials_in_progress = False

    from .models import JobPosting, MatchScore

    stats = {
        "total_jobs": JobPosting.objects.count(),
        "user_matches": (
            MatchScore.objects.filter(user=request.user).count()
            if has_credentials
            else 0
        ),
        "has_credentials": has_credentials,
        "credentials_verified": credentials_verified,
        "credentials_in_progress": credentials_in_progress,
    }

    # Si es petición AJAX, devolver solo las estadísticas
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"success": True, "stats": stats})

    # Obtener información de rotación de credenciales
    from django.core.cache import cache

    verified_users = (
        UserProfile.objects.filter(
            dv_username__isnull=False,
            dv_password__isnull=False,
            dv_connection_status="verified",
        )
        .exclude(dv_username="", dv_password="")
        .select_related("user")
        .order_by("user_id")
    )

    # Calcular el próximo usuario en rotación
    next_user = None
    total_verified = verified_users.count()

    if total_verified > 0:
        last_used_id = cache.get("scraper_last_user_id")
        user_ids = [u.user_id for u in verified_users]

        if last_used_id and last_used_id in user_ids:
            # Encontrar el índice del último usuario usado
            current_index = user_ids.index(last_used_id)
            # El próximo es el siguiente en la lista (circular)
            next_index = (current_index + 1) % len(user_ids)
            next_user_profile = verified_users[next_index]
        else:
            # Si no hay último usado, el próximo es el primero
            next_user_profile = verified_users[0]

        next_user = {
            "name": next_user_profile.user.get_full_name()
            or next_user_profile.user.username,
            "email": next_user_profile.user.email,
            "dv_username": next_user_profile.dv_username,
        }

    rotation_info = {
        "total_verified": total_verified,
        "next_user": next_user,
    }

    # Obtener información del scraping programado
    from .models import ScheduledScraping

    scheduled_config = ScheduledScraping.objects.first()

    context = {
        "title": "Probar Scraper",
        "stats": stats,
        "profile": profile if has_credentials else None,
        "rotation_info": rotation_info,
        "scheduled_config": scheduled_config,
    }

    return render(request, "matching/test_scraper.html", context)


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["GET", "POST"])
def scheduled_scraping_config(request):
    """Vista para configurar el scraping programado."""
    import json

    from .models import ScheduledScraping

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            is_enabled = data.get("is_enabled", False)
            scheduled_time_str = data.get("scheduled_time")  # formato "HH:MM"

            if not scheduled_time_str:
                return JsonResponse(
                    {"success": False, "message": "Hora no proporcionada"}, status=400
                )

            # Parsear la hora
            from datetime import datetime

            scheduled_time = datetime.strptime(scheduled_time_str, "%H:%M").time()

            # Obtener o crear la configuración (solo debe haber una)
            config, created = ScheduledScraping.objects.get_or_create(
                pk=1,
                defaults={"is_enabled": is_enabled, "scheduled_time": scheduled_time},
            )

            if not created:
                config.is_enabled = is_enabled
                config.scheduled_time = scheduled_time
                config.save()

            # ============================================================
            # Actualizar el CrontabSchedule de la tarea periódica
            # ============================================================
            from django_celery_beat.models import CrontabSchedule, PeriodicTask

            # Buscar la tarea periódica existente primero
            task = PeriodicTask.objects.filter(
                task="matching.tasks_stealth.check_and_run_scheduled_scraping"
            ).first()

            # Guardar el crontab anterior para limpiarlo después si no se usa
            old_crontab = None
            if task and task.crontab:
                old_crontab = task.crontab

            # Crear o obtener el CrontabSchedule específico para esta hora
            crontab, crontab_created = CrontabSchedule.objects.get_or_create(
                minute=str(scheduled_time.minute),
                hour=str(scheduled_time.hour),
                day_of_week="*",
                day_of_month="*",
                month_of_year="*",
                timezone="America/Argentina/Buenos_Aires",
            )

            # Actualizar o crear la tarea periódica
            if task:
                task.crontab = crontab
                task.enabled = is_enabled
                task.save()
                logger.info(
                    f"✅ Tarea periódica actualizada: {task.name} - Schedule: {crontab} - Enabled: {is_enabled}"
                )
            else:
                # Si no existe, crearla
                task = PeriodicTask.objects.create(
                    name="check-scheduled-scraping",
                    crontab=crontab,
                    task="matching.tasks_stealth.check_and_run_scheduled_scraping",
                    enabled=is_enabled,
                )
                logger.info(
                    f"✅ Tarea periódica creada: {task.name} - Schedule: {crontab}"
                )

            # ============================================================
            # Limpiar el crontab anterior si no se usa más
            # ============================================================
            if old_crontab and old_crontab.id != crontab.id:
                # Verificar si el crontab anterior tiene otras tareas asociadas
                other_tasks_count = PeriodicTask.objects.filter(
                    crontab=old_crontab
                ).count()

                if other_tasks_count == 0:
                    # No hay otras tareas usando este crontab, eliminarlo
                    try:
                        old_crontab.delete()
                        logger.info(
                            f"🧹 Crontab anterior eliminado: {old_crontab} (no utilizado)"
                        )
                    except Exception as e:
                        logger.warning(
                            f"⚠️ No se pudo eliminar el crontab anterior {old_crontab}: {e}"
                        )
                else:
                    logger.debug(
                        f"ℹ️ Crontab anterior {old_crontab} aún en uso por {other_tasks_count} tarea(s)"
                    )

            # ============================================================
            # 🔄 FORZAR RECARGA: Hacer que el beat detecte el cambio inmediatamente
            # ============================================================
            try:
                from django.core.cache import cache

                # Limpiar el cache del scheduler de django-celery-beat
                # Esto fuerza al beat a recargar el schedule desde la BD
                cache_keys = [
                    "celery-beat-schedule",
                    "celery-beat-last-run",
                    f"celery-beat-task-{task.id}",
                ]
                for key in cache_keys:
                    cache.delete(key)

                # Actualizar last_run_at a NULL para forzar recalcular el próximo run
                # Esto hace que el beat recalcule inmediatamente cuándo debe ejecutarse
                task.last_run_at = None
                task.save(update_fields=["last_run_at"])

                logger.info(
                    "🔄 Cache del scheduler limpiado, beat recargará el schedule inmediatamente"
                )
            except Exception as e:
                # No fallar si la limpieza de cache falla
                logger.warning(f"⚠️ No se pudo limpiar el cache del scheduler: {e}")

            return JsonResponse(
                {
                    "success": True,
                    "message": f'Configuración guardada exitosamente. El scraping se ejecutará diariamente a las {scheduled_time.strftime("%H:%M")}.',
                    "config": {
                        "is_enabled": config.is_enabled,
                        "scheduled_time": config.scheduled_time.strftime("%H:%M"),
                        "last_run": (
                            config.last_run.isoformat() if config.last_run else None
                        ),
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error guardando configuración de scraping programado: {e}")
            return JsonResponse(
                {"success": False, "message": f"Error: {str(e)}"}, status=500
            )

    # GET: Obtener configuración actual
    try:
        config = ScheduledScraping.objects.first()
        if config:
            return JsonResponse(
                {
                    "success": True,
                    "config": {
                        "is_enabled": config.is_enabled,
                        "scheduled_time": config.scheduled_time.strftime("%H:%M"),
                        "last_run": (
                            config.last_run.isoformat() if config.last_run else None
                        ),
                    },
                }
            )
        else:
            return JsonResponse(
                {
                    "success": True,
                    "config": {
                        "is_enabled": False,
                        "scheduled_time": "09:00",
                        "last_run": None,
                    },
                }
            )
    except Exception as e:
        logger.error(f"Error obteniendo configuración de scraping programado: {e}")
        return JsonResponse(
            {"success": False, "message": f"Error: {str(e)}"}, status=500
        )


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["GET"])
def get_current_scraping_task(request):
    """Vista AJAX para obtener el task_id del scraping activo."""
    from django.core.cache import cache

    task_id = cache.get("current_scraping_task_id")

    if task_id:
        # Verificar si la tarea aún está activa
        from celery.result import AsyncResult

        result = AsyncResult(task_id)

        # Si la tarea terminó, limpiar el cache
        if result.state in ["SUCCESS", "FAILURE", "REVOKED"]:
            cache.delete("current_scraping_task_id")
            return JsonResponse(
                {"success": True, "has_active_task": False, "task_id": None}
            )

        return JsonResponse(
            {"success": True, "has_active_task": True, "task_id": task_id}
        )

    return JsonResponse({"success": True, "has_active_task": False, "task_id": None})


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["GET"])
def get_next_user_in_rotation(request):
    """Vista AJAX para obtener el próximo usuario en rotación."""
    from django.core.cache import cache

    verified_users = (
        UserProfile.objects.filter(
            dv_username__isnull=False,
            dv_password__isnull=False,
            dv_connection_status="verified",
        )
        .exclude(dv_username="", dv_password="")
        .select_related("user")
        .order_by("user_id")
    )

    total_verified = verified_users.count()

    if total_verified == 0:
        return JsonResponse({"success": True, "total_verified": 0, "next_user": None})

    last_used_id = cache.get("scraper_last_user_id")
    user_ids = [u.user_id for u in verified_users]

    if last_used_id and last_used_id in user_ids:
        current_index = user_ids.index(last_used_id)
        next_index = (current_index + 1) % len(user_ids)
        next_user_profile = verified_users[next_index]
    else:
        next_user_profile = verified_users[0]

    next_user = {
        "name": next_user_profile.user.get_full_name()
        or next_user_profile.user.username,
        "email": next_user_profile.user.email,
        "dv_username": next_user_profile.dv_username,
    }

    return JsonResponse(
        {"success": True, "total_verified": total_verified, "next_user": next_user}
    )


@login_required
@require_http_methods(["GET"])
def dv_connection_status_view(request):
    """Vista AJAX para obtener el estado de conexión DV."""
    try:
        profile = UserProfile.objects.get(user=request.user)

        return JsonResponse(
            {
                "success": True,
                "credentials_verified": profile.is_dv_connection_verified(),
                "credentials_in_progress": profile.is_dv_connection_in_progress(),
                "has_credentials": bool(profile.dv_username and profile.dv_password),
                "dv_connection_status": profile.dv_connection_status,
            }
        )
    except UserProfile.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "credentials_verified": False,
                "credentials_in_progress": False,
                "has_credentials": False,
                "dv_connection_status": "not_verified",
            }
        )


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def scraper_status_view(request, task_id):
    """Vista para obtener el estado real de una tarea de scraping (solo admins)."""
    from celery.result import AsyncResult

    try:
        # Obtener el resultado de la tarea de forma segura
        try:
            task_result = AsyncResult(task_id)
        except Exception as e:
            logger.error(f"Error creando AsyncResult para task_id={task_id}: {e}")
            return JsonResponse(
                {
                    "task_id": task_id,
                    "status": "ERROR",
                    "ready": True,
                    "successful": False,
                    "failed": True,
                    "result": {"error": f"Error obteniendo tarea: {str(e)}"},
                    "total_jobs": JobPosting.objects.count(),
                    "total_matches": MatchScore.objects.filter(
                        user=request.user
                    ).count(),
                },
                status=200,  # Retornar 200 para que el frontend pueda manejar el error
            )

        # Verificar si la tarea realmente existe
        # Si el estado es PENDING y no está en las tareas activas, probablemente no existe
        try:
            task_status = task_result.status
        except Exception as e:
            logger.warning(f"Error obteniendo status inicial: {e}")
            task_status = "UNKNOWN"

        if task_status == "PENDING":
            try:
                is_ready = task_result.ready()
            except Exception as e:
                logger.warning(f"Error verificando ready(): {e}")
                is_ready = False

            if not is_ready:
                try:
                    from celery import current_app

                    inspect = current_app.control.inspect()
                    active_tasks = inspect.active()

                    task_exists = False
                    if active_tasks:
                        for worker, tasks in active_tasks.items():
                            for task in tasks:
                                if task.get("id") == task_id:
                                    task_exists = True
                                    break
                            if task_exists:
                                break

                    if not task_exists:
                        return JsonResponse(
                            {
                                "task_id": task_id,
                                "status": "NOT_FOUND",
                                "ready": True,
                                "successful": False,
                                "failed": True,
                                "result": {"error": "Tarea no encontrada"},
                                "total_jobs": JobPosting.objects.count(),
                                "total_matches": MatchScore.objects.filter(
                                    user=request.user
                                ).count(),
                            },
                            status=200,  # Retornar 200 para que el frontend pueda manejar el error
                        )
                except Exception as inspect_error:
                    # Si falla la inspección de Celery, continuar con el estado actual
                    logger.warning(
                        f"Error inspeccionando tareas activas de Celery: {inspect_error}"
                    )
                    # Continuar con el flujo normal, no es crítico

        # Obtener estadísticas actuales
        total_jobs = JobPosting.objects.count()
        total_matches = MatchScore.objects.filter(user=request.user).count()

        # Preparar información detallada del resultado
        result_info = None
        is_ready = False
        is_successful = False
        is_failed = False

        try:
            is_ready = task_result.ready()
        except Exception as e:
            logger.warning(f"Error verificando si tarea está lista: {e}")
            is_ready = False

        if is_ready:
            try:
                is_successful = task_result.successful()
                is_failed = task_result.failed()

                if is_successful:
                    try:
                        result_info = task_result.result
                    except Exception as e:
                        logger.warning(f"Error obteniendo resultado exitoso: {e}")
                        result_info = {"message": "Tarea completada exitosamente"}
                elif is_failed:
                    # Capturar información detallada del error
                    try:
                        result_info = {
                            "error": str(task_result.result),
                            "traceback": getattr(task_result, "traceback", None),
                            "info": getattr(task_result, "info", None),
                        }
                    except Exception as e:
                        logger.warning(f"Error obteniendo detalles de error: {e}")
                        result_info = {"error": "Error desconocido en la tarea"}
            except Exception as e:
                logger.warning(f"Error verificando estado de tarea: {e}")
                # Continuar con valores por defecto
        else:
            # Si la tarea no está lista, incluir información de meta si está disponible
            try:
                meta_info = getattr(task_result, "info", {})
                if meta_info and isinstance(meta_info, dict):
                    result_info = {
                        "current_step": meta_info.get("current_step"),
                        "progress_info": meta_info.get("progress_info"),
                        "progress_percentage": meta_info.get("progress_percentage"),
                    }
            except Exception as e:
                logger.warning(f"Error obteniendo meta info: {e}")

        # Obtener estado de forma segura
        try:
            task_status = task_result.status
        except Exception as e:
            logger.warning(f"Error obteniendo status de tarea: {e}")
            task_status = "UNKNOWN"

        status_data = {
            "task_id": task_id,
            "status": task_status,
            "ready": is_ready,
            "successful": is_successful,
            "failed": is_failed,
            "result": result_info,
            "total_jobs": total_jobs,
            "total_matches": total_matches,
        }

        return JsonResponse(status_data)

    except Exception as e:
        logger.error(f"Error obteniendo estado de tarea {task_id}: {e}", exc_info=True)
        # Retornar 200 con información de error para que el frontend pueda manejarlo
        return JsonResponse(
            {
                "task_id": task_id,
                "status": "ERROR",
                "ready": True,
                "successful": False,
                "failed": True,
                "result": {"error": str(e)},
                "total_jobs": JobPosting.objects.count(),
                "total_matches": MatchScore.objects.filter(user=request.user).count(),
            },
            status=200,  # Retornar 200 para que el frontend pueda manejar el error
        )


@login_required
def process_cv_view(request, cv_id):
    """Procesa un CV específico de forma manual."""
    try:
        cv = get_object_or_404(UserCV, id=cv_id, user=request.user)

        if cv.is_processed:
            messages.info(
                request, f'El CV "{cv.original_file.name}" ya está procesado.'
            )
        else:
            # Enviar tarea de procesamiento
            from .tasks import process_cv_file

            task_result = process_cv_file.delay(cv.id)

            messages.success(
                request,
                f'Procesamiento iniciado para "{cv.original_file.name}". '
                f"Task ID: {task_result.id}",
            )

    except Exception as e:
        logger.error(f"Error procesando CV {cv_id}: {e}")
        messages.error(request, f"Error iniciando el procesamiento: {str(e)}")

    return redirect("cv_list")


@login_required
def task_status_view(request):
    """Vista para monitorear el estado de las tareas de procesamiento."""
    # Obtener CVs recientes del usuario
    user_cvs = UserCV.objects.filter(user=request.user).order_by("-created_at")[:5]

    context = {
        "title": "Estado de Tareas",
        "user_cvs": user_cvs,
    }
    return render(request, "matching/task_status.html", context)


@login_required
def scraping_results_view(request):
    """Vista para mostrar ofertas de trabajo y matches."""
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]

    # Estadísticas
    total_jobs = JobPosting.objects.count()
    total_matches = MatchScore.objects.filter(user=request.user).count()

    context = {
        "title": "Ofertas y Matches",
        "user_profile": user_profile,
        "stats": {
            "total_jobs": total_jobs,
            "total_matches": total_matches,
        },
    }
    return render(request, "matching/scraping_results.html", context)


@login_required
def paginated_matches_view(request):
    """Vista AJAX para obtener matches paginados."""
    try:
        page = int(request.GET.get("page", 1))
        per_page = 10

        # Obtener matches del usuario con información del CV
        matches_query = (
            MatchScore.objects.filter(user=request.user)
            .select_related("cv", "job_posting")
            .order_by("-created_at")
        )

        # Calcular paginación
        total_matches = matches_query.count()
        total_pages = (total_matches + per_page - 1) // per_page
        offset = (page - 1) * per_page

        matches = matches_query[offset : offset + per_page]

        # Formatear datos para el frontend
        matches_data = []
        for match in matches:
            matches_data.append(
                {
                    "id": match.id,
                    "job_id": match.job_posting.id,
                    "job_title": match.job_posting.title,
                    "job_email": match.job_posting.email,
                    "job_description": match.job_posting.description,
                    "job_created_at": match.job_posting.created_at.strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "job_external_id": match.job_posting.external_id,
                    "score": match.score,
                    "is_above_threshold": match.is_above_threshold,
                    "cv_id": match.cv.id,
                    "cv_filename": match.cv.original_file.name.split("/")[
                        -1
                    ],  # Solo el nombre del archivo
                    "created_at": match.created_at.strftime("%Y-%m-%d %H:%M"),
                }
            )

        # Obtener estadísticas adicionales
        from .models import JobPosting

        total_jobs = JobPosting.objects.count()

        return JsonResponse(
            {
                "success": True,
                "matches": matches_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_matches": total_matches,
                    "total_jobs": total_jobs,
                    "has_prev": page > 1,
                    "has_next": page < total_pages,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error en paginated_matches_view: {e}")
        return JsonResponse({"success": False, "error": "Error al cargar matches"})


@login_required
def paginated_jobs_view(request):
    """Vista AJAX para obtener ofertas paginadas."""
    try:
        page = int(request.GET.get("page", 1))
        per_page = 10

        # Obtener ofertas
        jobs_query = JobPosting.objects.all().order_by("-created_at")

        # Calcular paginación
        total_jobs = jobs_query.count()
        total_pages = (total_jobs + per_page - 1) // per_page
        offset = (page - 1) * per_page

        jobs = jobs_query[offset : offset + per_page]

        # Formatear datos para el frontend
        jobs_data = []
        for job in jobs:
            jobs_data.append(
                {
                    "id": job.id,
                    "title": job.title,
                    "email": job.email,
                    "description": job.description,
                    "created_at": job.created_at.strftime("%Y-%m-%d %H:%M"),
                    "external_id": job.external_id,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "jobs": jobs_data,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_jobs": total_jobs,
                    "has_prev": page > 1,
                    "has_next": page < total_pages,
                },
            }
        )

    except Exception as e:
        logger.error(f"Error en paginated_jobs_view: {e}")
        return JsonResponse({"success": False, "error": "Error al cargar ofertas"})


def logout_view(request):
    """Vista para cerrar sesión."""
    from django.contrib import messages
    from django.shortcuts import redirect

    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect("login")


def custom_404_view(request, exception):
    """Vista personalizada para errores 404."""
    return render(request, "404.html", status=404)


def custom_500_view(request):
    """Vista personalizada para errores 500."""
    return render(request, "500.html", status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_job_view(request, job_id):
    """Eliminar oferta de trabajo (AJAX)."""
    try:
        job = get_object_or_404(JobPosting, id=job_id)
        job_title = job.title
        job.delete()

        # Obtener estadísticas actualizadas
        total_jobs = JobPosting.objects.count()
        total_matches = MatchScore.objects.filter(user=request.user).count()

        return JsonResponse(
            {
                "success": True,
                "message": f'Oferta "{job_title}" eliminada correctamente.',
                "updated_totals": {
                    "total_jobs": total_jobs,
                    "total_matches": total_matches,
                },
                "matches_deleted": 0,  # TODO: Implementar contador de matches eliminados
            }
        )

    except Exception as e:
        logger.error(f"Error eliminando oferta {job_id}: {e}")
        return JsonResponse(
            {"success": False, "error": f"Error al eliminar la oferta: {str(e)}"}
        )


@login_required
def delete_all_jobs_view(request):
    """Eliminar todas las ofertas de trabajo."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    try:
        # Contar ofertas antes de eliminar
        jobs_count = JobPosting.objects.count()
        matches_count = MatchScore.objects.filter(user=request.user).count()

        # Eliminar todas las ofertas (esto también eliminará los matches por CASCADE)
        JobPosting.objects.all().delete()

        return JsonResponse(
            {
                "success": True,
                "message": f"{jobs_count} ofertas eliminadas correctamente.",
                "jobs_deleted": jobs_count,
                "matches_deleted": matches_count,
            }
        )

    except Exception as e:
        logger.error(f"Error eliminando todas las ofertas: {e}")
        return JsonResponse(
            {"success": False, "error": f"Error al eliminar las ofertas: {str(e)}"}
        )


def login_view(request):
    """Vista para iniciar sesión."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        # Buscar usuario por email (ya que usamos email como username)
        from django.contrib.auth.models import User

        try:
            user = User.objects.get(email=email)
            # Autenticar usando el username (que es el email)
            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"¡Bienvenido, {user.email}!")
                return redirect("dashboard")
            else:
                messages.error(request, "Email o contraseña incorrectos.")
        except User.DoesNotExist:
            messages.error(request, "Email o contraseña incorrectos.")

    return render(request, "registration/login.html")


def register_view(request):
    """Vista para registrar nuevos usuarios."""
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # Validaciones básicas
        if not email or not password1 or not password2:
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, "registration/register.html")

        # Validar dominio del email
        if not email.endswith("@davinci.edu.ar"):
            messages.error(
                request,
                "Solo se permiten cuentas con email institucional de @davinci.edu.ar",
            )
            return render(request, "registration/register.html")

        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, "registration/register.html")

        if len(password1) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres.")
            return render(request, "registration/register.html")

        # Verificar si el email ya está registrado
        from django.contrib.auth.models import User

        if User.objects.filter(email=email).exists():
            messages.error(request, "El email ya está registrado.")
            return render(request, "registration/register.html")

        try:
            # Usar email como username (Django requiere username único)
            username = email  # Usar email como username
            user = User.objects.create_user(
                username=username, email=email, password=password1
            )

            # Crear perfil de usuario
            UserProfile.objects.create(user=user)

            messages.success(
                request, "¡Cuenta creada exitosamente! Ahora puedes iniciar sesión."
            )
            return redirect("login")

        except Exception as e:
            messages.error(request, f"Error al crear la cuenta: {str(e)}")
            return render(request, "registration/register.html")

    return render(request, "registration/register.html")


@login_required
def test_smtp_email_view(request):
    """Vista para probar el envío de email SMTP."""

    # Log del request para debugging
    request_id = request.POST.get("request_id", "no-id")
    print(
        f"SMTP Test request received - ID: {request_id}, User: {request.user.username}"
    )

    try:
        user_profile = UserProfile.objects.get(user=request.user)

        # Verificar que tenga configuración SMTP
        if (
            not user_profile.smtp_host
            or not user_profile.smtp_port
            or not user_profile.smtp_username
            or not user_profile.smtp_password
        ):
            return JsonResponse(
                {
                    "success": False,
                    "message": "Configura primero host, puerto, usuario y contraseña SMTP.",
                }
            )

        # Importar librerías para envío de email
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        # Configurar el servidor SMTP
        smtp_server = user_profile.smtp_host
        smtp_port = user_profile.smtp_port
        smtp_username = user_profile.smtp_username

        # Obtener contraseña SMTP de forma segura
        try:
            smtp_password = user_profile.get_smtp_password()
            logger.info(
                f"Contraseña SMTP obtenida exitosamente para {request.user.username}"
            )
        except Exception as e:
            # Si falla la desencriptación, puede ser texto plano
            logger.warning(
                f"Error obteniendo contraseña SMTP para {request.user.username}: {e}"
            )
            # Intentar usar la contraseña tal como está (texto plano)
            smtp_password = user_profile.smtp_password
            logger.info(
                f"Usando contraseña SMTP como texto plano para {request.user.username}"
            )

        logger.info(
            f"Iniciando conexión SMTP: {smtp_server}:{smtp_port}, usuario: {smtp_username}"
        )

        # Crear el mensaje de prueba
        msg = MIMEMultipart()
        msg["From"] = smtp_username
        msg["To"] = smtp_username  # Enviar a sí mismo para prueba
        msg["Subject"] = "PostulaMatic - Email de Prueba"

        # Cuerpo del email
        body = f"""
        <html>
        <body>
            <h2>🎉 ¡Email de Prueba Exitoso!</h2>
            <p>Hola <strong>{user_profile.display_name or request.user.username}</strong>,</p>
            <p>Este es un email de prueba enviado desde <strong>PostulaMatic</strong>.</p>
            <p>Tu configuración SMTP está funcionando correctamente:</p>
            <ul>
                <li><strong>Servidor:</strong> {smtp_server}</li>
                <li><strong>Puerto:</strong> {smtp_port}</li>
                <li><strong>Usuario:</strong> {smtp_username}</li>
                <li><strong>TLS:</strong> {'Sí' if user_profile.smtp_use_tls else 'No'}</li>
                <li><strong>SSL:</strong> {'Sí' if user_profile.smtp_use_ssl else 'No'}</li>
            </ul>
            <p>¡Ya puedes recibir notificaciones de matches y postulaciones automáticas!</p>
            <hr>
            <p><small>Enviado desde PostulaMatic</small></p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, "html"))

        # Configurar conexión SMTP
        logger.info(
            f"Configurando conexión SMTP: SSL={user_profile.smtp_use_ssl}, TLS={user_profile.smtp_use_tls}"
        )

        try:
            if user_profile.smtp_use_ssl:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                logger.info("Conexión SSL establecida")
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                logger.info("Conexión SMTP establecida")
                if user_profile.smtp_use_tls:
                    server.starttls()
                    logger.info("TLS iniciado")

            # Autenticarse y enviar
            logger.info("Intentando autenticación SMTP...")
            server.login(smtp_username, smtp_password)
            logger.info("Autenticación SMTP exitosa")

            logger.info("Enviando mensaje...")
            server.send_message(msg)
            logger.info("Mensaje enviado exitosamente")

            server.quit()
            logger.info("Conexión SMTP cerrada")

        except Exception as smtp_error:
            logger.error(f"Error en conexión SMTP: {smtp_error}")
            raise

        return JsonResponse(
            {
                "success": True,
                "message": f"✅ Email de prueba enviado correctamente a {smtp_username}. Revisa tu bandeja de entrada.",
            }
        )

    except UserProfile.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Perfil de usuario no encontrado"}
        )
    except Exception as e:
        # Verificar si es un error de desencriptación
        if "Error desencriptando" in str(e) or "decrypt" in str(e).lower():
            return JsonResponse(
                {
                    "success": False,
                    "message": "❌ Error: Contraseña SMTP corrupta. Por favor, re-ingresa tu contraseña SMTP.",
                }
            )
        # Si no es error de desencriptación, re-lanzar para manejo normal
        raise
    except smtplib.SMTPAuthenticationError as e:
        error_msg = str(e)
        if "Username and Password not accepted" in error_msg or "535" in error_msg:
            message = "❌ Credenciales SMTP incorrectas. Para Gmail, usa una contraseña de aplicación en lugar de tu contraseña normal."
        else:
            message = "❌ Error de autenticación SMTP. Verifica usuario y contraseña."
        return JsonResponse({"success": False, "message": message})

    except smtplib.SMTPConnectError:
        return JsonResponse(
            {
                "success": False,
                "message": "❌ Error de conexión SMTP. Verifica servidor y puerto.",
            }
        )
    except smtplib.SMTPException as e:
        error_msg = str(e)
        if "535" in error_msg:
            return JsonResponse(
                {
                    "success": False,
                    "message": "❌ Credenciales SMTP rechazadas. Para Gmail, asegúrate de usar una contraseña de aplicación.",
                }
            )
        else:
            return JsonResponse(
                {"success": False, "message": f"❌ Error SMTP: {error_msg}"}
            )
    except Exception as e:
        logger.error(f"Error inesperado en test SMTP: {e}")
        return JsonResponse(
            {
                "success": False,
                "message": "❌ Error inesperado del servidor. Intenta nuevamente.",
            }
        )


def test_dv_login_view(request):
    """Encola verificación de login DV en Celery y devuelve task_id."""
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "message": "Usuario no autenticado"})

    try:
        user_profile = UserProfile.objects.get(user=request.user)

        # Verificar que tenga credenciales
        if not user_profile.dv_username or not user_profile.dv_password:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Configura primero usuario y contraseña de INTRANET DAVINCI.",
                }
            )

        # PROTECCIÓN: Cancelar tareas anteriores de verificación DV para este usuario
        try:
            from celery import current_app

            inspect = current_app.control.inspect()
            active_tasks = inspect.active() or {}
            reserved_tasks = inspect.reserved() or {}

            tasks_to_revoke = []

            # Buscar en tareas activas
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    if "verify_dv_login_task" in task.get("name", ""):
                        task_args = str(task.get("args", ""))
                        if str(request.user.id) in task_args:
                            tasks_to_revoke.append(task.get("id"))

            # Buscar en tareas reservadas
            for worker, tasks in reserved_tasks.items():
                for task in tasks:
                    if "verify_dv_login_task" in task.get("name", ""):
                        task_args = str(task.get("args", ""))
                        if str(request.user.id) in task_args:
                            tasks_to_revoke.append(task.get("id"))

            # Revocar tareas encontradas
            if tasks_to_revoke:
                for task_id in tasks_to_revoke:
                    current_app.control.revoke(task_id, terminate=True)
                logger.info(
                    f"🛡️ Revocadas {len(tasks_to_revoke)} tareas previas de verificación DV para usuario {request.user.id}"
                )
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron cancelar tareas previas: {e}")

        # Marcar estado en progreso inmediatamente
        user_profile.set_dv_connection_verified(None)
        user_profile.save(update_fields=["dv_connection_status"])

        # Encolar tarea Celery
        from .tasks_dv import verify_dv_login_task

        try:
            async_result = verify_dv_login_task.delay(request.user.id)
            logger.info(
                "DV verify task enqueued",
                extra={"user_id": request.user.id, "task_id": async_result.id},
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": "Verificación encolada",
                    "task_id": async_result.id,
                }
            )
        except Exception as e:
            # Revertir estado a not_verified si no se pudo encolar
            user_profile.set_dv_connection_verified(False)
            user_profile.save(update_fields=["dv_connection_status"])
            logger.error(f"No se pudo encolar verify_dv_login_task: {e}")
            return JsonResponse(
                {
                    "success": False,
                    "message": "No se pudo iniciar la verificación. Intenta nuevamente.",
                }
            )

    except UserProfile.DoesNotExist:
        return JsonResponse(
            {"success": False, "message": "Perfil de usuario no encontrado"}
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error: {str(e)}"})


@login_required
def test_dv_login_task_view(request):
    """Endpoint GET para disparar tarea DV sin CSRF (temporal)."""
    try:
        # Obtener credenciales del usuario actual
        user_profile = UserProfile.objects.get(user=request.user)

        if not user_profile.dv_username or not user_profile.dv_password:
            return JsonResponse(
                {"success": False, "message": "Credenciales DV no configuradas"}
            )

        # PROTECCIÓN: Cancelar tareas anteriores
        try:
            from celery import current_app

            inspect = current_app.control.inspect()
            active_tasks = inspect.active() or {}
            reserved_tasks = inspect.reserved() or {}

            tasks_to_revoke = []
            for worker, tasks in {**active_tasks, **reserved_tasks}.items():
                for task in tasks:
                    if "verify_dv_login_task" in task.get("name", "") and str(
                        request.user.id
                    ) in str(task.get("args", "")):
                        tasks_to_revoke.append(task.get("id"))

            if tasks_to_revoke:
                for task_id in tasks_to_revoke:
                    current_app.control.revoke(task_id, terminate=True)
                logger.info(
                    f"🛡️ Revocadas {len(tasks_to_revoke)} tareas previas para usuario {request.user.id}"
                )
        except Exception as e:
            logger.warning(f"⚠️ No se pudieron cancelar tareas previas: {e}")

        # Marcar estado en progreso inmediatamente
        user_profile.set_dv_connection_verified(None)
        user_profile.save(update_fields=["dv_connection_status"])

        # Encolar tarea Celery
        async_result = verify_dv_login_task.delay(request.user.id)

        logger.info(f"Tarea DV encolada desde GET: {async_result.id}")

        return JsonResponse(
            {
                "success": True,
                "message": "Verificación iniciada",
                "task_id": async_result.id,
            }
        )

    except Exception as e:
        logger.error(f"Error encolando tarea DV: {e}")
        return JsonResponse({"success": False, "message": str(e)})


@login_required
def dv_login_manual_view(request):
    """Vista para iniciar login manual asistido desde la web."""
    if request.method == "POST":
        try:
            user_profile = UserProfile.objects.get(user=request.user)

            if not user_profile.dv_username or not user_profile.dv_password:
                return JsonResponse(
                    {
                        "success": False,
                        "message": "Configura primero usuario y contraseña de INTRANET DAVINCI",
                    }
                )

            # PROTECCIÓN: Cancelar tareas anteriores
            try:
                from celery import current_app

                inspect = current_app.control.inspect()
                active_tasks = inspect.active() or {}
                reserved_tasks = inspect.reserved() or {}

                tasks_to_revoke = []
                for worker, tasks in {**active_tasks, **reserved_tasks}.items():
                    for task in tasks:
                        if "verify_dv_login" in task.get("name", "") and str(
                            request.user.id
                        ) in str(task.get("args", "")):
                            tasks_to_revoke.append(task.get("id"))

                if tasks_to_revoke:
                    for task_id in tasks_to_revoke:
                        current_app.control.revoke(task_id, terminate=True)
                    logger.info(
                        f"🛡️ Revocadas {len(tasks_to_revoke)} tareas previas para usuario {request.user.id}"
                    )
            except Exception as e:
                logger.warning(f"⚠️ No se pudieron cancelar tareas previas: {e}")

            # Marcar estado en progreso
            user_profile.set_dv_connection_verified(None)
            user_profile.save(update_fields=["dv_connection_status"])

            # Encolar tarea de login manual
            from .tasks_dv import verify_dv_login_manual_task

            async_result = verify_dv_login_manual_task.delay(request.user.id)

            logger.info(f"Tarea DV login manual encolada: {async_result.id}")

            return JsonResponse(
                {
                    "success": True,
                    "message": "Login manual iniciado - se abrirá un navegador",
                    "task_id": async_result.id,
                }
            )

        except Exception as e:
            logger.error(f"Error iniciando login manual DV: {e}")
            return JsonResponse(
                {"success": False, "message": f"Error iniciando login manual: {str(e)}"}
            )

    return JsonResponse({"success": False, "message": "Método no permitido"})


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def scraping_logs_view(request, task_id):
    """Vista para obtener los logs GLOBALES de un scraping específico (solo admins)."""
    try:
        from django.utils import timezone as django_timezone

        # Obtener logs del scraping SIN filtrar por usuario (global para admins)
        logs = ScrapingLog.objects.filter(task_id=task_id).order_by("timestamp")

        # Convertir a formato JSON
        logs_data = []
        for log in logs:
            # Convertir timestamp a zona horaria local (Buenos Aires)
            local_timestamp = django_timezone.localtime(log.timestamp)
            logs_data.append(
                {
                    "id": log.id,
                    "message": log.message,
                    "type": log.log_type,
                    "timestamp": local_timestamp.strftime("%H:%M:%S"),
                }
            )

        return JsonResponse({"success": True, "logs": logs_data, "task_id": task_id})

    except Exception as e:
        logger.error(f"Error obteniendo logs de tarea {task_id}: {e}")
        return JsonResponse(
            {"success": False, "error": str(e), "logs": [], "task_id": task_id}
        )


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def scraping_logs_general_view(request):
    """Vista para obtener TODOS los logs GLOBALES (solo admins)"""
    try:
        from django.utils import timezone as django_timezone

        # Obtener TODOS los logs SIN filtrar por usuario (global para admins)
        logs = ScrapingLog.objects.all().order_by("timestamp")

        logs_data = []
        for log in logs:
            # Convertir timestamp a zona horaria local (Buenos Aires)
            local_timestamp = django_timezone.localtime(log.timestamp)
            logs_data.append(
                {
                    "message": log.message,
                    "type": log.log_type,
                    "timestamp": local_timestamp.strftime("%H:%M:%S"),
                    "task_id": log.task_id,
                }
            )

        return JsonResponse({"success": True, "logs": logs_data})

    except Exception as e:
        logger.error(f"Error obteniendo logs generales: {e}")
        return JsonResponse({"success": False, "error": str(e), "logs": []})


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def latest_screenshot_view(request, task_id):
    """Vista para obtener el screenshot más reciente de una tarea (solo admins)"""
    try:
        import os
        from pathlib import Path

        # Buscar todos los screenshots posibles (PNG y JPG)
        # Usar búsqueda más amplia para asegurar que encontramos todos los archivos
        screenshots_dir = Path("media/screenshots")

        if not screenshots_dir.exists():
            logger.warning(f"Directorio de screenshots no existe: {screenshots_dir}")
            return JsonResponse(
                {"success": False, "message": "No hay screenshots disponibles"}
            )

        # Buscar todos los archivos PNG y JPG
        all_screenshots = list(screenshots_dir.glob("*.png")) + list(
            screenshots_dir.glob("*.jpg")
        )

        # Filtrar por task_id (debe estar en el nombre del archivo)
        matching_screenshots = [str(s) for s in all_screenshots if task_id in s.name]

        # Log detallado para debugging
        logger.info(
            f"Buscando screenshots para task_id={task_id}: "
            f"Total archivos={len(all_screenshots)}, "
            f"Coincidencias={len(matching_screenshots)}"
        )

        if matching_screenshots:
            # Priorizar screenshots de "tablero_cargado" (el más importante)
            tablero_screenshots = [
                s for s in matching_screenshots if "tablero_cargado" in s.name
            ]

            # Si hay screenshots de tablero_cargado, usar esos
            if tablero_screenshots:
                logger.info(
                    f"✅ Encontrados {len(tablero_screenshots)} screenshots de 'tablero_cargado': "
                    f"{[os.path.basename(s) for s in tablero_screenshots]}"
                )
                # Priorizar JPG sobre PNG para tablero_cargado
                tablero_jpg = [s for s in tablero_screenshots if s.endswith(".jpg")]
                tablero_png = [s for s in tablero_screenshots if s.endswith(".png")]

                if tablero_jpg:
                    latest_screenshot = max(tablero_jpg, key=os.path.getmtime)
                    logger.info(
                        f"✅ Usando JPG de tablero_cargado: {os.path.basename(latest_screenshot)}"
                    )
                elif tablero_png:
                    # Verificar si existe JPG correspondiente
                    latest_png = max(tablero_png, key=os.path.getmtime)
                    png_path = Path(latest_png)
                    jpg_path = png_path.with_suffix(".jpg")
                    if jpg_path.exists():
                        latest_screenshot = str(jpg_path)
                        logger.info(
                            f"✅ Encontrado JPG de tablero_cargado: {jpg_path.name}"
                        )
                    else:
                        latest_screenshot = latest_png
                        logger.info(
                            f"✅ Usando PNG de tablero_cargado: {os.path.basename(latest_screenshot)}"
                        )
                else:
                    latest_screenshot = max(tablero_screenshots, key=os.path.getmtime)
                logger.info("✅ Priorizando screenshot de tablero_cargado")
            else:
                # Si no hay tablero_cargado, usar el más reciente de todos
                # Priorizar JPG sobre PNG (después de compresión, JPG es el archivo final)
                jpg_screenshots = [
                    s for s in matching_screenshots if s.endswith(".jpg")
                ]
                png_screenshots = [
                    s for s in matching_screenshots if s.endswith(".png")
                ]

                # Si hay JPGs, usar el más reciente de esos (son los comprimidos)
                # Si no, usar el PNG más reciente
                if jpg_screenshots:
                    latest_screenshot = max(jpg_screenshots, key=os.path.getmtime)
                elif png_screenshots:
                    # Verificar si existe un JPG correspondiente para cada PNG
                    # (puede que el PNG se haya convertido a JPG pero aún no se haya eliminado)
                    latest_png = max(png_screenshots, key=os.path.getmtime)
                    png_path = Path(latest_png)
                    # Buscar JPG con el mismo nombre base
                    jpg_path = png_path.with_suffix(".jpg")
                    if jpg_path.exists():
                        # El JPG existe, usar ese en lugar del PNG
                        latest_screenshot = str(jpg_path)
                        logger.info(
                            f"✅ Encontrado JPG correspondiente para PNG: {jpg_path.name}"
                        )
                    else:
                        latest_screenshot = latest_png
                else:
                    # Fallback: usar el más reciente de todos
                    latest_screenshot = max(matching_screenshots, key=os.path.getmtime)

            screenshot_url = latest_screenshot.replace("media/", "/media/")
            screenshot_name = os.path.basename(latest_screenshot)

            logger.info(
                f"✅ Screenshot encontrado: {screenshot_name} "
                f"(modificado: {os.path.getmtime(latest_screenshot)})"
            )

            return JsonResponse(
                {
                    "success": True,
                    "screenshot_url": screenshot_url,
                    "timestamp": os.path.getmtime(latest_screenshot),
                    "filename": screenshot_name,
                }
            )
        else:
            # Log detallado de qué archivos existen para debugging
            if all_screenshots:
                sample_files = [s.name for s in all_screenshots[:5]]
                logger.warning(
                    f"No se encontraron screenshots para task_id={task_id}. "
                    f"Archivos de ejemplo en directorio: {sample_files}"
                )
            else:
                logger.warning(
                    f"No hay screenshots en el directorio para task_id={task_id}"
                )

            return JsonResponse(
                {"success": False, "message": "No hay screenshots disponibles"}
            )

    except Exception as e:
        logger.error(f"Error obteniendo screenshot: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def clear_session_view(request):
    """Vista para limpiar TODAS las sesiones guardadas del scraper (solo admins)"""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Método no permitido"})

    try:
        import glob
        import os
        from pathlib import Path

        # Buscar TODOS los archivos de sesión en el directorio
        sessions_dir = Path("media/sessions")
        session_files = glob.glob(str(sessions_dir / "user_*_stealth_session.json"))

        deleted_count = 0
        deleted_users = []

        for session_file in session_files:
            try:
                # Extraer user_id del nombre del archivo
                filename = os.path.basename(session_file)
                user_id = filename.split("_")[1]

                # Eliminar archivo
                os.remove(session_file)
                deleted_count += 1
                deleted_users.append(user_id)
                logger.info(f"✅ Sesión eliminada: {filename}")
            except Exception as e:
                logger.error(f"Error eliminando {session_file}: {e}")

        if deleted_count > 0:
            logger.info(
                f"🧹 Total de sesiones eliminadas: {deleted_count} (usuarios: {', '.join(deleted_users)})"
            )
            return JsonResponse(
                {
                    "success": True,
                    "message": f"✅ {deleted_count} sesión(es) eliminada(s) exitosamente",
                    "deleted_count": deleted_count,
                    "deleted_users": deleted_users,
                }
            )
        else:
            logger.info("ℹ️ No había sesiones guardadas para eliminar")
            return JsonResponse(
                {
                    "success": True,
                    "message": "No había sesiones guardadas",
                    "deleted_count": 0,
                }
            )

    except Exception as e:
        logger.error(f"Error limpiando sesiones: {e}")
        return JsonResponse(
            {"success": False, "message": f"Error limpiando sesión: {str(e)}"}
        )


@login_required
def add_scraping_log_view(request):
    """Vista para agregar un log al scraping actual."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            task_id = data.get("task_id")
            message = data.get("message")
            log_type = data.get("type", "info")

            if not task_id or not message:
                return JsonResponse(
                    {"success": False, "error": "task_id y message son requeridos"}
                )

            # Crear el log
            log = ScrapingLog.objects.create(
                user=request.user, task_id=task_id, message=message, log_type=log_type
            )

            return JsonResponse(
                {
                    "success": True,
                    "log_id": log.id,
                    "timestamp": log.timestamp.strftime("%H:%M:%S"),
                }
            )

        except Exception as e:
            logger.error(f"Error agregando log: {e}")
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Método no permitido"})


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def clear_scraping_logs_view(request, task_id):
    """Vista para limpiar los logs GLOBALES de un scraping específico (solo admins)."""
    try:
        # Eliminar logs del scraping SIN filtrar por usuario (global)
        deleted_count = ScrapingLog.objects.filter(task_id=task_id).delete()[0]

        return JsonResponse(
            {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"Se eliminaron {deleted_count} logs",
            }
        )

    except Exception as e:
        logger.error(f"Error limpiando logs de tarea {task_id}: {e}")
        return JsonResponse({"success": False, "error": str(e)})


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def clear_user_scraping_logs_view(request):
    """Elimina TODOS los logs de scraping GLOBALES (solo admins)."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    try:
        # Eliminar TODOS los logs SIN filtrar por usuario (global)
        deleted_count = ScrapingLog.objects.all().delete()[0]
        return JsonResponse(
            {
                "success": True,
                "deleted_logs": deleted_count,
                "message": f"Se eliminaron {deleted_count} logs globales",
            }
        )
    except Exception as e:
        logger.error(f"Error limpiando logs globales: {e}")
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def cv_parsed_text_view(request, cv_id):
    """Vista AJAX para obtener el texto parseado de un CV."""
    try:
        # Obtener el CV del usuario autenticado
        cv = get_object_or_404(UserCV, id=cv_id, user=request.user)

        # Verificar si tiene texto parseado
        if cv.parsed_text:
            return JsonResponse(
                {
                    "success": True,
                    "parsed_text": cv.parsed_text,
                    "is_processed": cv.is_processed,
                    "skills_count": cv.skills_count,
                    "skills_list": cv.skills_list,
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "parsed_text": None,
                    "is_processed": cv.is_processed,
                    "skills_count": cv.skills_count,
                    "skills_list": cv.skills_list,
                    "message": "No hay texto parseado disponible",
                }
            )

    except UserCV.DoesNotExist:
        return JsonResponse({"success": False, "error": "CV no encontrado"})
    except Exception as e:
        logger.error(f"Error obteniendo texto parseado del CV {cv_id}: {e}")
        return JsonResponse({"success": False, "error": "Error interno del servidor"})


@login_required
def download_cv_view(request, cv_id):
    """Vista para descargar un CV específico del usuario."""
    try:
        # Obtener el CV del usuario actual
        cv = get_object_or_404(UserCV, id=cv_id, user=request.user)

        # Verificar que el archivo existe
        if not cv.original_file:
            raise Http404("Archivo no encontrado")

        # Obtener la ruta del archivo
        file_path = cv.original_file.path

        # Verificar que el archivo existe físicamente
        if not os.path.exists(file_path):
            raise Http404("Archivo no encontrado en el servidor")

        # Leer el archivo
        with open(file_path, "rb") as file:
            file_content = file.read()

        # Determinar el content-type basado en la extensión del archivo
        if file_path.lower().endswith(".pdf"):
            content_type = "application/pdf"
        elif file_path.lower().endswith(".docx"):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif file_path.lower().endswith(".doc"):
            content_type = "application/msword"
        else:
            content_type = "application/octet-stream"

        # Crear respuesta HTTP con el archivo
        response = HttpResponse(file_content, content_type=content_type)

        # Configurar headers para descarga
        # Obtener el nombre original del archivo de manera más robusta
        original_filename = os.path.basename(cv.original_file.name)

        # Si no tiene extensión, intentar detectarla del content-type
        if not original_filename or "." not in original_filename:
            # Crear un nombre por defecto con extensión basada en el archivo
            if file_path.lower().endswith(".pdf"):
                original_filename = f"cv_{cv_id}.pdf"
            elif file_path.lower().endswith(".docx"):
                original_filename = f"cv_{cv_id}.docx"
            elif file_path.lower().endswith(".doc"):
                original_filename = f"cv_{cv_id}.doc"
            else:
                original_filename = f"cv_{cv_id}.pdf"  # Por defecto PDF

        # Usar quote para manejar caracteres especiales en el nombre
        from urllib.parse import quote

        safe_filename = quote(original_filename)
        response["Content-Disposition"] = (
            f"attachment; filename=\"{safe_filename}\"; filename*=UTF-8''{safe_filename}"
        )
        response["Content-Length"] = len(file_content)

        logger.info(
            f"CV descargado: {original_filename} por usuario {request.user.email}"
        )

        return response

    except UserCV.DoesNotExist:
        logger.warning(
            f"Usuario {request.user.email} intentó descargar CV inexistente: {cv_id}"
        )
        raise Http404("CV no encontrado o no tienes permisos para acceder a él")
    except Exception as e:
        logger.error(
            f"Error descargando CV {cv_id} para usuario {request.user.email}: {e}"
        )
        raise Http404("Error al descargar el archivo")


@login_required
def calculate_matches_view(request):
    """Vista para calcular matches entre CVs y ofertas de trabajo (usando Celery)."""
    logger.info(f"🧮 calculate_matches_view llamada por usuario {request.user.id}")

    if request.method != "POST":
        logger.warning(f"⚠️ Método no permitido: {request.method}")
        return JsonResponse({"success": False, "message": "Método no permitido"})

    try:
        logger.info("📦 Importando recalculate_matches_for_user...")
        from .tasks import recalculate_matches_for_user

        logger.info("✅ Tarea importada correctamente")

        # Verificar que el usuario tenga CVs
        user_cvs = UserCV.objects.filter(
            user=request.user, parsed_text__isnull=False
        ).exclude(parsed_text="")

        if not user_cvs.exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": "No tienes CVs procesados para calcular matches",
                }
            )

        # Verificar que haya ofertas de trabajo
        jobs = JobPosting.objects.all()
        if not jobs.exists():
            return JsonResponse(
                {
                    "success": False,
                    "message": "No hay ofertas de trabajo para calcular matches",
                }
            )

        # Iniciar tarea en background
        task = recalculate_matches_for_user.delay(request.user.id)

        logger.info(
            f"Cálculo de matches iniciado en background para usuario {request.user.id} (task: {task.id})"
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Cálculo de matches iniciado en background",
                "task_id": task.id,
                "jobs_to_process": jobs.count(),
                "cvs_to_process": user_cvs.count(),
            }
        )

    except Exception as e:
        logger.error(
            f"Error iniciando cálculo de matches para usuario {request.user.id}: {e}"
        )
        return JsonResponse(
            {
                "success": False,
                "message": f"Error iniciando cálculo de matches: {str(e)}",
            }
        )


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="dashboard")
def get_global_scraping_status(request):
    """
    Vista para obtener el estado del scraping GLOBAL activo (si existe).
    Todos los admins ven el mismo scraping sin importar quién lo inició.
    Limpia automáticamente locks huérfanos antes de verificar.
    """
    try:
        from .services.scraping_lock import scraping_lock

        # Verificar si hay un scraping activo globalmente
        # get_active_scraping() ya limpia locks huérfanos automáticamente
        active_scraping = scraping_lock.get_active_scraping()

        if active_scraping:
            task_id = active_scraping.get("task_id")

            # Verificar el estado real de la tarea en Celery
            from celery.result import AsyncResult

            try:
                task_result = AsyncResult(task_id)
                celery_state = task_result.state

                # Si la tarea terminó, limpiar el lock automáticamente
                finished_states = ["SUCCESS", "FAILURE", "REVOKED", "REJECTED"]

                # Verificar si la tarea realmente terminó
                if celery_state in finished_states:
                    logger.info(
                        f"🧹 Limpiando lock huérfano detectado en get_global_scraping_status: "
                        f"task={task_id}, estado={celery_state}"
                    )
                    scraping_lock.force_release_lock()
                    return JsonResponse(
                        {
                            "success": True,
                            "has_active_scraping": False,
                            "task_id": None,
                            "message": "Lock huérfano limpiado automáticamente",
                        }
                    )
                elif celery_state == "PENDING":
                    # Si está PENDING, verificar si realmente existe en workers activos
                    # Si no existe, es un lock huérfano
                    try:
                        from celery import current_app

                        inspect = current_app.control.inspect()
                        active_tasks = inspect.active()
                        task_exists = False

                        if active_tasks:
                            for worker, tasks in active_tasks.items():
                                for task in tasks:
                                    if task.get("id") == task_id:
                                        task_exists = True
                                        break
                                if task_exists:
                                    break

                        if not task_exists:
                            # Verificar también si hay logs recientes (últimos 2 minutos)
                            from datetime import timedelta

                            from django.utils import timezone

                            from matching.models import ScrapingLog

                            recent_logs = ScrapingLog.objects.filter(
                                task_id=task_id,
                                created_at__gte=timezone.now() - timedelta(minutes=2),
                            ).exists()

                            if not recent_logs:
                                # No existe en workers y no hay logs recientes = lock huérfano
                                logger.info(
                                    f"🧹 Limpiando lock huérfano PENDING: "
                                    f"task={task_id}, no existe en workers, sin logs recientes"
                                )
                                scraping_lock.force_release_lock()
                                return JsonResponse(
                                    {
                                        "success": True,
                                        "has_active_scraping": False,
                                        "task_id": None,
                                        "message": "Lock huérfano limpiado automáticamente",
                                    }
                                )
                    except Exception as inspect_error:
                        logger.warning(
                            f"Error verificando workers activos: {inspect_error}"
                        )
                        # Si no se puede verificar, ser conservador y no limpiar
                        pass

            except Exception as task_check_error:
                logger.warning(
                    f"Error verificando estado de tarea {task_id}: {task_check_error}"
                )
                # Si no se puede verificar el estado, asumir que está activo
                pass

            return JsonResponse(
                {
                    "success": True,
                    "has_active_scraping": True,
                    "task_id": task_id,
                    "user_id": active_scraping.get("user_id"),
                    "source": active_scraping.get("source"),
                    "started_at": active_scraping.get("started_at"),
                    "celery_status": celery_state,
                }
            )
        else:
            return JsonResponse(
                {
                    "success": True,
                    "has_active_scraping": False,
                    "task_id": None,
                }
            )

    except Exception as e:
        logger.error(f"Error obteniendo estado de scraping global: {e}")
        return JsonResponse(
            {
                "success": False,
                "error": str(e),
                "has_active_scraping": False,
            }
        )
