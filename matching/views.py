import json
import logging
import os

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import (
    CVUploadForm,
    DVCredentialsForm,
    MatchingConfigForm,
    SMTPConfigForm,
    DVCookiesForm,
)
from .forms_email import EmailConfigForm
from .models import JobPosting, MatchScore, ScrapingLog, UserCV, UserProfile
from .services.cv_parser import cv_parser
from .services.skills_extractor import skills_extractor

# from .tasks import scrape_dvcarreras_jobs  # Comentado para usar Playwright

logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    """Dashboard principal del usuario."""
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]

    # Estadísticas básicas
    stats = {
        "total_cvs": UserCV.objects.filter(user=request.user).count(),
        "total_matches": MatchScore.objects.filter(user=request.user).count(),
        "emails_sent_today": 0,  # TODO: Implementar contador de emails
        "emails_failed": 0,  # TODO: Implementar contador de errores
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
    cookies_form = DVCookiesForm(instance=profile)

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
        elif section == "dv_cookies":
            cookies_form = DVCookiesForm(request.POST, instance=profile)
            if cookies_form.is_valid():
                cookies_form.save()
                if is_ajax:
                    return JsonResponse({"success": True, "message": "Cookies DV guardadas (cifradas)."})
                else:
                    messages.success(request, "Cookies DV guardadas correctamente.")
            else:
                if is_ajax:
                    return JsonResponse({"success": False, "message": "Error al guardar cookies."})
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
            logger.info(f"Matching form - old_threshold (ANTES de crear formulario): {old_threshold}")
            
            matching_form = MatchingConfigForm(request.POST, instance=profile)
            logger.info(f"Matching form - POST data: {request.POST}")
            logger.info(f"Matching form - Form is_valid: {matching_form.is_valid()}")
            if matching_form.errors:
                logger.info(f"Matching form - Form errors: {matching_form.errors}")
            
            if matching_form.is_valid():
                # Leer el nuevo valor ANTES de guardar
                new_threshold = matching_form.cleaned_data['match_threshold']
                logger.info(f"Matching form - new_threshold: {new_threshold}")
                logger.info(f"Matching form - ¿Cambió umbral?: {old_threshold != new_threshold}")
                
                matching_form.save()
                
                if old_threshold != new_threshold:
                    try:
                        # Importar tarea de recálculo
                        from .tasks import recalculate_matches_for_user
                        
                        # Ejecutar recálculo en background
                        task = recalculate_matches_for_user.delay(request.user.id)
                        
                        logger.info(f"Recálculo de matches iniciado para usuario {request.user.id} (task: {task.id})")
                        
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
                                f"✅ Configuración guardada y recálculo iniciado. Umbral cambiado de {old_threshold}% a {new_threshold}%."
                            )
                    except Exception as e:
                        logger.error(f"Error iniciando recálculo para usuario {request.user.id}: {e}")
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
                                "✅ Configuración guardada. ⚠️ Error al iniciar recálculo automático."
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
                            request, "✅ Configuración de matching guardada correctamente."
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
        "cookies_form": cookies_form,
        "profile": profile,
        "title": "Mi Perfil",
    }
    return render(request, "matching/profile.html", context)


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
        cv = form.save(commit=False)
        cv.user = request.user

        # Guardar el CV primero
        cv.save()

        # Procesar el archivo inmediatamente si es posible
        try:
            file_path = cv.original_file.path

            # Verificar que el formato es soportado
            if cv_parser.is_supported(file_path):
                logger.info(f"Procesando CV inmediatamente: {cv.original_file.name}")

                # Extraer texto del archivo
                parse_result = cv_parser.parse_cv(file_path)
                parsed_text = parse_result["text"]

                # Procesar todos los archivos sin validación previa
                skills_data = skills_extractor.extract_skills(parsed_text)

                # Guardar resultados
                cv.parsed_text = parsed_text
                cv.skills = skills_data
                cv.save()

                logger.info(f"CV procesado: {cv.skills_count} skills detectadas")

                # Iniciar recálculo automático en background (sin modal)
                try:
                    from .tasks import recalculate_matches_for_user
                    task = recalculate_matches_for_user.delay(request.user.id)
                    logger.info(f"Recálculo automático iniciado en background después de subir CV para usuario {request.user.id} (task: {task.id})")
                except Exception as e:
                    logger.error(f"Error iniciando recálculo automático después de subir CV: {e}")
                
                return JsonResponse(
                    {
                        "success": True,
                        "message": f'CV "{cv.original_file.name}" subido y procesado exitosamente.',
                        "skills_count": cv.skills_count,
                    }
                )
            else:
                logger.warning(f"Formato no soportado: {cv.original_file.name}")
                return JsonResponse(
                    {
                        "success": False,
                        "message": f'CV "{cv.original_file.name}" subido, pero el formato no es soportado para parsing automático.',
                    }
                )

        except Exception as e:
            logger.error(f"Error procesando CV {cv.original_file.name}: {e}")
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

    # Calcular habilidades para cada CV si no están calculadas
    for cv in user_cvs:
        logger.info(f"CV {cv.id}: skills={cv.skills}, skills_count={cv.skills_count}")
        if not cv.skills or cv.skills_count == 0:
            try:
                from matching.services.cv_parser import CVParser
                from matching.services.skills_extractor import SkillsExtractor

                # Parsear el CV si no está parseado
                if not cv.parsed_text:
                    parser = CVParser()
                    parsed_text = parser.parse_cv(cv.original_file.path)
                    if parsed_text:
                        cv.parsed_text = parsed_text
                        cv.save()

                # Extraer habilidades si hay texto parseado
                if cv.parsed_text:
                    extractor = SkillsExtractor()
                    skills_data = extractor.extract_skills(cv.parsed_text)
                    cv.skills = skills_data
                    cv.save()

                    # Calcular skills_count después de guardar
                    skills_count = len(skills_data.get("skills", []))
                    logger.info(
                        f"CV {cv.id} procesado: {skills_count} skills detectadas"
                    )

            except Exception as e:
                logger.error(f"Error procesando CV {cv.id}: {e}")
                # Continuar con el siguiente CV

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
        logger.info(f"Recálculo automático iniciado en background después de eliminar CV para usuario {request.user.id} (task: {task.id})")
    except Exception as e:
        logger.error(f"Error iniciando recálculo automático después de eliminar CV: {e}")

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
            return JsonResponse({
                "success": False, 
                "message": "No tienes CVs para eliminar"
            })
        
        # Eliminar archivos físicos antes de eliminar registros
        files_deleted = 0
        for cv in user_cvs:
            try:
                if cv.original_file and cv.original_file.path:
                    if os.path.exists(cv.original_file.path):
                        os.remove(cv.original_file.path)
                        files_deleted += 1
                        logger.info(f"Archivo físico eliminado: {cv.original_file.path}")
                    else:
                        logger.warning(f"Archivo físico no encontrado: {cv.original_file.path}")
            except Exception as e:
                logger.error(f"Error eliminando archivo físico {cv.original_file.path}: {e}")
        
        # Eliminar todos los CVs de la base de datos
        user_cvs.delete()
        
        # Iniciar recálculo automático en background (sin modal)
        try:
            from .tasks import recalculate_matches_for_user
            task = recalculate_matches_for_user.delay(request.user.id)
            logger.info(f"Recálculo automático iniciado en background después de eliminar todos los CVs para usuario {request.user.id} (task: {task.id})")
        except Exception as e:
            logger.error(f"Error iniciando recálculo automático después de eliminar todos los CVs: {e}")
        
        return JsonResponse({
            "success": True,
            "message": f"Todos los CVs eliminados correctamente ({cv_count} registros, {files_deleted} archivos).",
        })
        
    except Exception as e:
        logger.error(f"Error eliminando todos los CVs del usuario {request.user.id}: {e}")
        return JsonResponse({
            "success": False, 
            "message": "Error interno al eliminar los CVs"
        }, status=500)




@login_required
def recalculation_modal_partial_view(request):
    """Vista para servir el modal de recálculo como partial."""
    return render(request, "matching/partials/recalculation_modal.html")


@login_required
def start_recalculation_view(request):
    """Vista AJAX para iniciar recálculo manual de matches."""
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "Método no permitido"}, status=405)
    
    try:
        from .tasks import recalculate_matches_for_user
        
        # Obtener razón del recálculo
        reason = request.POST.get('reason', 'manual')
        
        # Ejecutar recálculo en background
        task = recalculate_matches_for_user.delay(request.user.id)
        
        logger.info(f"Recálculo manual iniciado para usuario {request.user.id} (task: {task.id}, reason: {reason})")
        
        return JsonResponse({
            "success": True,
            "message": f"Recálculo iniciado ({reason})",
            "task_id": task.id,
        })
    except Exception as e:
        logger.error(f"Error iniciando recálculo manual para usuario {request.user.id}: {e}")
        return JsonResponse({
            "success": False,
            "message": f"Error iniciando recálculo: {str(e)}"
        }, status=500)


@login_required
def matching_recalculation_status_view(request, task_id):
    """Vista AJAX para verificar el estado del recálculo de matches."""
    try:
        from celery.result import AsyncResult
        
        # Obtener resultado de la tarea
        task_result = AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {
                'success': True,
                'state': task_result.state,
                'status': 'Esperando...',
                'progress': 0
            }
        elif task_result.state == 'PROGRESS':
            response = {
                'success': True,
                'state': task_result.state,
                'status': task_result.info.get('current_step', 'Procesando...'),
                'progress_info': task_result.info.get('progress_info', ''),
                'progress': task_result.info.get('progress_percentage', 0)
            }
        elif task_result.state == 'SUCCESS':
            result = task_result.result
            logger.info(f"Matching recalculation status - task_id: {task_id}, result: {result}")
            response = {
                'success': True,
                'state': task_result.state,
                'status': 'Recálculo completado',
                'progress': 100,
                'result': result
            }
        elif task_result.state == 'FAILURE':
            response = {
                'success': False,
                'state': task_result.state,
                'status': 'Error en recálculo',
                'error': str(task_result.info)
            }
        else:
            response = {
                'success': False,
                'state': task_result.state,
                'status': f'Estado desconocido: {task_result.state}'
            }
            
        return JsonResponse(response)
        
    except Exception as e:
        logger.error(f"Error verificando estado de recálculo {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error verificando estado: {str(e)}'
        })


@login_required
def test_scraper_view(request):
    """Vista para probar el scraper de dvcarreras."""
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

            # Antes de lanzar, verificar si ya hay una tarea activa para este usuario
            try:
                from celery import current_app

                inspect = current_app.control.inspect()
                active_tasks = inspect.active() or {}
                existing_task_id = None
                for worker, tasks in active_tasks.items():
                    for t in tasks:
                        if t.get("name", "").endswith(
                            "scrape_dvcarreras_jobs_playwright"
                        ):
                            args = t.get("args") or ""
                            # args suele ser string como "(user_id,)" o lista
                            if str(request.user.id) in str(args):
                                existing_task_id = t.get("id")
                                break
                    if existing_task_id:
                        break
                if existing_task_id:
                    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                        return JsonResponse(
                            {
                                "success": True,
                                "task_id": existing_task_id,
                                "message": f"Ya hay un scraping activo. Reutilizando Task ID: {existing_task_id}",
                            }
                        )
                    messages.info(
                        request,
                        f"Ya hay un scraping activo. Task ID: {existing_task_id}",
                    )
                    return redirect("test_scraper")
            except Exception:
                # Si falla la inspección, continuamos y lanzamos la tarea
                pass

            # Iniciar tarea de scraping con PLAYWRIGHT
            from .tasks import scrape_dvcarreras_jobs_playwright

            task = scrape_dvcarreras_jobs_playwright.delay(request.user.id)

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "task_id": task.id,
                        "message": f"Scraping con PLAYWRIGHT iniciado (navegador real). Task ID: {task.id}",
                    }
                )

            messages.success(
                request,
                f"Scraping con PLAYWRIGHT iniciado (navegador real). Task ID: {task.id}",
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

    context = {
        "title": "Probar Scraper",
        "stats": stats,
        "profile": profile if has_credentials else None,
    }

    return render(request, "matching/test_scraper.html", context)


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
def scraper_status_view(request, task_id):
    """Vista para obtener el estado real de una tarea de scraping."""
    from celery.result import AsyncResult

    try:
        # Obtener el resultado de la tarea
        task_result = AsyncResult(task_id)

        # Verificar si la tarea realmente existe
        # Si el estado es PENDING y no está en las tareas activas, probablemente no existe
        if task_result.status == "PENDING" and not task_result.ready():
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
                    }
                )

        # Obtener estadísticas actuales
        total_jobs = JobPosting.objects.count()
        total_matches = MatchScore.objects.filter(user=request.user).count()

        # Preparar información detallada del resultado
        result_info = None
        if task_result.ready():
            if task_result.successful():
                result_info = task_result.result
            elif task_result.failed():
                # Capturar información detallada del error
                try:
                    result_info = {
                        "error": str(task_result.result),
                        "traceback": getattr(task_result, "traceback", None),
                        "info": getattr(task_result, "info", None),
                    }
                except Exception as e:
                    result_info = {"error": f"Error desconocido en la tarea: {str(e)}"}
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

        status_data = {
            "task_id": task_id,
            "status": task_result.status,
            "ready": task_result.ready(),
            "successful": task_result.successful() if task_result.ready() else False,
            "failed": task_result.failed() if task_result.ready() else False,
            "result": result_info,
            "total_jobs": total_jobs,
            "total_matches": total_matches,
        }

        return JsonResponse(status_data)

    except Exception as e:
        logger.error(f"Error obteniendo estado de tarea {task_id}: {e}")
        return JsonResponse({"error": str(e)}, status=500)


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
    """Vista para mostrar los resultados del scraping."""
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]

    # Estadísticas
    total_jobs = JobPosting.objects.count()
    total_matches = MatchScore.objects.filter(user=request.user).count()

    context = {
        "title": "Resultados del Scraping",
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
    from django.contrib.auth import logout
    from django.shortcuts import redirect
    from django.contrib import messages
    
    logout(request)
    messages.success(request, "Has cerrado sesión correctamente.")
    return redirect('login')


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
                username=username,
                email=email,
                password=password1
            )
            
            # Crear perfil de usuario
            UserProfile.objects.create(user=user)
            
            messages.success(request, "¡Cuenta creada exitosamente! Ahora puedes iniciar sesión.")
            return redirect("login")
            
        except Exception as e:
            messages.error(request, f"Error al crear la cuenta: {str(e)}")
            return render(request, "registration/register.html")

    return render(request, "registration/register.html")


@login_required
def test_smtp_email_view(request):
    """Vista para probar el envío de email SMTP."""
    
    # Log del request para debugging
    request_id = request.POST.get('request_id', 'no-id')
    print(f"SMTP Test request received - ID: {request_id}, User: {request.user.username}")

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
            logger.info(f"Contraseña SMTP obtenida exitosamente para {request.user.username}")
        except Exception as e:
            # Si falla la desencriptación, puede ser texto plano
            logger.warning(f"Error obteniendo contraseña SMTP para {request.user.username}: {e}")
            # Intentar usar la contraseña tal como está (texto plano)
            smtp_password = user_profile.smtp_password
            logger.info(f"Usando contraseña SMTP como texto plano para {request.user.username}")
        
        logger.info(f"Iniciando conexión SMTP: {smtp_server}:{smtp_port}, usuario: {smtp_username}")

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
        logger.info(f"Configurando conexión SMTP: SSL={user_profile.smtp_use_ssl}, TLS={user_profile.smtp_use_tls}")
        
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
        
    except smtplib.SMTPConnectError as e:
        return JsonResponse(
            {
                "success": False,
                "message": "❌ Error de conexión SMTP. Verifica servidor y puerto.",
            }
        )
    except smtplib.SMTPException as e:
        error_msg = str(e)
        if "535" in error_msg:
            return JsonResponse({"success": False, "message": "❌ Credenciales SMTP rechazadas. Para Gmail, asegúrate de usar una contraseña de aplicación."})
        else:
            return JsonResponse({"success": False, "message": f"❌ Error SMTP: {error_msg}"})
    except Exception as e:
        logger.error(f"Error inesperado en test SMTP: {e}")
        return JsonResponse(
            {"success": False, "message": "❌ Error inesperado del servidor. Intenta nuevamente."}
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
def scraping_logs_view(request, task_id):
    """Vista para obtener los logs de un scraping específico."""
    try:
        # Obtener logs del scraping
        logs = ScrapingLog.objects.filter(user=request.user, task_id=task_id).order_by(
            "timestamp"
        )

        # Convertir a formato JSON
        logs_data = []
        for log in logs:
            logs_data.append(
                {
                    "id": log.id,
                    "message": log.message,
                    "type": log.log_type,
                    "timestamp": log.timestamp.strftime("%H:%M:%S"),
                }
            )

        return JsonResponse({"success": True, "logs": logs_data, "task_id": task_id})

    except Exception as e:
        logger.error(f"Error obteniendo logs de tarea {task_id}: {e}")
        return JsonResponse(
            {"success": False, "error": str(e), "logs": [], "task_id": task_id}
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
def clear_scraping_logs_view(request, task_id):
    """Vista para limpiar los logs de un scraping específico."""
    try:
        # Eliminar logs del scraping
        deleted_count = ScrapingLog.objects.filter(
            user=request.user, task_id=task_id
        ).delete()[0]

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
def clear_user_scraping_logs_view(request):
    """Elimina todos los logs de scraping del usuario autenticado."""
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    try:
        deleted_count = ScrapingLog.objects.filter(user=request.user).delete()[0]
        return JsonResponse(
            {
                "success": True,
                "deleted_logs": deleted_count,
                "message": f"Se eliminaron {deleted_count} logs del usuario",
            }
        )
    except Exception as e:
        logger.error(f"Error limpiando logs del usuario {request.user.id}: {e}")
        return JsonResponse({"success": False, "error": str(e)})


@login_required
def cv_parsed_text_view(request, cv_id):
    """Vista AJAX para obtener el texto parseado de un CV."""
    try:
        # Obtener el CV del usuario autenticado
        cv = get_object_or_404(UserCV, id=cv_id, user=request.user)
        
        # Verificar si tiene texto parseado
        if cv.parsed_text:
            return JsonResponse({
                "success": True,
                "parsed_text": cv.parsed_text,
                "is_processed": cv.is_processed,
                "skills_count": cv.skills_count,
                "skills_list": cv.skills_list
            })
        else:
            return JsonResponse({
                "success": False,
                "parsed_text": None,
                "is_processed": cv.is_processed,
                "skills_count": cv.skills_count,
                "skills_list": cv.skills_list,
                "message": "No hay texto parseado disponible"
            })
            
    except UserCV.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "CV no encontrado"
        })
    except Exception as e:
        logger.error(f"Error obteniendo texto parseado del CV {cv_id}: {e}")
        return JsonResponse({
            "success": False,
            "error": "Error interno del servidor"
        })


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
        with open(file_path, 'rb') as file:
            file_content = file.read()
        
        # Determinar el content-type basado en la extensión del archivo
        if file_path.lower().endswith('.pdf'):
            content_type = 'application/pdf'
        elif file_path.lower().endswith('.docx'):
            content_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        elif file_path.lower().endswith('.doc'):
            content_type = 'application/msword'
        else:
            content_type = 'application/octet-stream'
        
        # Crear respuesta HTTP con el archivo
        response = HttpResponse(file_content, content_type=content_type)
        
        # Configurar headers para descarga
        # Obtener el nombre original del archivo de manera más robusta
        original_filename = os.path.basename(cv.original_file.name)
        
        # Si no tiene extensión, intentar detectarla del content-type
        if not original_filename or '.' not in original_filename:
            # Crear un nombre por defecto con extensión basada en el archivo
            if file_path.lower().endswith('.pdf'):
                original_filename = f"cv_{cv_id}.pdf"
            elif file_path.lower().endswith('.docx'):
                original_filename = f"cv_{cv_id}.docx"
            elif file_path.lower().endswith('.doc'):
                original_filename = f"cv_{cv_id}.doc"
            else:
                original_filename = f"cv_{cv_id}.pdf"  # Por defecto PDF
        
        # Usar quote para manejar caracteres especiales en el nombre
        from urllib.parse import quote
        safe_filename = quote(original_filename)
        response['Content-Disposition'] = f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{safe_filename}'
        response['Content-Length'] = len(file_content)
        
        logger.info(f"CV descargado: {original_filename} por usuario {request.user.email}")
        
        return response
        
    except UserCV.DoesNotExist:
        logger.warning(f"Usuario {request.user.email} intentó descargar CV inexistente: {cv_id}")
        raise Http404("CV no encontrado o no tienes permisos para acceder a él")
    except Exception as e:
        logger.error(f"Error descargando CV {cv_id} para usuario {request.user.email}: {e}")
        raise Http404("Error al descargar el archivo")
