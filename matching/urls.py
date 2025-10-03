from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('perfil/', views.profile_view, name='profile'),
    path('upload-cv-ajax/', views.upload_cv_view, name='upload_cv'),
    path('mis-cvs/', views.cv_list_view, name='cv_list'),
    path('eliminar-cv/<int:cv_id>/', views.delete_cv_view, name='delete_cv'),
    path('probar-scraper/', views.test_scraper_view, name='test_scraper'),
    path('scraper-status/<str:task_id>/', views.scraper_status_view, name='scraper_status'),
    path('resultados-scraping/', views.scraping_results_view, name='scraping_results'),
    path('procesar-cv/<int:cv_id>/', views.process_cv_view, name='process_cv'),
    path('estado-tareas/', views.task_status_view, name='task_status'),
    path('test-smtp-email/', views.test_smtp_email_view, name='test_smtp_email'),
    path('test-dv-login/', views.test_dv_login_view, name='test_dv_login'),
    path('dv-connection-status/', views.dv_connection_status_view, name='dv_connection_status'),
    path('delete-all-jobs/', views.delete_all_jobs_view, name='delete_all_jobs'),
    path('scraping-logs/<str:task_id>/', views.scraping_logs_view, name='scraping_logs'),
    path('add-scraping-log/', views.add_scraping_log_view, name='add_scraping_log'),
    path('clear-scraping-logs/<str:task_id>/', views.clear_scraping_logs_view, name='clear_scraping_logs'),
    path('clear-my-scraping-logs/', views.clear_user_scraping_logs_view, name='clear_user_scraping_logs'),
    path('paginated-jobs/', views.paginated_jobs_view, name='paginated_jobs'),
    path('paginated-matches/', views.paginated_matches_view, name='paginated_matches'),
    path('delete-job/<int:job_id>/', views.delete_job_view, name='delete_job'),
    path('logout/', views.logout_view, name='logout'),
]
