"""
APIs para el sistema de monitoreo de emails.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .models import UserCV, JobPosting


@login_required
@require_http_methods(["GET"])
def user_cvs_api(request):
    """API para obtener CVs del usuario."""

    cvs = UserCV.objects.filter(user=request.user).order_by("-created_at")

    cvs_data = []
    for cv in cvs:
        cvs_data.append(
            {
                "id": cv.id,
                "created_at": cv.created_at.strftime("%d/%m/%Y %H:%M"),
                "skills_count": cv.skills_count,
                "is_processed": cv.is_processed,
                "file_name": (
                    cv.original_file.name.split("/")[-1]
                    if cv.original_file
                    else "Sin archivo"
                ),
            }
        )

    return JsonResponse({"success": True, "cvs": cvs_data})


@login_required
@require_http_methods(["GET"])
def job_postings_api(request):
    """API para obtener puestos de trabajo disponibles."""

    jobs = JobPosting.objects.all().order_by("-created_at")[
        :100
    ]  # Limitar a 100 más recientes

    jobs_data = []
    for job in jobs:
        jobs_data.append(
            {
                "id": job.id,
                "title": job.title,
                "email": job.email,
                "created_at": job.created_at.strftime("%d/%m/%Y"),
                "description_preview": (
                    job.description[:200] + "..."
                    if len(job.description) > 200
                    else job.description
                ),
            }
        )

    return JsonResponse({"success": True, "jobs": jobs_data})


@login_required
@require_http_methods(["GET"])
def email_logs_api(request):
    """API para obtener logs de emails con filtros."""

    from .models import EmailSentLog

    # Parámetros de filtro
    status = request.GET.get("status", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    page = int(request.GET.get("page", 1))
    per_page = int(request.GET.get("per_page", 20))

    # Query base
    logs_query = EmailSentLog.objects.filter(user=request.user)

    # Aplicar filtros
    if status:
        logs_query = logs_query.filter(status=status)

    if date_from:
        try:
            from datetime import datetime

            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            logs_query = logs_query.filter(sent_at__date__gte=date_from_obj)
        except ValueError:
            pass

    if date_to:
        try:
            from datetime import datetime

            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            logs_query = logs_query.filter(sent_at__date__lte=date_to_obj)
        except ValueError:
            pass

    # Paginación
    total_count = logs_query.count()
    start = (page - 1) * per_page
    end = start + per_page

    logs = logs_query.select_related("job_posting", "cv")[start:end]

    logs_data = []
    for log in logs:
        logs_data.append(
            {
                "id": log.id,
                "job_title": log.job_posting.title,
                "job_email": log.job_posting.email,
                "email_subject": log.email_subject,
                "status": log.status,
                "status_display": log.get_status_display(),
                "sent_at": log.sent_at.strftime("%d/%m/%Y %H:%M"),
                "email_template": log.email_template,
                "ai_provider": log.ai_provider,
                "error_message": log.error_message,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "logs": logs_data,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": (total_count + per_page - 1) // per_page,
            },
        }
    )


@login_required
@require_http_methods(["GET"])
def email_statistics_api(request):
    """API para obtener estadísticas de emails."""

    from .models import EmailSentLog
    from django.db.models import Count, Q
    from datetime import datetime, timedelta
    from django.utils import timezone

    # Estadísticas generales
    total_emails = EmailSentLog.objects.filter(user=request.user).count()
    successful_emails = EmailSentLog.objects.filter(
        user=request.user, status="sent"
    ).count()
    failed_emails = EmailSentLog.objects.filter(
        user=request.user, status="failed"
    ).count()

    success_rate = (successful_emails / total_emails * 100) if total_emails > 0 else 0

    # Estadísticas por día (últimos 30 días)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)

    daily_stats = (
        EmailSentLog.objects.filter(
            user=request.user, sent_at__date__gte=thirty_days_ago
        )
        .extra(select={"day": "date(sent_at)"})
        .values("day")
        .annotate(
            sent=Count("id", filter=Q(status="sent")),
            failed=Count("id", filter=Q(status="failed")),
            total=Count("id"),
        )
        .order_by("day")
    )

    daily_data = []
    for stat in daily_stats:
        daily_data.append(
            {
                "date": stat["day"].strftime("%Y-%m-%d"),
                "sent": stat["sent"],
                "failed": stat["failed"],
                "total": stat["total"],
            }
        )

    # Estadísticas por template
    template_stats = (
        EmailSentLog.objects.filter(user=request.user)
        .values("email_template")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    template_data = []
    for stat in template_stats:
        template_data.append(
            {"template": stat["email_template"], "count": stat["count"]}
        )

    # Estadísticas por proveedor de IA
    ai_provider_stats = (
        EmailSentLog.objects.filter(user=request.user)
        .values("ai_provider")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    ai_provider_data = []
    for stat in ai_provider_stats:
        ai_provider_data.append(
            {"provider": stat["ai_provider"], "count": stat["count"]}
        )

    return JsonResponse(
        {
            "success": True,
            "statistics": {
                "total_emails": total_emails,
                "successful_emails": successful_emails,
                "failed_emails": failed_emails,
                "success_rate": round(success_rate, 1),
                "daily_stats": daily_data,
                "template_stats": template_data,
                "ai_provider_stats": ai_provider_data,
            },
        }
    )
