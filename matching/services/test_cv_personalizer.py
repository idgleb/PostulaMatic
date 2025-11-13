"""
Tests para el servicio de personalización de CV.
"""

from unittest.mock import Mock, patch

from django.test import TestCase


from .ats_matcher import KeywordExtractor
from .cv_personalizer import CVPersonalizationService


class TestKeywordExtractor(TestCase):
    """Tests para el extractor de keywords (reemplaza JobRequirementsAnalyzer)."""

    def setUp(self):
        self.extractor = KeywordExtractor()

    def test_extract_keywords_basic(self):
        """Test extracción básica de keywords."""
        description = """
        Buscamos Desarrollador Python Senior con 5+ años de experiencia.
        
        Requisitos:
        - Python, Django, PostgreSQL
        - React, JavaScript
        - Docker, AWS
        - Experiencia con APIs REST
        """

        result = self.extractor.extract_keywords(description)

        self.assertIn("python", result)
        self.assertIn("django", result)
        self.assertIn("postgresql", result)
        self.assertIn("react", result)
        self.assertIn("javascript", result)
        self.assertIn("docker", result)
        self.assertIn("aws", result)

    def test_extract_keywords_multiple_technologies(self):
        """Test extracción de múltiples tecnologías."""
        description = """
        Necesitamos alguien con experiencia en:
        - Python y Django
        - JavaScript y React
        - PostgreSQL y MongoDB
        - Docker y Kubernetes
        - AWS y Azure
        """

        result = self.extractor.extract_keywords(description)

        self.assertIn("python", result)
        self.assertIn("django", result)
        self.assertIn("javascript", result)
        self.assertIn("react", result)
        self.assertIn("postgresql", result)
        self.assertIn("mongodb", result)
        self.assertIn("docker", result)
        self.assertIn("kubernetes", result)
        self.assertIn("aws", result)
        self.assertIn("azure", result)


class TestCVPersonalizationService(TestCase):
    """Tests para el servicio de personalización de CV."""

    def setUp(self):
        self.service = CVPersonalizationService()

        # Mock UserCV
        self.user_cv = Mock()
        self.user_cv.id = 1
        self.user_cv.skills_list = ["Python", "Django", "PostgreSQL", "React"]
        self.user_cv.skills_categories = {
            "backend": ["Python", "Django"],
            "frontend": ["React"],
        }
        self.user_cv.parsed_text = """
        Juan Pérez
        Desarrollador Python con 3 años de experiencia
        Universidad de Buenos Aires - Ingeniería en Sistemas
        Proyecto: Sistema de gestión de inventario en Django
        """
        self.user_cv.original_file.name = "cvs/2025/01/01/juan_cv.pdf"

        # Mock JobPosting
        self.job_posting = Mock()
        self.job_posting.id = 1
        self.job_posting.title = "Desarrollador Python Senior"
        self.job_posting.description = """
        Buscamos Desarrollador Python Senior con 5+ años de experiencia.
        Requisitos: Python, Django, PostgreSQL, React
        """

    def test_personalize_cv_for_job_basic(self):
        """Test personalización básica de CV."""
        with patch.object(self.service, "_generate_personalized_cv") as mock_generate:
            mock_generate.return_value = {
                "header": {
                    "full_name": "Juan Pérez",
                    "email": "juan@example.com",
                    "city": "Buenos Aires",
                    "country": "Argentina",
                    "phone": "+54 11 1234-5678",
                    "links": {},
                    "target_title": "Desarrollador Python Senior",
                },
                "summary": "Desarrollador Python con experiencia sólida",
                "skills": ["Python", "Django"],
                "experience": [],
                "projects": [],
                "education": [],
                "certifications": [],
                "languages": [],
                "extras": {},
                "tailoring_meta": {},
            }

            result = self.service.personalize_cv_for_job(self.user_cv, self.job_posting)

            self.assertTrue(result["success"])
            self.assertIsNotNone(result["personalized_cv"])
            self.assertIsNotNone(result["job_requirements"])
            self.assertIsNotNone(result["cv_data"])
            self.assertGreaterEqual(result["match_score"], 0)

    def test_normalize_cv_data(self):
        """Test normalización de cv_data."""
        # Test con string
        result = self.service._normalize_cv_data("Texto del CV")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["parsed_text"], "Texto del CV")

        # Test con dict
        cv_dict = {"parsed_text": "Texto del CV", "other": "data"}
        result = self.service._normalize_cv_data(cv_dict)
        self.assertEqual(result, cv_dict)

    def test_extract_text_from_cv_data(self):
        """Test extracción de texto del CV."""
        # Test con string
        result = self.service._extract_text_from_cv_data("Texto del CV")
        self.assertEqual(result, "Texto del CV")

        # Test con dict
        cv_dict = {"parsed_text": "Texto del CV"}
        result = self.service._extract_text_from_cv_data(cv_dict)
        self.assertEqual(result, "Texto del CV")

    def test_create_cv_personalization_prompt(self):
        """Test creación de prompt para personalización."""
        cv_data = {
            "parsed_text": "Juan Pérez\nDesarrollador Python con 3 años de experiencia"
        }

        job_requirements = {
            "title": "Desarrollador Python",
            "description": "Buscamos desarrollador Python con experiencia en Django",
            "mail": "hr@example.com",
        }

        result = self.service._create_cv_personalization_prompt(
            cv_data, job_requirements
        )

        self.assertIn("Desarrollador Python", result)
        self.assertIn("Python", result)
        self.assertIn("JSON", result)
        self.assertIn("parsed_text", result)

    def test_personalize_cv_error_handling(self):
        """Test manejo de errores en personalización."""
        # Mock con error
        with patch.object(self.service, "_generate_personalized_cv") as mock_generate:
            mock_generate.side_effect = Exception("Error de IA")

            result = self.service.personalize_cv_for_job(self.user_cv, self.job_posting)

            self.assertFalse(result["success"])
            self.assertIn("error", result)
            self.assertIsNone(result["personalized_cv"])
            self.assertEqual(result["match_score"], 0)
