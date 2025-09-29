#!/usr/bin/env python3
"""
Script para verificar las ofertas guardadas.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')
django.setup()

from matching.models import JobPosting

def check_jobs():
    """Verifica las ofertas guardadas."""
    
    print("🔍 Verificando ofertas guardadas...")
    
    jobs = JobPosting.objects.all().order_by('-created_at')[:5]
    
    print(f"📊 Total de ofertas: {JobPosting.objects.count()}")
    print(f"📋 Mostrando las últimas {len(jobs)} ofertas:\n")
    
    for i, job in enumerate(jobs, 1):
        print(f"--- Oferta {i} ---")
        print(f"Título: {job.title}")
        print(f"Email: '{job.email}'")
        print(f"Descripción (primeros 150 chars): {job.description[:150]}...")
        print(f"External ID: {job.external_id}")
        print()
    
    # Contar ofertas con email
    jobs_with_email = JobPosting.objects.exclude(email='').count()
    print(f"📧 Ofertas con email: {jobs_with_email}")
    print(f"📭 Ofertas sin email: {JobPosting.objects.count() - jobs_with_email}")

if __name__ == "__main__":
    check_jobs()


