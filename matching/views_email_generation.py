"""
Vistas para generación y prueba de emails personalizados.
"""

import json
import logging
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import UserCV, JobPosting, MatchScore, UserProfile
from .services.email_personalizer import email_personalization_service

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def email_generation_test_view(request):
    """Vista para probar la generación de emails personalizados."""

    # Obtener CVs del usuario
    user_cvs = UserCV.objects.filter(
        user=request.user, parsed_text__isnull=False
    ).exclude(parsed_text="")

    # Obtener puestos de trabajo recientes
    recent_jobs = JobPosting.objects.all()[:10]

    # Obtener matches del usuario
    user_matches = (
        MatchScore.objects.filter(user_cv__user=request.user)
        .select_related("job_posting", "user_cv")
        .order_by("-score")[:10]
    )

    context = {
        "user_cvs": user_cvs,
        "recent_jobs": recent_jobs,
        "user_matches": user_matches,
        "available_templates": [
            "base",
            "formal",
            "creative",
            "technical",
            "startup",
            "corporate",
        ],
        "available_providers": ["openai", "anthropic"],
    }

    return render(request, "matching/email_generation_test.html", context)


@login_required
@require_http_methods(["POST"])
def generate_test_email_view(request):
    """Vista AJAX para generar email de prueba."""

    try:
        # Obtener parámetros
        cv_id = request.POST.get("cv_id")
        job_id = request.POST.get("job_id")
        template_type = request.POST.get("template_type", "base")
        custom_instructions = request.POST.get("custom_instructions", "")
        ai_provider = request.POST.get("ai_provider", "openai")

        if not cv_id or not job_id:
            return JsonResponse(
                {"success": False, "message": "CV y puesto de trabajo son requeridos"}
            )

        # Obtener objetos
        user_cv = get_object_or_404(UserCV, id=cv_id, user=request.user)
        job_posting = get_object_or_404(JobPosting, id=job_id)

        # Buscar match score si existe
        try:
            match_score = MatchScore.objects.get(
                user_cv=user_cv, job_posting=job_posting
            )
        except MatchScore.DoesNotExist:
            match_score = None

        # Generar email personalizado
        result = email_personalization_service.generate_personalized_email(
            user=request.user,
            user_cv=user_cv,
            job_posting=job_posting,
            match_score=match_score,
            template_type=template_type,
            custom_instructions=custom_instructions,
            ai_provider=ai_provider,
        )

        if result.error:
            return JsonResponse(
                {"success": False, "message": f"Error generando email: {result.error}"}
            )

        # Preparar respuesta
        response_data = {
            "success": True,
            "email_data": {
                "subject": result.subject,
                "body": result.body,
                "provider": result.provider,
                "model": result.model,
                "tokens_used": result.tokens_used,
                "template_used": template_type,
                "cv_filename": (
                    user_cv.original_file.name.split("/")[-1]
                    if user_cv.original_file
                    else "CV"
                ),
                "job_title": job_posting.title,
                "match_score": match_score.score if match_score else 0,
            },
        }

        logger.info(
            f"Email de prueba generado para usuario {request.user.email}, "
            f"CV {cv_id}, puesto {job_id}, proveedor {result.provider}"
        )

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error en generación de email de prueba: {e}")
        return JsonResponse({"success": False, "message": f"Error interno: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def email_template_preview_view(request):
    """Vista para previsualizar templates de email."""

    template_type = request.GET.get("template_type", "base")

    # Datos de ejemplo
    sample_data = {
        "job_description": """
        Estamos buscando un Desarrollador Python con experiencia en Django.
        
        Requisitos:
        - 3+ años de experiencia en Python
        - Conocimiento en Django, PostgreSQL
        - Experiencia con APIs REST
        - Trabajo remoto disponible
        
        Ofrecemos:
        - Salario competitivo
        - Trabajo remoto
        - Capacitación continua
        """,
        "cv_skills": {
            "skills": ["Python", "Django", "PostgreSQL", "REST APIs", "JavaScript"],
            "experience_years": 4,
            "experience_summary": "Desarrollador Python",
            "education": "Universidad de Buenos Aires - Ingeniería en Sistemas",
            "projects": [
                "Sistema de gestión de inventario",
                "API REST para e-commerce",
            ],
        },
        "user_profile": {"display_name": "Juan Pérez", "email": "juan@example.com"},
    }

    context = {
        "template_type": template_type,
        "sample_data": sample_data,
        "available_templates": [
            "base",
            "formal",
            "creative",
            "technical",
            "startup",
            "corporate",
        ],
    }

    return render(request, "matching/email_template_preview.html", context)


@login_required
@require_http_methods(["POST"])
def save_email_template_view(request):
    """Vista para guardar template personalizado de email."""

    try:
        template_name = request.POST.get("template_name")
        template_content = request.POST.get("template_content")

        if not template_name or not template_content:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Nombre y contenido del template son requeridos",
                }
            )

        # Por ahora solo loguear, en el futuro se podría guardar en DB
        logger.info(
            f"Template personalizado guardado por usuario {request.user.email}: "
            f"nombre={template_name}, contenido={template_content[:100]}..."
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Template personalizado guardado correctamente",
            }
        )

    except Exception as e:
        logger.error(f"Error guardando template personalizado: {e}")
        return JsonResponse({"success": False, "message": f"Error interno: {str(e)}"})


@login_required
@require_http_methods(["GET"])
def email_analytics_view(request):
    """Vista para mostrar analytics de emails generados."""

    # Por ahora datos mock, en el futuro se obtendrían de logs/DB
    analytics_data = {
        "total_emails_generated": 0,
        "emails_by_provider": {"openai": 0, "anthropic": 0},
        "emails_by_template": {
            "base": 0,
            "formal": 0,
            "creative": 0,
            "technical": 0,
            "startup": 0,
            "corporate": 0,
        },
        "average_tokens_used": 0,
        "success_rate": 100,
    }

    context = {"analytics": analytics_data}

    return render(request, "matching/email_analytics.html", context)
