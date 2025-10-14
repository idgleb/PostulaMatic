"""
Comando para crear datos de prueba para el sistema de emails.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.utils import timezone

from matching.models import UserCV, JobPosting, UserProfile


class Command(BaseCommand):
    help = 'Crea datos de prueba para el sistema de emails'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID del usuario para crear datos de prueba',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Creando datos de prueba...')
        )

        # Obtener o crear usuario
        user_id = options['user_id']
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Usuario con ID {user_id} no encontrado')
                )
                return
        else:
            # Crear usuario de prueba
            user, created = User.objects.get_or_create(
                username='test',
                defaults={
                    'email': 'test@test.com',
                    'first_name': 'Usuario',
                    'last_name': 'Prueba'
                }
            )
            if created:
                self.stdout.write(f'👤 Usuario creado: {user.username}')
            else:
                self.stdout.write(f'👤 Usuario existente: {user.username}')

        # Crear perfil de usuario
        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                'display_name': 'Usuario de Prueba',
                'daily_limit': 50,
                'match_threshold': 70,
                'min_pause_seconds': 30,
                'max_pause_seconds': 120,
                'is_active': True
            }
        )
        if created:
            self.stdout.write(f'⚙️ Perfil creado para {user.username}')
        else:
            self.stdout.write(f'⚙️ Perfil existente para {user.username}')

        # Crear CV de prueba
        existing_cv = UserCV.objects.filter(user=user).first()
        if not existing_cv:
            # Crear contenido de CV de prueba
            cv_content = """
            Juan Pérez - Desarrollador Full Stack
            
            Email: juan.perez@email.com
            Teléfono: +54 11 1234-5678
            LinkedIn: linkedin.com/in/juanperez
            
            EXPERIENCIA PROFESIONAL
            
            Desarrollador Senior - TechCorp (2022-2024)
            • Desarrollo de aplicaciones web con React y Node.js
            • Implementación de microservicios con Python y Django
            • Gestión de bases de datos PostgreSQL y MongoDB
            • Colaboración en metodologías Agile/Scrum
            
            Desarrollador Full Stack - StartupXYZ (2020-2022)
            • Desarrollo frontend con Vue.js y TypeScript
            • Backend con Python, Flask y FastAPI
            • Integración de APIs REST y GraphQL
            • Implementación de CI/CD con Docker y AWS
            
            EDUCACIÓN
            
            Ingeniería en Sistemas - Universidad Tecnológica (2016-2020)
            
            HABILIDADES TÉCNICAS
            
            Lenguajes: Python, JavaScript, TypeScript, Java, SQL
            Frameworks: Django, React, Vue.js, FastAPI, Express.js
            Bases de Datos: PostgreSQL, MongoDB, Redis
            Herramientas: Git, Docker, AWS, Kubernetes, Jenkins
            Metodologías: Agile, Scrum, TDD
            
            PROYECTOS REALIZADOS
            
            • Sistema de gestión de inventario para empresa retail
            • Aplicación móvil de delivery con React Native
            • Plataforma de e-learning con Django y PostgreSQL
            • API de pagos integrada con Stripe y PayPal
            """
            
            # Crear archivo de CV
            cv_file = ContentFile(cv_content.encode('utf-8'), name='cv_juan_perez.txt')
            
            # Crear objeto UserCV
            user_cv = UserCV.objects.create(
                user=user,
                original_file=cv_file,
                parsed_text=cv_content,
                skills={
                    'skills': [
                        'Python', 'JavaScript', 'TypeScript', 'Java', 'SQL',
                        'Django', 'React', 'Vue.js', 'FastAPI', 'Express.js',
                        'PostgreSQL', 'MongoDB', 'Redis', 'Git', 'Docker',
                        'AWS', 'Kubernetes', 'Jenkins', 'Agile', 'Scrum'
                    ],
                    'categories': {
                        'languages': ['Python', 'JavaScript', 'TypeScript', 'Java', 'SQL'],
                        'frameworks': ['Django', 'React', 'Vue.js', 'FastAPI', 'Express.js'],
                        'databases': ['PostgreSQL', 'MongoDB', 'Redis'],
                        'tools': ['Git', 'Docker', 'AWS', 'Kubernetes', 'Jenkins'],
                        'methodologies': ['Agile', 'Scrum']
                    }
                }
            )
            
            self.stdout.write(f'📄 CV creado: {user_cv.id}')
        else:
            self.stdout.write(f'📄 CV existente: {existing_cv.id}')

        # Crear puestos de trabajo de prueba
        job_postings_data = [
            {
                'external_id': 'job_001',
                'title': 'Desarrollador Python Senior',
                'description': '''
                Buscamos un desarrollador Python senior para unirse a nuestro equipo de desarrollo.
                
                Requisitos:
                - 5+ años de experiencia con Python
                - Conocimiento en Django y FastAPI
                - Experiencia con bases de datos PostgreSQL
                - Conocimiento en Docker y AWS
                - Experiencia en metodologías Agile
                
                Ofrecemos:
                - Salario competitivo
                - Trabajo remoto
                - Capacitación continua
                - Ambiente colaborativo
                ''',
                'email': 'hr@techcompany.com'
            },
            {
                'external_id': 'job_002',
                'title': 'Full Stack Developer React/Python',
                'description': '''
                Posición para desarrollador full stack con experiencia en React y Python.
                
                Requisitos:
                - 3+ años de experiencia con React
                - Conocimiento en Python y Django
                - Experiencia con TypeScript
                - Conocimiento en Git y metodologías Agile
                
                Beneficios:
                - Trabajo híbrido
                - Seguro médico
                - Bono por productividad
                - Vacaciones flexibles
                ''',
                'email': 'jobs@startup.com'
            },
            {
                'external_id': 'job_003',
                'title': 'Desarrollador Backend Python',
                'description': '''
                Desarrollador backend especializado en Python para proyecto de escala.
                
                Requisitos:
                - Experiencia sólida con Python
                - Conocimiento en FastAPI y Django
                - Experiencia con bases de datos (PostgreSQL, MongoDB)
                - Conocimiento en microservicios
                - Experiencia con Docker y Kubernetes
                
                Ofrecemos:
                - Salario en USD
                - Trabajo 100% remoto
                - Equipamiento completo
                - Horario flexible
                ''',
                'email': 'careers@fintech.com'
            }
        ]

        created_jobs = 0
        for job_data in job_postings_data:
            job_posting, created = JobPosting.objects.get_or_create(
                external_id=job_data['external_id'],
                defaults=job_data
            )
            if created:
                created_jobs += 1
                self.stdout.write(f'💼 Puesto creado: {job_posting.title}')

        if created_jobs == 0:
            self.stdout.write('💼 Todos los puestos ya existen')

        self.stdout.write(
            self.style.SUCCESS(f'✅ Datos de prueba creados exitosamente')
        )
        self.stdout.write(f'👤 Usuario: {user.username} (ID: {user.id})')
        self.stdout.write(f'📄 CV: {UserCV.objects.filter(user=user).count()} CV(s)')
        self.stdout.write(f'💼 Puestos: {JobPosting.objects.count()} puestos')
