from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout, authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
import logging
import json
from .models import UserProfile, UserCV, JobPosting, MatchScore, ScrapingLog
from .forms import UserProfileForm, CVUploadForm, SMTPConfigForm, DVCredentialsForm, MatchingConfigForm
from .forms_email import EmailConfigForm
from .services.cv_parser import cv_parser, CVParserError
from .services.skills_extractor import skills_extractor, SkillsExtractorError
from .services.matching import matching_service
# from .tasks import scrape_dvcarreras_jobs  # Comentado para usar Playwright

logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    """Dashboard principal del usuario."""
    user_profile = UserProfile.objects.get_or_create(user=request.user)[0]
    
    # Estadísticas básicas
    stats = {
        'total_cvs': UserCV.objects.filter(user=request.user).count(),
        'total_matches': MatchScore.objects.filter(user=request.user).count(),
        'emails_sent_today': 0,  # TODO: Implementar contador de emails
        'emails_failed': 0,  # TODO: Implementar contador de errores
    }
    
    # Obtener ofertas recientes y matches para mostrar en el dashboard
    recent_jobs = JobPosting.objects.all().order_by('-created_at')[:5]
    recent_matches = MatchScore.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    context = {
        'title': 'Dashboard',
        'profile': user_profile,
        'stats': stats,
        'recent_jobs': recent_jobs,
        'recent_matches': recent_matches,
    }
    return render(request, 'matching/dashboard.html', context)


@login_required
def profile_view(request):
    """Vista para editar perfil de usuario."""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # Crear formularios separados
    smtp_form = SMTPConfigForm(instance=profile)
    dv_form = DVCredentialsForm(instance=profile)
    matching_form = MatchingConfigForm(instance=profile)
    email_form = EmailConfigForm(instance=profile)
    
    if request.method == 'POST':
        section = request.POST.get('section')
        
        # Verificar si es petición AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if section == 'smtp':
            smtp_form = SMTPConfigForm(request.POST, instance=profile)
            if smtp_form.is_valid():
                smtp_form.save()
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Configuración SMTP y nombre para mostrar guardados correctamente. Los emails se enviarán desde tu cuenta configurada.'
                    })
                else:
                    messages.success(request, 'Configuración SMTP y nombre para mostrar guardados correctamente.')
            else:
                if is_ajax:
                    # Obtener errores específicos del formulario
                    errors = []
                    for field, field_errors in smtp_form.errors.items():
                        for error in field_errors:
                            errors.append(f"{field}: {error}")
                    
                    return JsonResponse({
                        'success': False,
                        'message': f'❌ Error en la configuración SMTP: {"; ".join(errors)}'
                    })
        elif section == 'dv':
            dv_form = DVCredentialsForm(request.POST, instance=profile)
            if dv_form.is_valid():
                dv_form.save()
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Credenciales INTRANET DAVINCI guardadas correctamente. El sistema podrá acceder a las ofertas de trabajo.'
                    })
                else:
                    messages.success(request, 'Credenciales INTRANET DAVINCI guardadas correctamente.')
            else:
                if is_ajax:
                    # Obtener errores específicos del formulario
                    errors = []
                    for field, field_errors in dv_form.errors.items():
                        for error in field_errors:
                            errors.append(f"{field}: {error}")
                    
                    return JsonResponse({
                        'success': False,
                        'message': f'❌ Error en las credenciales INTRANET DAVINCI: {"; ".join(errors)}'
                    })
        elif section == 'matching':
            matching_form = MatchingConfigForm(request.POST, instance=profile)
            if matching_form.is_valid():
                matching_form.save()
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Configuración de matching guardada correctamente.'
                    })
                else:
                    messages.success(request, 'Configuración de matching guardada correctamente.')
            else:
                if is_ajax:
                    # Obtener errores específicos del formulario
                    errors = []
                    for field, field_errors in matching_form.errors.items():
                        for error in field_errors:
                            errors.append(f"{field}: {error}")
                    
                    return JsonResponse({
                        'success': False,
                        'message': f'❌ Error en la configuración de matching: {"; ".join(errors)}'
                    })
        elif section == 'email':
            email_form = EmailConfigForm(request.POST, instance=profile)
            if email_form.is_valid():
                email_form.save()
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Configuración de envíos de emails guardada correctamente.'
                    })
                else:
                    messages.success(request, 'Configuración de envíos de emails guardada correctamente.')
            else:
                if is_ajax:
                    # Obtener errores específicos del formulario
                    errors = []
                    for field, field_errors in email_form.errors.items():
                        for error in field_errors:
                            errors.append(f"{field}: {error}")
                    
                    return JsonResponse({
                        'success': False,
                        'message': f'❌ Error en la configuración de envíos: {"; ".join(errors)}'
                    })
    
    context = {
        'smtp_form': smtp_form,
        'dv_form': dv_form,
        'matching_form': matching_form,
        'email_form': email_form,
        'profile': profile,
        'title': 'Mi Perfil'
    }
    return render(request, 'matching/profile.html', context)


@login_required
def upload_cv_view(request):
    """Vista para subir CV con parsing automático."""
    if request.method == 'POST':
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
                    
                    # Procesar el CV inmediatamente
                    
                    # Extraer texto del archivo
                    parse_result = cv_parser.parse_cv(file_path)
                    parsed_text = parse_result['text']
                    
                    # Detectar habilidades
                    skills_data = skills_extractor.extract_skills(parsed_text)
                    
                    # Guardar resultados
                    cv.parsed_text = parsed_text
                    cv.skills = skills_data
                    cv.save()
                    
                    logger.info(f"CV procesado inmediatamente: {cv.skills_count} skills detectadas")
                    messages.success(
                        request, 
                        f'CV "{cv.original_file.name}" subido y procesado correctamente. '
                        f'Habilidades detectadas: {cv.skills_count}'
                    )
                else:
                    logger.warning(f"Formato no soportado: {cv.original_file.name}")
                    messages.warning(
                        request, 
                        f'CV "{cv.original_file.name}" subido, pero el formato no es soportado para parsing automático.'
                    )
                
            except Exception as e:
                logger.error(f"Error procesando CV {cv.original_file.name}: {e}")
                messages.error(
                    request, 
                    f'Error procesando el CV: {str(e)}'
                )
            return redirect('cv_list')
    else:
        form = CVUploadForm()
    
    # Lista de CVs del usuario
    user_cvs = UserCV.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'form': form,
        'user_cvs': user_cvs,
        'title': 'Subir CV',
        'supported_formats': cv_parser.get_supported_formats()
    }
    return render(request, 'matching/upload_cv.html', context)


@login_required
def cv_list_view(request):
    """Lista de CVs del usuario."""
    user_cvs = UserCV.objects.filter(user=request.user).order_by('-created_at')
    
    # Calcular habilidades para cada CV si no están calculadas
    for cv in user_cvs:
        logger.info(f"CV {cv.id}: skills={cv.skills}, skills_count={cv.skills_count}")
        if not cv.skills or cv.skills_count == 0:
            try:
                from matching.services.skills_extractor import SkillsExtractor
                from matching.services.cv_parser import CVParser
                
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
                    skills_count = len(skills_data.get('skills', []))
                    logger.info(f"CV {cv.id} procesado: {skills_count} skills detectadas")
                    
            except Exception as e:
                logger.error(f"Error procesando CV {cv.id}: {e}")
                # Continuar con el siguiente CV
    
    # Calcular total de habilidades
    total_skills = sum(cv.skills_count for cv in user_cvs)
    
    context = {
        'user_cvs': user_cvs,
        'total_skills': total_skills,
        'title': 'Mis CVs'
    }
    return render(request, 'matching/cv_list.html', context)


@login_required
@require_http_methods(["DELETE"])
def delete_cv_view(request, cv_id):
    """Eliminar CV (AJAX)."""
    cv = get_object_or_404(UserCV, id=cv_id, user=request.user)
    cv_name = cv.original_file.name
    cv.delete()
    
    return JsonResponse({
        'success': True,
        'message': f'CV "{cv_name}" eliminado correctamente.'
    })


@login_required
def dashboard_view(request):
    """Dashboard principal con estadísticas."""
    # Estadísticas básicas
    user_cvs = UserCV.objects.filter(user=request.user).count()
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # TODO: En pasos posteriores agregar:
    # - Total de matches
    # - Emails enviados hoy
    # - Emails enviados totales
    # - Emails fallidos
    
    context = {
        'title': 'Dashboard',
        'user_cvs': user_cvs,
        'profile': profile,
        'stats': {
            'total_cvs': user_cvs,
            'total_matches': 0,  # TODO: implementar
            'emails_sent_today': 0,  # TODO: implementar
            'emails_sent_total': 0,  # TODO: implementar
            'emails_failed': 0,  # TODO: implementar
        }
    }
    return render(request, 'matching/dashboard.html', context)


@login_required
def test_scraper_view(request):
    """Vista para probar el scraper de dvcarreras."""
    if request.method == 'POST':
        try:
            profile = UserProfile.objects.get(user=request.user)
            
            if not profile.dv_username or not profile.dv_password:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Debes configurar las credenciales de dvcarreras primero.'
                    })
                messages.error(request, 'Debes configurar las credenciales de dvcarreras primero.')
                return redirect('profile')
            
            # Antes de lanzar, verificar si ya hay una tarea activa para este usuario
            try:
                from celery import current_app
                inspect = current_app.control.inspect()
                active_tasks = inspect.active() or {}
                existing_task_id = None
                for worker, tasks in active_tasks.items():
                    for t in tasks:
                        if t.get('name', '').endswith('scrape_dvcarreras_jobs_playwright'):
                            args = t.get('args') or ''
                            # args suele ser string como "(user_id,)" o lista
                            if str(request.user.id) in str(args):
                                existing_task_id = t.get('id')
                                break
                    if existing_task_id:
                        break
                if existing_task_id:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': True,
                            'task_id': existing_task_id,
                            'message': f'Ya hay un scraping activo. Reutilizando Task ID: {existing_task_id}'
                        })
                    messages.info(request, f'Ya hay un scraping activo. Task ID: {existing_task_id}')
                    return redirect('test_scraper')
            except Exception:
                # Si falla la inspección, continuamos y lanzamos la tarea
                pass

            # Iniciar tarea de scraping con PLAYWRIGHT
            from .tasks import scrape_dvcarreras_jobs_playwright
            task = scrape_dvcarreras_jobs_playwright.delay(request.user.id)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'task_id': task.id,
                    'message': f'Scraping con PLAYWRIGHT iniciado (navegador real). Task ID: {task.id}'
                })
            
            messages.success(request, f'Scraping con PLAYWRIGHT iniciado (navegador real). Task ID: {task.id}')
            
        except UserProfile.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'No tienes perfil configurado.'
                })
            messages.error(request, 'No tienes perfil configurado.')
            return redirect('profile')
        except Exception as e:
            logger.error(f"Error iniciando scraping: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': f'Error iniciando scraping: {str(e)}'
                })
            messages.error(request, f'Error iniciando scraping: {str(e)}')
    
    # Obtener estadísticas básicas
    try:
        profile = UserProfile.objects.get(user=request.user)
        has_credentials = bool(profile.dv_username and profile.dv_password)
    except UserProfile.DoesNotExist:
        has_credentials = False
    
    from .models import JobPosting, MatchScore
    
    stats = {
        'total_jobs': JobPosting.objects.count(),
        'user_matches': MatchScore.objects.filter(user=request.user).count() if has_credentials else 0,
        'has_credentials': has_credentials,
    }
    
    context = {
        'title': 'Probar Scraper',
        'stats': stats,
        'profile': profile if has_credentials else None
    }
    
    return render(request, 'matching/test_scraper.html', context)


@login_required
def scraper_status_view(request, task_id):
    """Vista para obtener el estado real de una tarea de scraping."""
    from celery.result import AsyncResult
    
    try:
        # Obtener el resultado de la tarea
        task_result = AsyncResult(task_id)
        
        # Verificar si la tarea realmente existe
        # Si el estado es PENDING y no está en las tareas activas, probablemente no existe
        if task_result.status == 'PENDING' and not task_result.ready():
            from celery import current_app
            inspect = current_app.control.inspect()
            active_tasks = inspect.active()
            
            task_exists = False
            if active_tasks:
                for worker, tasks in active_tasks.items():
                    for task in tasks:
                        if task.get('id') == task_id:
                            task_exists = True
                            break
                    if task_exists:
                        break
            
            if not task_exists:
                return JsonResponse({
                    'task_id': task_id,
                    'status': 'NOT_FOUND',
                    'ready': True,
                    'successful': False,
                    'failed': True,
                    'result': {'error': 'Tarea no encontrada'},
                    'total_jobs': JobPosting.objects.count(),
                    'total_matches': MatchScore.objects.filter(user=request.user).count(),
                })
        
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
                        'error': str(task_result.result),
                        'traceback': getattr(task_result, 'traceback', None),
                        'info': getattr(task_result, 'info', None)
                    }
                except:
                    result_info = {'error': 'Error desconocido en la tarea'}
        else:
            # Si la tarea no está lista, incluir información de meta si está disponible
            try:
                meta_info = getattr(task_result, 'info', {})
                if meta_info and isinstance(meta_info, dict):
                    result_info = {
                        'current_step': meta_info.get('current_step'),
                        'progress_info': meta_info.get('progress_info'),
                        'progress_percentage': meta_info.get('progress_percentage')
                    }
            except:
                pass
        
        status_data = {
            'task_id': task_id,
            'status': task_result.status,
            'ready': task_result.ready(),
            'successful': task_result.successful() if task_result.ready() else False,
            'failed': task_result.failed() if task_result.ready() else False,
            'result': result_info,
            'total_jobs': total_jobs,
            'total_matches': total_matches,
        }
        
        return JsonResponse(status_data)
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de tarea {task_id}: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def process_cv_view(request, cv_id):
    """Procesa un CV específico de forma manual."""
    try:
        cv = get_object_or_404(UserCV, id=cv_id, user=request.user)
        
        if cv.is_processed:
            messages.info(request, f'El CV "{cv.original_file.name}" ya está procesado.')
        else:
            # Enviar tarea de procesamiento
            from .tasks import process_cv_file
            task_result = process_cv_file.delay(cv.id)
            
            messages.success(
                request, 
                f'Procesamiento iniciado para "{cv.original_file.name}". '
                f'Task ID: {task_result.id}'
            )
            
    except Exception as e:
        logger.error(f"Error procesando CV {cv_id}: {e}")
        messages.error(request, f'Error iniciando el procesamiento: {str(e)}')
    
    return redirect('cv_list')


@login_required
def task_status_view(request):
    """Vista para monitorear el estado de las tareas de procesamiento."""
    # Obtener CVs recientes del usuario
    user_cvs = UserCV.objects.filter(user=request.user).order_by('-created_at')[:5]
    
    context = {
        'title': 'Estado de Tareas',
        'user_cvs': user_cvs,
    }
    return render(request, 'matching/task_status.html', context)


@login_required
def scraping_results_view(request):
    """Vista para mostrar los resultados del scraping."""
    # Obtener ofertas recientes
    recent_jobs = JobPosting.objects.all().order_by('-created_at')[:20]
    
    # Obtener matches del usuario
    user_matches = MatchScore.objects.filter(user=request.user).order_by('-created_at')[:10]
    
    # Estadísticas
    total_jobs = JobPosting.objects.count()
    total_matches = MatchScore.objects.filter(user=request.user).count()
    above_threshold_matches = MatchScore.objects.filter(
        user=request.user, 
        score__gte=request.user.profile.match_threshold
    ).count()
    
    context = {
        'title': 'Resultados del Scraping',
        'recent_jobs': recent_jobs,
        'user_matches': user_matches,
        'stats': {
            'total_jobs': total_jobs,
            'total_matches': total_matches,
            'above_threshold_matches': above_threshold_matches,
        }
    }
    return render(request, 'matching/scraping_results.html', context)


def logout_view(request):
    """Vista para cerrar sesión."""
    logout(request)
    return redirect('http://localhost:8000/matching/login/')


def login_view(request):
    """Vista para iniciar sesión."""
    if request.user.is_authenticated:
        return redirect('http://localhost:8000/matching/')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'¡Bienvenido, {user.username}!')
            return redirect('http://localhost:8000/matching/')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')
    
    return render(request, 'matching/login.html')


def test_smtp_email_view(request):
    """Vista para probar el envío de email SMTP."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Usuario no autenticado'})
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Verificar que tenga configuración SMTP
        if not user_profile.smtp_host or not user_profile.smtp_port or not user_profile.smtp_username or not user_profile.smtp_password:
            return JsonResponse({
                'success': False, 
                'message': 'Configura primero host, puerto, usuario y contraseña SMTP.'
            })
        
        # Importar librerías para envío de email
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # Configurar el servidor SMTP
        smtp_server = user_profile.smtp_host
        smtp_port = user_profile.smtp_port
        smtp_username = user_profile.smtp_username
        smtp_password = user_profile.smtp_password
        
        # Crear el mensaje de prueba
        msg = MIMEMultipart()
        msg['From'] = smtp_username
        msg['To'] = smtp_username  # Enviar a sí mismo para prueba
        msg['Subject'] = "PostulaMatic - Email de Prueba"
        
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
        
        msg.attach(MIMEText(body, 'html'))
        
        # Configurar conexión SMTP
        if user_profile.smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            if user_profile.smtp_use_tls:
                server.starttls()
        
        # Autenticarse y enviar
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        
        return JsonResponse({
            'success': True,
            'message': f'✅ Email de prueba enviado correctamente a {smtp_username}. Revisa tu bandeja de entrada.'
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Perfil de usuario no encontrado'})
    except smtplib.SMTPAuthenticationError:
        return JsonResponse({'success': False, 'message': '❌ Error de autenticación SMTP. Verifica usuario y contraseña.'})
    except smtplib.SMTPConnectError:
        return JsonResponse({'success': False, 'message': '❌ Error de conexión SMTP. Verifica servidor y puerto.'})
    except smtplib.SMTPException as e:
        return JsonResponse({'success': False, 'message': f'❌ Error SMTP: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'❌ Error inesperado: {str(e)}'})


def test_dv_login_view(request):
    """Vista para probar el login en INTRANET DAVINCI."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Usuario no autenticado'})
    
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Verificar que tenga credenciales
        if not user_profile.dv_username or not user_profile.dv_password:
            return JsonResponse({
                'success': False, 
                'message': 'Configura primero usuario y contraseña de INTRANET DAVINCI.'
            })
        
        # Importar el cliente Playwright
        from matching.clients.dvcarreras_playwright_simple import DVCarrerasPlaywrightSimple
        
        # Crear instancia del cliente
        client = DVCarrerasPlaywrightSimple(
            username=user_profile.dv_username,
            password=user_profile.dv_password
        )
        
        # Probar login real
        try:
            # Intentar login
            success = client.test_login()
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': f'✅ Conexión a INTRANET DAVINCI verificada correctamente (Playwright). Usuario: {user_profile.dv_username}'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': '❌ Error de autenticación en INTRANET DAVINCI. Verifica usuario y contraseña.'
                })
                
        except Exception as login_error:
            return JsonResponse({
                'success': False,
                'message': f'❌ Error de conexión: {str(login_error)}'
            })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Perfil de usuario no encontrado'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


def delete_all_jobs_view(request):
    """Vista para eliminar todas las ofertas de trabajo."""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Usuario no autenticado'})
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        # Eliminar todas las ofertas de trabajo (MatchScore se borra por CASCADE)
        deleted_jobs = JobPosting.objects.all().delete()[0]

        # Eliminar todos los logs de scraping
        from .models import ScrapingLog
        deleted_logs = ScrapingLog.objects.all().delete()[0]
        
        return JsonResponse({
            'success': True,
            'message': f'Se eliminaron {deleted_jobs} ofertas y {deleted_logs} logs de scraping.',
            'deleted_jobs': deleted_jobs,
            'deleted_logs': deleted_logs,
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


@login_required
def scraping_logs_view(request, task_id):
    """Vista para obtener los logs de un scraping específico."""
    try:
        # Obtener logs del scraping
        logs = ScrapingLog.objects.filter(
            user=request.user,
            task_id=task_id
        ).order_by('timestamp')
        
        # Convertir a formato JSON
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'message': log.message,
                'type': log.log_type,
                'timestamp': log.timestamp.strftime('%H:%M:%S')
            })
        
        return JsonResponse({
            'success': True,
            'logs': logs_data,
            'task_id': task_id
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo logs de tarea {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'logs': [],
            'task_id': task_id
        })


@login_required
def add_scraping_log_view(request):
    """Vista para agregar un log al scraping actual."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            message = data.get('message')
            log_type = data.get('type', 'info')
            
            if not task_id or not message:
                return JsonResponse({
                    'success': False,
                    'error': 'task_id y message son requeridos'
                })
            
            # Crear el log
            log = ScrapingLog.objects.create(
                user=request.user,
                task_id=task_id,
                message=message,
                log_type=log_type
            )
            
            return JsonResponse({
                'success': True,
                'log_id': log.id,
                'timestamp': log.timestamp.strftime('%H:%M:%S')
            })
            
        except Exception as e:
            logger.error(f"Error agregando log: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    })


@login_required
def clear_scraping_logs_view(request, task_id):
    """Vista para limpiar los logs de un scraping específico."""
    try:
        # Eliminar logs del scraping
        deleted_count = ScrapingLog.objects.filter(
            user=request.user,
            task_id=task_id
        ).delete()[0]
        
        return JsonResponse({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Se eliminaron {deleted_count} logs'
        })
        
    except Exception as e:
        logger.error(f"Error limpiando logs de tarea {task_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def clear_user_scraping_logs_view(request):
    """Elimina todos los logs de scraping del usuario autenticado."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})

    try:
        deleted_count = ScrapingLog.objects.filter(user=request.user).delete()[0]
        return JsonResponse({
            'success': True,
            'deleted_logs': deleted_count,
            'message': f'Se eliminaron {deleted_count} logs del usuario'
        })
    except Exception as e:
        logger.error(f"Error limpiando logs del usuario {request.user.id}: {e}")
        return JsonResponse({'success': False, 'error': str(e)})
