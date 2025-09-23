from django.urls import path
from . import views

urlpatterns = [
  path('', views.home, name='home'),
  path('enviar-cv-automaticamente', views.home, name='enviar_cv'),
  path('postularse-automaticamente', views.home, name='postularse_auto'),
  path('bot-para-postular', views.home, name='bot_postular'),
  path('privacidad', views.privacidad, name='privacidad'),
  path('terminos', views.terminos, name='terminos'),
  path('gracias', views.gracias, name='gracias'),
]


