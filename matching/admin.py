from django.contrib import admin

from .models import (ApplicationAttempt, JobPosting, MatchScore, UserCV,
                     UserProfile)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "display_name",
        "match_threshold",
        "daily_limit",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["user__username", "user__email", "display_name"]
    fieldsets = (
        ("Usuario", {"fields": ("user", "display_name")}),
        (
            "Configuración SMTP",
            {
                "fields": (
                    "smtp_host",
                    "smtp_port",
                    "smtp_use_tls",
                    "smtp_use_ssl",
                    "smtp_username",
                    "smtp_password",
                ),
                "description": "Configuración del servidor SMTP para envío de emails",
            },
        ),
        (
            "Credenciales dvcarreras",
            {
                "fields": ("dv_username", "dv_password"),
                "description": "Credenciales para login en dvcarreras.davinci.edu.ar",
            },
        ),
        (
            "Configuración de Matching",
            {
                "fields": (
                    "match_threshold",
                    "daily_limit",
                    "min_pause_seconds",
                    "max_pause_seconds",
                ),
                "description": "Umbral de coincidencia y límites de envío",
            },
        ),
        ("Control", {"fields": ("is_active",)}),
    )


@admin.register(UserCV)
class UserCVAdmin(admin.ModelAdmin):
    list_display = ["user", "created_at", "skills_count"]
    list_filter = ["created_at"]
    search_fields = ["user__username", "parsed_text"]
    readonly_fields = ["created_at"]

    def skills_count(self, obj):
        return len(obj.skills_list) if obj.skills_list else 0

    skills_count.short_description = "Número de Skills"


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ["title", "email", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["title", "description", "email"]
    readonly_fields = ["created_at", "updated_at", "external_id"]


@admin.register(MatchScore)
class MatchScoreAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "job_posting_title",
        "score",
        "is_above_threshold",
        "created_at",
    ]
    list_filter = ["score", "created_at", "user"]
    search_fields = ["user__username", "job_posting__title", "job_posting__email"]
    readonly_fields = ["created_at"]

    def job_posting_title(self, obj):
        return obj.job_posting.title

    job_posting_title.short_description = "Oferta"

    def is_above_threshold(self, obj):
        return obj.is_above_threshold

    is_above_threshold.short_description = "Supera Umbral"
    is_above_threshold.boolean = True


@admin.register(ApplicationAttempt)
class ApplicationAttemptAdmin(admin.ModelAdmin):
    list_display = ["user", "job_posting_title", "smtp_status", "created_at", "sent_at"]
    list_filter = ["smtp_status", "created_at", "sent_at"]
    search_fields = ["user__username", "job_posting__title", "smtp_from"]
    readonly_fields = ["created_at"]

    def job_posting_title(self, obj):
        return obj.job_posting.title

    job_posting_title.short_description = "Oferta"
