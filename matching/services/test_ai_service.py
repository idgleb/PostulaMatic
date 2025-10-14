"""
Tests para el servicio de IA.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from .ai_service import AIEmailService, EmailContent, OpenAIProvider, AnthropicProvider


class TestAIEmailService(TestCase):
    """Tests para el servicio de IA."""
    
    def setUp(self):
        self.service = AIEmailService()
        self.sample_job_description = """
        Estamos buscando un Desarrollador Python con experiencia en Django.
        Requisitos:
        - 3+ años de experiencia en Python
        - Conocimiento en Django, PostgreSQL
        - Experiencia con APIs REST
        """
        
        self.sample_cv_skills = {
            'skills': ['Python', 'Django', 'PostgreSQL', 'REST APIs', 'JavaScript'],
            'experience': '5 años',
            'education': 'Ingeniería en Sistemas'
        }
        
        self.sample_user_profile = {
            'display_name': 'Juan Pérez',
            'email': 'juan@example.com'
        }
    
    def test_service_initialization(self):
        """Test que el servicio se inicializa correctamente."""
        self.assertIsInstance(self.service, AIEmailService)
        self.assertIn('openai', self.service.get_available_providers())
        self.assertIn('anthropic', self.service.get_available_providers())
    
    def test_get_available_providers(self):
        """Test que retorna los proveedores disponibles."""
        providers = self.service.get_available_providers()
        self.assertIsInstance(providers, list)
        self.assertGreater(len(providers), 0)
    
    def test_openai_provider_configured(self):
        """Test que OpenAI está configurado cuando hay API key en la base de datos."""
        from matching.models import AIConfiguration
        config = AIConfiguration.get_config()
        config.openai_enabled = True
        config.set_openai_key('test-key')
        config.save()
        
        # Limpiar cache del servicio
        self.service._config = None
        
        self.assertTrue(self.service.is_provider_configured('openai'))
    
    def test_openai_provider_not_configured(self):
        """Test que OpenAI no está configurado sin API key."""
        from matching.models import AIConfiguration
        config = AIConfiguration.get_config()
        config.openai_enabled = False
        config.save()
        
        # Limpiar cache del servicio
        self.service._config = None
        
        self.assertFalse(self.service.is_provider_configured('openai'))
    
    def test_anthropic_provider_configured(self):
        """Test que Anthropic está configurado cuando hay API key en la base de datos."""
        from matching.models import AIConfiguration
        config = AIConfiguration.get_config()
        config.anthropic_enabled = True
        config.set_anthropic_key('test-key')
        config.save()
        
        # Limpiar cache del servicio
        self.service._config = None
        
        self.assertTrue(self.service.is_provider_configured('anthropic'))
    
    def test_unknown_provider(self):
        """Test que proveedor desconocido retorna False."""
        self.assertFalse(self.service.is_provider_configured('unknown'))
    
    def test_generate_email_without_api_keys(self):
        """Test que genera error cuando no hay API keys."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': '', 'ANTHROPIC_API_KEY': ''}):
            result = self.service.generate_email(
                self.sample_job_description,
                self.sample_cv_skills,
                self.sample_user_profile
            )
            self.assertIsInstance(result, EmailContent)
            self.assertTrue(result.error is not None or result.subject == "")


class TestEmailContent(TestCase):
    """Tests para la clase EmailContent."""
    
    def test_email_content_creation(self):
        """Test creación de EmailContent."""
        content = EmailContent(
            subject="Test Subject",
            body="Test Body",
            provider="openai",
            model="gpt-3.5-turbo",
            tokens_used=100
        )
        
        self.assertEqual(content.subject, "Test Subject")
        self.assertEqual(content.body, "Test Body")
        self.assertEqual(content.provider, "openai")
        self.assertEqual(content.model, "gpt-3.5-turbo")
        self.assertEqual(content.tokens_used, 100)
        self.assertIsNone(content.error)


class TestPromptBuilding(TestCase):
    """Tests para construcción de prompts."""
    
    def setUp(self):
        self.provider = OpenAIProvider()
    
    def test_build_prompt_basic(self):
        """Test construcción básica de prompt."""
        job_desc = "Desarrollador Python"
        cv_skills = {'skills': ['Python', 'Django']}
        user_profile = {'display_name': 'Juan'}
        
        prompt = self.provider._build_prompt(job_desc, cv_skills, user_profile)
        
        self.assertIn("Desarrollador Python", prompt)
        self.assertIn("Python, Django", prompt)
        self.assertIn("Juan", prompt)
        self.assertIn("ASUNTO:", prompt)
        self.assertIn("CUERPO:", prompt)
    
    def test_build_prompt_with_custom(self):
        """Test construcción de prompt con instrucciones personalizadas."""
        job_desc = "Desarrollador Python"
        cv_skills = {'skills': ['Python']}
        user_profile = {'display_name': 'Juan'}
        custom = "Sé muy formal"
        
        prompt = self.provider._build_prompt(job_desc, cv_skills, user_profile, custom)
        
        self.assertIn("Sé muy formal", prompt)


class TestEmailParsing(TestCase):
    """Tests para parsing de emails generados."""
    
    def setUp(self):
        self.provider = OpenAIProvider()
    
    def test_parse_email_standard_format(self):
        """Test parsing de email con formato estándar."""
        content = """
        ASUNTO: Postulación para Desarrollador Python
        CUERPO: Estimado equipo de recursos humanos,
        
        Me dirijo a ustedes para postular al puesto de Desarrollador Python.
        Tengo experiencia en Python y Django.
        
        Saludos cordiales,
        Juan
        """
        
        subject, body = self.provider._parse_email_content(content)
        
        self.assertEqual(subject, "Postulación para Desarrollador Python")
        self.assertIn("Estimado equipo", body)
        self.assertIn("Juan", body)
    
    def test_parse_email_no_format(self):
        """Test parsing de email sin formato específico."""
        content = """
        Postulación para Desarrollador Python
        
        Estimado equipo,
        Me interesa el puesto.
        """
        
        subject, body = self.provider._parse_email_content(content)
        
        # Debería usar la primera línea como subject si es corta
        self.assertEqual(subject, "Postulación para Desarrollador Python")
        self.assertIn("Estimado equipo", body)
    
    def test_parse_email_empty(self):
        """Test parsing de email vacío."""
        content = ""
        
        subject, body = self.provider._parse_email_content(content)
        
        self.assertEqual(subject, "Postulación de trabajo")  # Fallback
        self.assertEqual(body, "")  # Vacío


if __name__ == '__main__':
    unittest.main()

