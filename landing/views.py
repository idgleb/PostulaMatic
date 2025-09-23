from django.shortcuts import render, redirect
from .forms import LeadForm
from .models import Lead


BASE_SEO = {
  'title':'PostulaMatic — Enviar CV automáticamente por habilidades (IA)',
  'description':'Postularse automáticamente a empleos por habilidades. Leemos tu CV, detectamos skills y aplicamos por vos.',
  'canonical':'http://127.0.0.1:8000/',
}


def home(request):
  if request.method == 'POST':
    form = LeadForm(request.POST)
    if form.is_valid():
      Lead.objects.get_or_create(email=form.cleaned_data['email'])
      return redirect('gracias')
  else:
    form = LeadForm()
  return render(request,'landing/home.html',{'seo':BASE_SEO,'form':form})


def gracias(request):
  return render(request,'landing/gracias.html',{'seo':{
    'title':'¡Gracias! — PostulaMatic',
    'description':'Te avisaremos cuando esté listo.',
    'canonical':'http://127.0.0.1:8000/gracias',
  }})


def privacidad(request):
  return render(request,'landing/privacidad.html',{'seo':{
    'title':'Privacidad — PostulaMatic',
    'description':'Política de privacidad de PostulaMatic.',
    'canonical':'http://127.0.0.1:8000/privacidad',
  }})


def terminos(request):
  return render(request,'landing/terminos.html',{'seo':{
    'title':'Términos — PostulaMatic',
    'description':'Términos y condiciones de PostulaMatic.',
    'canonical':'http://127.0.0.1:8000/terminos',
  }})


