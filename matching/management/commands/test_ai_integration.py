"""
Comando Django para probar la integración con proveedores de IA.
"""

import os
import logging
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.conf import settings

from matching.models import UserCV, JobPosting, UserProfile
from matching.services.ai_service import ai_email_service
from matching.services.email_personalizer import email_personalization_service

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Prueba la integración con proveedores de IA (OpenAI/Anthropic)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--provider',
            type=str,
            choices=['openai', 'anthropic', 'both'],
            default='both',
            help='Proveedor de IA a probar'
        )
        parser.add_argument(
            '--user-id',
            type=int,
            help='ID del usuario para usar sus datos'
        )
        parser.add_argument(
            '--cv-id',
            type=int,
            help='ID del CV específico a usar'
        )
        parser.add_argument(
            '--job-id',
            type=int,
            help='ID del puesto específico a usar'
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🤖 Iniciando prueba de integración con IA...')
        )
        
        # Verificar configuración
        self.check_configuration()
        
        # Obtener datos de prueba
        user, user_cv, job_posting = self.get_test_data(options)
        
        # Probar proveedores
        provider = options['provider']
        
        if provider in ['openai', 'both']:
            self.test_openai(user, user_cv, job_posting)
        
        if provider in ['anthropic', 'both']:
            self.test_anthropic(user, user_cv, job_posting)
        
        self.stdout.write(
            self.style.SUCCESS('✅ Pruebas de integración completadas')
        )

    def check_configuration(self):
        """Verifica la configuración de las API keys."""
        self.stdout.write('\n🔧 Verificando configuración...')
        
        # Verificar OpenAI
        openai_key = os.getenv('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', '')
        if openai_key:
            self.stdout.write(
                self.style.SUCCESS('✅ OpenAI API Key configurada')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ OpenAI API Key no configurada')
            )
        
        # Verificar Anthropic
        anthropic_key = os.getenv('ANTHROPIC_API_KEY') or getattr(settings, 'ANTHROPIC_API_KEY', '')
        if anthropic_key:
            self.stdout.write(
                self.style.SUCCESS('✅ Anthropic API Key configurada')
            )
        else:
            self.stdout.write(
                self.style.WARNING('⚠️ Anthropic API Key no configurada')
            )
        
        # Verificar proveedor por defecto
        default_provider = os.getenv('AI_PROVIDER', 'openai')
        self.stdout.write(f'📋 Proveedor por defecto: {default_provider}')

    def get_test_data(self, options):
        """Obtiene datos de prueba para la generación."""
        self.stdout.write('\n📊 Obteniendo datos de prueba...')
        
        # Obtener usuario
        if options['user_id']:
            try:
                user = User.objects.get(id=options['user_id'])
            except User.DoesNotExist:
                raise CommandError(f'Usuario con ID {options["user_id"]} no encontrado')
        else:
            user = User.objects.filter(userprofile__isnull=False).first()
            if not user:
                raise CommandError('No se encontraron usuarios con perfil configurado')
        
        self.stdout.write(f'👤 Usuario: {user.email}')
        
        # Obtener CV
        if options['cv_id']:
            try:
                user_cv = UserCV.objects.get(id=options['cv_id'], user=user)
            except UserCV.DoesNotExist:
                raise CommandError(f'CV con ID {options["cv_id"]} no encontrado para el usuario')
        else:
            user_cv = UserCV.objects.filter(
                user=user,
                parsed_text__isnull=False
            ).exclude(parsed_text='').first()
            
            if not user_cv:
                raise CommandError('No se encontraron CVs procesados para el usuario')
        
        self.stdout.write(f'📄 CV: {user_cv.original_file.name} ({user_cv.skills_count} habilidades)')
        
        # Obtener puesto
        if options['job_id']:
            try:
                job_posting = JobPosting.objects.get(id=options['job_id'])
            except JobPosting.DoesNotExist:
                raise CommandError(f'Puesto con ID {options["job_id"]} no encontrado')
        else:
            job_posting = JobPosting.objects.filter(
                description__isnull=False
            ).exclude(description='').first()
            
            if not job_posting:
                raise CommandError('No se encontraron puestos de trabajo disponibles')
        
        self.stdout.write(f'💼 Puesto: {job_posting.title}')
        
        return user, user_cv, job_posting

    def test_openai(self, user, user_cv, job_posting):
        """Prueba la integración con OpenAI."""
        self.stdout.write('\n🔵 Probando OpenAI...')
        
        try:
            # Verificar si está configurado
            if not ai_email_service.is_provider_configured('openai'):
                self.stdout.write(
                    self.style.WARNING('⚠️ OpenAI no configurado, saltando prueba')
                )
                return
            
            # Generar email usando el servicio de personalización
            result = email_personalization_service.generate_personalized_email(
                user=user,
                user_cv=user_cv,
                job_posting=job_posting,
                ai_provider='openai',
                template_type='technical'
            )
            
            if result.error:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error con OpenAI: {result.error}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ OpenAI: Email generado exitosamente')
                )
                self.display_email_result(result, 'OpenAI')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error probando OpenAI: {e}')
            )
            logger.error(f"Error probando OpenAI: {e}")

    def test_anthropic(self, user, user_cv, job_posting):
        """Prueba la integración con Anthropic."""
        self.stdout.write('\n🟣 Probando Anthropic...')
        
        try:
            # Verificar si está configurado
            if not ai_email_service.is_provider_configured('anthropic'):
                self.stdout.write(
                    self.style.WARNING('⚠️ Anthropic no configurado, saltando prueba')
                )
                return
            
            # Generar email usando el servicio de personalización
            result = email_personalization_service.generate_personalized_email(
                user=user,
                user_cv=user_cv,
                job_posting=job_posting,
                ai_provider='anthropic',
                template_type='creative'
            )
            
            if result.error:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error con Anthropic: {result.error}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✅ Anthropic: Email generado exitosamente')
                )
                self.display_email_result(result, 'Anthropic')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error probando Anthropic: {e}')
            )
            logger.error(f"Error probando Anthropic: {e}")

    def display_email_result(self, result, provider):
        """Muestra el resultado del email generado."""
        self.stdout.write(f'\n📧 Resultado {provider}:')
        self.stdout.write('─' * 50)
        
        # Información del proveedor
        self.stdout.write(f'Proveedor: {result.provider}')
        self.stdout.write(f'Modelo: {result.model}')
        if result.tokens_used:
            self.stdout.write(f'Tokens usados: {result.tokens_used}')
        
        # Asunto
        self.stdout.write(f'\n📌 Asunto:')
        self.stdout.write(f'  {result.subject}')
        
        # Cuerpo
        self.stdout.write(f'\n📝 Cuerpo:')
        body_lines = result.body.split('\n')
        for line in body_lines[:10]:  # Mostrar primeras 10 líneas
            self.stdout.write(f'  {line}')
        
        if len(body_lines) > 10:
            self.stdout.write(f'  ... ({len(body_lines) - 10} líneas más)')
        
        self.stdout.write('─' * 50)
