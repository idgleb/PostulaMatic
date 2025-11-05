from django.urls import path

from . import views
from . import views_email_generation
from . import views_ai_testing
from . import views_cv_personalization
from . import views_email_monitoring
from . import views_api
from . import views_ai_admin
from . import views_email_sending

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("registro/", views.register_view, name="register"),
    path("perfil/", views.profile_view, name="profile"),
    path("upload-cv-ajax/", views.upload_cv_view, name="upload_cv"),
    path("cv-progress/<str:progress_id>/", views.get_cv_progress, name="cv_progress"),
    path("cancel-cv-task/", views.cancel_cv_task, name="cancel_cv_task"),
    path("mis-cvs/", views.cv_list_view, name="cv_list"),
    path("descargar-cv/<int:cv_id>/", views.download_cv_view, name="download_cv"),
    path("eliminar-cv/<int:cv_id>/", views.delete_cv_view, name="delete_cv"),
    path("eliminar-todos-cvs/", views.delete_all_cvs_view, name="delete_all_cvs"),
    path("cv-parsed-text/<int:cv_id>/", views.cv_parsed_text_view, name="cv_parsed_text"),
    path("probar-scraper/", views.test_scraper_view, name="test_scraper"),
    path("api/current-scraping-task/", views.get_current_scraping_task, name="current_scraping_task"),
    path("api/next-user-rotation/", views.get_next_user_in_rotation, name="next_user_rotation"),
    path("api/scheduled-scraping/", views.scheduled_scraping_config, name="scheduled_scraping_config"),
    path(
        "scraper-status/<str:task_id>/",
        views.scraper_status_view,
        name="scraper_status",
    ),
    path("resultados-scraping/", views.scraping_results_view, name="scraping_results"),
    path("procesar-cv/<int:cv_id>/", views.process_cv_view, name="process_cv"),
    path("estado-tareas/", views.task_status_view, name="task_status"),
    path("test-smtp-email/", views.test_smtp_email_view, name="test_smtp_email"),
    path("test-dv-login/", views.test_dv_login_view, name="test_dv_login"),
    path("test-dv-login-task/", views.test_dv_login_task_view, name="test_dv_login_task"),
    path("dv-login-manual/", views.dv_login_manual_view, name="dv_login_manual"),
    path(
        "dv-connection-status/",
        views.dv_connection_status_view,
        name="dv_connection_status",
    ),
    path("delete-all-jobs/", views.delete_all_jobs_view, name="delete_all_jobs"),
    path(
        "scraping-logs/<str:task_id>/", views.scraping_logs_view, name="scraping_logs"
    ),
    path(
        "scraping-logs/", views.scraping_logs_general_view, name="scraping_logs_general"
    ),
    path(
        "latest-screenshot/<str:task_id>/", views.latest_screenshot_view, name="latest_screenshot"
    ),
    path(
        "clear-session/", views.clear_session_view, name="clear_session"
    ),
    path("add-scraping-log/", views.add_scraping_log_view, name="add_scraping_log"),
    path(
        "clear-scraping-logs/<str:task_id>/",
        views.clear_scraping_logs_view,
        name="clear_scraping_logs",
    ),
    path(
        "clear-my-scraping-logs/",
        views.clear_user_scraping_logs_view,
        name="clear_user_scraping_logs",
    ),
    path("paginated-jobs/", views.paginated_jobs_view, name="paginated_jobs"),
    path("paginated-matches/", views.paginated_matches_view, name="paginated_matches"),
    path("delete-job/<int:job_id>/", views.delete_job_view, name="delete_job"),
    path("logout/", views.logout_view, name="logout"),
    path("matching-recalculation-status/<str:task_id>/", views.matching_recalculation_status_view, name="matching_recalculation_status"),
    path("recalculation-modal-partial/", views.recalculation_modal_partial_view, name="recalculation_modal_partial"),
    path("start-recalculation/", views.start_recalculation_view, name="start_recalculation"),
    path("calculate-matches/", views.calculate_matches_view, name="calculate_matches"),
    
    # URLs para generación de emails
    path("email-generation-test/", views_email_generation.email_generation_test_view, name="email_generation_test"),
    path("generate-test-email/", views_email_generation.generate_test_email_view, name="generate_test_email"),
    path("email-template-preview/", views_email_generation.email_template_preview_view, name="email_template_preview"),
    path("save-email-template/", views_email_generation.save_email_template_view, name="save_email_template"),
    path("email-analytics/", views_email_generation.email_analytics_view, name="email_analytics"),
    
    # URLs para testing de IA
    path("test-ai-provider/", views_ai_testing.test_ai_provider_view, name="test_ai_provider"),
    path("ai-integration-guide/", views_ai_testing.ai_integration_guide_view, name="ai_integration_guide"),
    path("update-ai-settings/", views_ai_testing.update_ai_settings_view, name="update_ai_settings"),
    
    # URLs para personalización de CV
    path("cv-personalization-test/", views_cv_personalization.cv_personalization_test, name="cv_personalization_test"),
    path("generate-personalized-cv/", views_cv_personalization.generate_personalized_cv, name="generate_personalized_cv"),
    path("send-cv-email/", views_email_sending.send_cv_email, name="send_cv_email"),
    path("cv-personalization-analytics/", views_cv_personalization.cv_personalization_analytics, name="cv_personalization_analytics"),
    path("cv-personalization-history/", views_cv_personalization.cv_personalization_history, name="cv_personalization_history"),
    path("download-personalized-cv/<int:cv_id>/<int:job_id>/", views_cv_personalization.download_personalized_cv, name="download_personalized_cv"),
    path("cv-personalization-guide/", views_cv_personalization.cv_personalization_guide, name="cv_personalization_guide"),
    
    # URLs para monitoreo de emails
    path("email-monitoring/", views_email_monitoring.email_monitoring_dashboard, name="email_monitoring"),
    path("email-logs/", views_email_monitoring.email_logs_list, name="email_logs_list"),
    path("email-log-detail/<int:log_id>/", views_email_monitoring.email_log_detail, name="email_log_detail"),
    path("api/email-detail/<int:email_id>/", views_email_monitoring.get_email_detail, name="email_detail_api"),
    path("download-email-cv/<int:email_id>/", views_email_monitoring.download_personalized_cv, name="download_email_personalized_cv"),
    path("send-test-email/", views_email_monitoring.send_test_email, name="send_test_email"),
    path("send-bulk-emails/", views_email_monitoring.send_bulk_emails, name="send_bulk_emails"),
    path("process-auto-matching/", views_email_monitoring.process_auto_matching, name="process_auto_matching"),
    path("email-statistics/", views_email_monitoring.email_statistics, name="email_statistics"),
    path("api/email-statistics/", views_email_monitoring.email_statistics_api, name="email_statistics_api"),
    path("api/user-cvs/", views_email_monitoring.get_user_cvs_api, name="get_user_cvs_api"),
    path("task-status/<str:task_id>/", views_email_monitoring.task_status, name="task_status"),
    path("cleanup-email-logs/", views_email_monitoring.cleanup_email_logs, name="cleanup_email_logs"),
    path("email-settings/", views_email_monitoring.email_settings, name="email_settings"),
    
    # URLs para APIs
    path("api/user-cvs/", views_api.user_cvs_api, name="user_cvs_api"),
    path("api/job-postings/", views_api.job_postings_api, name="job_postings_api"),
    path("api/email-logs/", views_api.email_logs_api, name="email_logs_api"),
    # path("api/email-statistics/", views_api.email_statistics_api, name="email_statistics_api"),  # Duplicado, se usa views_email_monitoring.email_statistics_api
    
    # URLs para administración de IA (solo staff)
    path("admin/ai-config/", views_ai_admin.ai_admin_config_view, name="ai_admin_config"),
    path("admin/ai-status/", views_ai_admin.ai_admin_status_view, name="ai_admin_status"),
    path("admin/test-ai-provider/", views_ai_admin.test_ai_provider_admin, name="test_ai_provider_admin"),
    path("admin/get-available-models/", views_ai_admin.get_available_models, name="get_available_models"),
]
