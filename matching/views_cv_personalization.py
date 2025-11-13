"""
Vistas para personalización de CV.
"""

import json
import logging
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from matching.models import JobPosting, UserCV

from .services.cv_personalizer import cv_personalization_service

logger = logging.getLogger(__name__)


@login_required
def cv_personalization_test(request):
    """Vista para probar la personalización de CV."""

    # Obtener CVs del usuario
    user_cvs = UserCV.objects.filter(user=request.user).order_by("-created_at")

    # Obtener puestos de trabajo disponibles
    job_postings = JobPosting.objects.all().order_by("-created_at")[:50]

    context = {
        "user_cvs": user_cvs,
        "job_postings": job_postings,
        "page_title": "Personalización de CV - Test",
    }

    return render(request, "matching/cv_personalization_test.html", context)


@login_required
@require_http_methods(["POST"])
def generate_personalized_cv(request):
    """Genera CV personalizado para un puesto específico."""

    try:
        logger.info(
            f"🔍 Iniciando personalización de CV - Usuario: {request.user.username}"
        )
        data = json.loads(request.body)
        cv_id = data.get("cv_id")
        job_id = data.get("job_id")

        logger.info(f"📋 CV ID: {cv_id}, Job ID: {job_id}")

        if not cv_id or not job_id:
            logger.warning("❌ Faltan CV ID o Job ID")
            return JsonResponse(
                {"success": False, "error": "CV ID y Job ID son requeridos"}
            )

        # Obtener CV y puesto
        logger.info(f"📄 Buscando CV {cv_id} y Job {job_id}...")
        user_cv = get_object_or_404(UserCV, id=cv_id, user=request.user)
        job_posting = get_object_or_404(JobPosting, id=job_id)

        logger.info(
            f"✅ CV encontrado: {user_cv.original_file.name if user_cv.original_file else 'Sin archivo'}"
        )
        logger.info(f"✅ Job encontrado: {job_posting.title}")

        # Generar perfil de usuario básico
        user_profile = {
            "name": f"{request.user.first_name} {request.user.last_name}".strip()
            or request.user.username,
            "email": request.user.email,
            "experience_summary": f"Usuario con {len(user_cv.skills_list)} habilidades",
        }

        logger.info(f"🤖 Generando CV personalizado con IA...")

        # Personalizar CV usando el servicio de IA
        result = cv_personalization_service.personalize_cv_for_job(
            user_cv=user_cv, job_posting=job_posting, user_profile=user_profile
        )

        if result["success"]:
            logger.info(
                f"✅ CV personalizado generado exitosamente - Score: {result['match_score']}%"
            )
            response_data = {
                "success": True,
                "personalized_cv": result["personalized_cv"],
                "job_requirements": result["job_requirements"],
                "cv_data": result["cv_data"],
                "match_score": result["match_score"],
                "user_cv_skills": (
                    user_cv.skills_list if hasattr(user_cv, "skills_list") else []
                ),
                "message": f'CV personalizado generado exitosamente. Score: {result["match_score"]}%',
                "process_logs": result.get("process_logs", []),
                # NUEVO: Scores de comparación
                "original_score": result.get("original_score", 0),
                "improvement": result.get("improvement", 0),
                # NUEVO: Análisis ATS detallado
                "ats_analysis": {
                    "score_breakdown": result.get("match_score_breakdown", {}),
                    "missing_keywords": result.get("missing_keywords", []),
                    "job_keywords": result.get("job_keywords", []),
                    "suggestions": [
                        f"✅ {len(result['personalized_cv'].get('skills', []))} habilidades incluidas",
                        f"{'✅' if result['match_score'] >= 70 else '⚠️'} Match score: {result['match_score']}%",
                        f"{'✅' if len(result.get('missing_keywords', [])) == 0 else '⚠️'} Keywords faltantes: {len(result.get('missing_keywords', []))}",
                    ],
                },
            }
            logger.info(f"📤 Enviando respuesta exitosa al cliente")
            return JsonResponse(response_data)
        else:
            # Mostrar error explícito de la IA
            error_message = result.get("error", "Error desconocido al personalizar CV")
            logger.error(f"❌ Error de IA: {error_message}")
            return JsonResponse(
                {
                    "success": False,
                    "error": f"Error de IA: {error_message}",
                    "ai_error": True,
                    "details": "La inteligencia artificial no pudo generar el CV personalizado. Verifica la configuración de API keys y modelos.",
                }
            )

    except Exception as e:
        logger.error(f"❌ EXCEPCIÓN generando CV personalizado: {e}", exc_info=True)
        return JsonResponse({"success": False, "error": f"Error interno: {str(e)}"})


@login_required
def cv_personalization_analytics(request):
    """Vista de analytics de personalización de CV."""

    # Obtener estadísticas básicas
    user_cvs = UserCV.objects.filter(user=request.user)

    # Estadísticas por CV
    cv_stats = []
    for cv in user_cvs:
        # Contar matches para este CV
        from matching.models import MatchScore

        matches = MatchScore.objects.filter(cv=cv)

        cv_stat = {
            "cv_id": cv.id,
            "filename": (
                cv.original_file.name.split("/")[-1] if cv.original_file else "CV"
            ),
            "skills_count": len(cv.skills_list),
            "matches_count": matches.count(),
            "avg_match_score": matches.aggregate(avg_score=models.Avg("score"))[
                "avg_score"
            ]
            or 0,
            "created_at": cv.created_at,
        }
        cv_stats.append(cv_stat)

    # Estadísticas generales
    total_cvs = user_cvs.count()
    total_matches = sum(stat["matches_count"] for stat in cv_stats)
    avg_skills_per_cv = (
        sum(stat["skills_count"] for stat in cv_stats) / total_cvs
        if total_cvs > 0
        else 0
    )

    context = {
        "cv_stats": cv_stats,
        "total_cvs": total_cvs,
        "total_matches": total_matches,
        "avg_skills_per_cv": round(avg_skills_per_cv, 1),
        "page_title": "Analytics de Personalización de CV",
    }

    return render(request, "matching/cv_personalization_analytics.html", context)


@login_required
def cv_personalization_history(request):
    """Historial de personalizaciones de CV."""

    # Por ahora, mostrar CVs del usuario
    # En el futuro se puede implementar un historial de personalizaciones
    user_cvs = UserCV.objects.filter(user=request.user).order_by("-created_at")

    # Paginación
    paginator = Paginator(user_cvs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {"page_obj": page_obj, "page_title": "Historial de Personalización de CV"}

    return render(request, "matching/cv_personalization_history.html", context)


@login_required
def download_personalized_cv(request, cv_id, job_id):
    """Descarga CV personalizado para un puesto específico."""

    try:
        user_cv = get_object_or_404(UserCV, id=cv_id, user=request.user)
        job_posting = get_object_or_404(JobPosting, id=job_id)

        # Generar CV personalizado
        user_profile = {
            "name": f"{request.user.first_name} {request.user.last_name}".strip()
            or request.user.username,
            "email": request.user.email,
        }

        result = cv_personalization_service.personalize_cv_for_job(
            user_cv=user_cv, job_posting=job_posting, user_profile=user_profile
        )

        if result["success"] and result["personalized_file"]:
            # Por ahora, devolver el archivo original
            # En el futuro se puede devolver el archivo personalizado
            file_path = result["personalized_file"]

            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    response = HttpResponse(f.read(), content_type="application/pdf")
                    filename = (
                        f"CV_personalizado_{job_posting.title.replace(' ', '_')}.pdf"
                    )
                    response["Content-Disposition"] = (
                        f'attachment; filename="{filename}"'
                    )
                    return response

        messages.error(request, "No se pudo generar el CV personalizado")
        return redirect("cv_personalization_test")

    except Exception as e:
        logger.error(f"Error descargando CV personalizado: {e}")
        messages.error(request, f"Error: {str(e)}")
        return redirect("cv_personalization_test")


@login_required
def cv_personalization_guide(request):
    """Guía de personalización de CV."""

    context = {
        "page_title": "Guía de Personalización de CV",
        "tips": [
            "El sistema analiza automáticamente los requisitos del puesto",
            "Destaca las habilidades más relevantes para cada posición",
            "Adapta el resumen profesional según el nivel requerido",
            "Prioriza proyectos y experiencia relacionada",
            "Calcula un score de coincidencia para cada postulación",
        ],
    }

    return render(request, "matching/cv_personalization_guide.html", context)
