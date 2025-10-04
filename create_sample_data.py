#!/usr/bin/env python
"""
Script para crear datos de prueba en PostulaMatic
"""
import os
from datetime import datetime, timedelta

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postulamatic.settings")
django.setup()

from django.contrib.auth.models import User

from matching.models import JobPosting, MatchScore, UserCV, UserProfile


def create_sample_data():
    print("=== CREANDO DATOS DE PRUEBA ===")

    # Obtener el usuario y CV
    try:
        user = User.objects.get(username="idgle2")
        cv = UserCV.objects.filter(user=user).first()
        profile = UserProfile.objects.get(user=user)

        print(f"Usuario: {user.username}")
        print(f'CV: {cv.original_file.name if cv else "No encontrado"}')
    except Exception as e:
        print(f"Error obteniendo datos del usuario: {e}")
        return

    # Crear ofertas de trabajo de prueba
    jobs_data = [
        {
            "title": "Desarrollador Android Senior",
            "company": "TechCorp Argentina",
            "location": "Buenos Aires, CABA",
            "description": "Buscamos desarrollador Android con experiencia en Kotlin, Jetpack Compose, y arquitecturas MVVM. Conocimiento en Firebase, GitLab CI/CD, y metodologías ágiles.",
            "url": "https://example.com/job1",
            "external_id": "dvc_001",
            "posted_at": datetime.now() - timedelta(hours=2),
        },
        {
            "title": "Programador Kotlin Mobile",
            "company": "StartupXYZ",
            "location": "Remoto",
            "description": "Desarrollo de aplicaciones móviles Android usando Kotlin, Room, Retrofit, y Dagger Hilt. Experiencia en coroutines y Flow.",
            "url": "https://example.com/job2",
            "external_id": "dvc_002",
            "posted_at": datetime.now() - timedelta(hours=5),
        },
        {
            "title": "Mobile Developer",
            "company": "Digital Solutions",
            "location": "Buenos Aires, CABA",
            "description": "Desarrollador móvil con experiencia en Android, Java, y herramientas de CI/CD. Conocimiento en Git y metodologías ágiles.",
            "url": "https://example.com/job3",
            "external_id": "dvc_003",
            "posted_at": datetime.now() - timedelta(hours=8),
        },
        {
            "title": "Android Developer",
            "company": "Innovation Labs",
            "location": "Córdoba, Argentina",
            "description": "Desarrollador Android con experiencia en Kotlin, Java, GitLab CI, y metodologías ágiles. Conocimiento en Firebase y arquitecturas limpias.",
            "url": "https://example.com/job4",
            "external_id": "dvc_004",
            "posted_at": datetime.now() - timedelta(hours=12),
        },
        {
            "title": "Senior Mobile Developer",
            "company": "TechStart Argentina",
            "location": "Buenos Aires, CABA",
            "description": "Desarrollador móvil senior con experiencia en Android, Kotlin, Jetpack Compose, Room, y Dagger Hilt. Liderazgo técnico y mentoría.",
            "url": "https://example.com/job5",
            "external_id": "dvc_005",
            "posted_at": datetime.now() - timedelta(hours=1),
        },
    ]

    # Crear ofertas
    jobs_created = 0
    for job_data in jobs_data:
        job, created = JobPosting.objects.update_or_create(
            external_id=job_data["external_id"],
            defaults={
                "title": job_data["title"],
                "company": job_data["company"],
                "location": job_data["location"],
                "description": job_data["description"],
                "url": job_data["url"],
                "source": "dvcarreras",
                "posted_at": job_data["posted_at"],
            },
        )
        if created:
            jobs_created += 1
            print(f"Creada oferta: {job.title}")

    # Crear matches de ejemplo
    matches_data = [
        {"score": 85, "external_id": "dvc_001"},
        {"score": 78, "external_id": "dvc_002"},
        {"score": 65, "external_id": "dvc_003"},
        {"score": 72, "external_id": "dvc_004"},
        {"score": 88, "external_id": "dvc_005"},
    ]

    matches_created = 0
    for match_data in matches_data:
        try:
            job = JobPosting.objects.get(external_id=match_data["external_id"])
            match, created = MatchScore.objects.update_or_create(
                user=user,
                cv=cv,
                job_posting=job,
                defaults={
                    "score": match_data["score"],
                    "details": {
                        "skills_matched": ["kotlin", "android", "java", "gitlab ci"],
                        "explanation": f'Coincidencia del {match_data["score"]}% basada en habilidades técnicas detectadas en el CV',
                    },
                },
            )
            if created:
                matches_created += 1
                print(f"Creado match: {match.score}% para {job.title}")
        except Exception as e:
            print(f'Error creando match para {match_data["external_id"]}: {e}')

    print()
    print("=== RESUMEN ===")
    print(f"Ofertas totales: {JobPosting.objects.count()}")
    print(f"Matches totales: {MatchScore.objects.count()}")
    print(f"Ofertas creadas: {jobs_created}")
    print(f"Matches creados: {matches_created}")
    print("¡Datos de prueba creados exitosamente!")


if __name__ == "__main__":
    create_sample_data()
