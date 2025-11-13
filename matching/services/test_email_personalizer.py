"""
Tests para el servicio de personalización de emails.
"""

import unittest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth.models import User

from matching.models import UserCV, JobPosting, MatchScore, UserProfile
from .email_personalizer import (
    CVDataExtractor,
    JobDataExtractor,
    EmailPersonalizationService,
)


class TestCVDataExtractor(TestCase):
    """Tests para el extractor de datos de CV."""

    def setUp(self):
        self.extractor = CVDataExtractor()

    def test_extract_cv_data_basic(self):
        """Test extracción básica de datos de CV."""
        # Mock UserCV
        user_cv = Mock()
        user_cv.id = 1
        user_cv.skills_list = ["Python", "Django", "PostgreSQL"]
        user_cv.skills_categories = {"backend": ["Python", "Django"]}
        user_cv.parsed_text = """
        Juan Pérez
        Desarrollador Python con 3 años de experiencia
        Universidad de Buenos Aires - Ingeniería en Sistemas
        Proyecto: Sistema de gestión de inventario
        """
        user_cv.original_file.name = "cvs/2025/01/01/juan_cv.pdf"

        result = self.extractor.extract_cv_data(user_cv)

        self.assertEqual(result["skills"], ["Python", "Django", "PostgreSQL"])
        self.assertEqual(result["cv_id"], 1)
        self.assertIn("Python", result["experience_summary"])
        self.assertIn("Universidad", result["education"])
        self.assertIn("Sistema de gestión", result["projects"][0])

    def test_extract_experience_info(self):
        """Test extracción de información de experiencia."""
        parsed_text = """
        Desarrollador Python con 5 años de experiencia en desarrollo web.
        Trabajé como Senior Developer en varias empresas.
        """

        result = self.extractor._extract_experience_info(parsed_text)

        self.assertEqual(result["years"], 5)
        self.assertIn("Desarrollador", result["summary"])

    def test_extract_education_info(self):
        """Test extracción de información de educación."""
        parsed_text = """
        Juan Pérez
        Universidad de Buenos Aires - Ingeniería en Sistemas
        Certificaciones en AWS y Docker
        """

        result = self.extractor._extract_education_info(parsed_text)

        self.assertIn("Universidad de Buenos Aires", result)
        self.assertIn("Ingeniería en Sistemas", result)

    def test_extract_projects_info(self):
        """Test extracción de información de proyectos."""
        parsed_text = """
        Proyectos realizados:
        - Sistema de gestión de inventario en Django
        - Aplicación móvil para delivery
        - API REST para e-commerce
        """

        result = self.extractor._extract_projects_info(parsed_text)

        self.assertGreater(len(result), 0)
        self.assertIn("Sistema de gestión", result[0])

    def test_extract_cv_data_empty(self):
        """Test extracción con CV vacío."""
        user_cv = Mock()
        user_cv.id = 1
        user_cv.skills_list = []
        user_cv.skills_categories = {}
        user_cv.parsed_text = ""
        user_cv.original_file.name = ""

        result = self.extractor.extract_cv_data(user_cv)

        self.assertEqual(result["skills"], [])
        self.assertEqual(result["experience_years"], 0)
        self.assertEqual(result["education"], "")
        self.assertEqual(result["projects"], [])


class TestJobDataExtractor(TestCase):
    """Tests para el extractor de datos de puestos."""

    def setUp(self):
        self.extractor = JobDataExtractor()

    def test_extract_job_data_basic(self):
        """Test extracción básica de datos de puesto."""
        job_posting = Mock()
        job_posting.id = 1
        job_posting.title = "Desarrollador Python Senior"
        job_posting.description = """
        Buscamos desarrollador Python con experiencia en Django.
        Requisitos:
        - 5+ años de experiencia en Python
        - Conocimiento en Django, PostgreSQL
        - Trabajo remoto disponible
        - Buenos Aires, Argentina
        """
        job_posting.email = "hr@empresa.com"
        job_posting.external_id = "job_123"

        result = self.extractor.extract_job_data(job_posting)

        self.assertEqual(result["title"], "Desarrollador Python Senior")
        self.assertIn("Python", result["required_skills"])
        self.assertIn("Django", result["required_skills"])
        self.assertEqual(result["experience_level"], "Senior")
        self.assertEqual(result["work_type"], "Remoto")
        self.assertIn("Buenos Aires", result["location"])

    def test_extract_required_skills(self):
        """Test extracción de habilidades requeridas."""
        description = """
        Necesitamos alguien con experiencia en:
        - Python y Django
        - JavaScript y React
        - PostgreSQL y Redis
        - Docker y AWS
        """

        result = self.extractor._extract_required_skills(description)

        expected_skills = [
            "Python",
            "Django",
            "Javascript",
            "React",
            "Postgresql",
            "Redis",
            "Docker",
            "Aws",
        ]
        for skill in expected_skills:
            self.assertIn(skill, result)

    def test_extract_experience_level(self):
        """Test extracción de nivel de experiencia."""
        # Test Senior
        description_senior = "Buscamos desarrollador Senior con experiencia"
        result = self.extractor._extract_experience_level(description_senior)
        self.assertEqual(result, "Senior")

        # Test Junior
        description_junior = "Posición para desarrollador Junior"
        result = self.extractor._extract_experience_level(description_junior)
        self.assertEqual(result, "Junior")

        # Test Mid-level
        description_mid = "Desarrollador Mid-level con experiencia intermedia"
        result = self.extractor._extract_experience_level(description_mid)
        self.assertEqual(result, "Mid-level")

    def test_extract_work_type(self):
        """Test extracción de tipo de trabajo."""
        # Test Remoto
        description_remote = "Trabajo remoto disponible"
        result = self.extractor._extract_work_type(description_remote)
        self.assertEqual(result, "Remoto")

        # Test Presencial
        description_office = "Trabajo presencial en oficina"
        result = self.extractor._extract_work_type(description_office)
        self.assertEqual(result, "Presencial")

        # Test Híbrido
        description_hybrid = "Modalidad híbrida de trabajo"
        result = self.extractor._extract_work_type(description_hybrid)
        self.assertEqual(result, "Híbrido")

    def test_extract_location(self):
        """Test extracción de ubicación."""
        description = "Empresa ubicada en Buenos Aires, Argentina"
        result = self.extractor._extract_location(description)
        self.assertIn("Buenos Aires", result)

    def test_extract_benefits(self):
        """Test extracción de beneficios."""
        description = """
        Ofrecemos:
        - Trabajo remoto
        - Vacaciones flexibles
        - Seguro médico
        - Capacitación continua
        """

        result = self.extractor._extract_benefits(description)

        expected_benefits = ["Remoto", "Flexible", "Seguro Médico", "Capacitación"]
        for benefit in expected_benefits:
            self.assertIn(benefit, result)


class TestEmailPersonalizationService(TestCase):
    """Tests para el servicio de personalización."""

    def setUp(self):
        self.service = EmailPersonalizationService()

        # Mock User
        self.user = Mock()
        self.user.id = 1
        self.user.email = "test@example.com"
        self.user.first_name = "Juan"
        self.user.username = "juan"

        # Mock UserCV
        self.user_cv = Mock()
        self.user_cv.id = 1
        self.user_cv.skills_list = ["Python", "Django"]
        self.user_cv.skills_categories = {"backend": ["Python"]}
        self.user_cv.parsed_text = "Desarrollador Python con 3 años de experiencia"
        self.user_cv.original_file.name = "cv.pdf"

        # Mock JobPosting
        self.job_posting = Mock()
        self.job_posting.id = 1
        self.job_posting.title = "Desarrollador Python"
        self.job_posting.description = "Buscamos desarrollador Python con Django"
        self.job_posting.email = "hr@empresa.com"
        self.job_posting.external_id = "job_123"

    @patch("matching.services.email_personalizer.ai_email_service")
    def test_generate_personalized_email_success(self, mock_ai_service):
        """Test generación exitosa de email personalizado."""
        # Mock AI service response
        from .ai_service import EmailContent

        mock_result = EmailContent(
            subject="Postulación para Desarrollador Python",
            body="Estimado equipo, me interesa el puesto...",
            provider="openai",
            model="gpt-3.5-turbo",
            tokens_used=150,
        )
        mock_ai_service.generate_email.return_value = mock_result

        # Mock user profile
        with patch.object(self.service, "_get_user_profile_data") as mock_profile:
            mock_profile.return_value = {
                "display_name": "Juan",
                "email": "test@example.com",
                "user_id": 1,
            }

            result = self.service.generate_personalized_email(
                self.user, self.user_cv, self.job_posting
            )

        self.assertEqual(result.subject, "Postulación para Desarrollador Python")
        self.assertEqual(result.provider, "openai")
        mock_ai_service.generate_email.assert_called_once()

    def test_select_optimal_template_technical(self):
        """Test selección de template técnico."""
        cv_data = {"experience_years": 3}
        job_data = {"title": "Desarrollador Python", "description": "Desarrollo web"}

        result = self.service._select_optimal_template(cv_data, job_data, "base")

        self.assertEqual(result, "technical")

    def test_select_optimal_template_startup(self):
        """Test selección de template para startup."""
        cv_data = {"experience_years": 2}
        job_data = {
            "title": "Desarrollador",
            "description": "Buscamos desarrollador",
        }  # Corto

        result = self.service._select_optimal_template(cv_data, job_data, "base")

        self.assertEqual(result, "startup")

    def test_select_optimal_template_corporate(self):
        """Test selección de template corporativo."""
        cv_data = {"experience_years": 2}
        job_data = {"title": "Analista", "description": "A" * 2500}  # Muy largo

        result = self.service._select_optimal_template(cv_data, job_data, "base")

        self.assertEqual(result, "corporate")

    def test_select_optimal_template_formal(self):
        """Test selección de template formal para experiencia alta."""
        cv_data = {"experience_years": 7}
        job_data = {"title": "Consultor", "description": "A" * 1000}

        result = self.service._select_optimal_template(cv_data, job_data, "base")

        self.assertEqual(result, "formal")

    def test_select_optimal_template_requested(self):
        """Test que se respeta el template solicitado."""
        cv_data = {"experience_years": 2}
        job_data = {"title": "Desarrollador", "description": "A" * 1000}

        result = self.service._select_optimal_template(cv_data, job_data, "creative")

        self.assertEqual(result, "creative")

    def test_guess_industry(self):
        """Test detección de industria."""
        # Test Fintech
        description = "Empresa fintech buscando desarrollador"
        result = self.service._guess_industry(description)
        self.assertEqual(result, "Fintech")

        # Test E-commerce
        description = "Plataforma de e-commerce"
        result = self.service._guess_industry(description)
        self.assertEqual(result, "E-Commerce")

        # Test por defecto
        description = "Empresa de software"
        result = self.service._guess_industry(description)
        self.assertEqual(result, "Technology")


if __name__ == "__main__":
    unittest.main()
