"""
Tests para el servicio de personalización de CV.
"""

import unittest
from unittest.mock import Mock, patch
from django.test import TestCase
from django.contrib.auth.models import User

from matching.models import UserCV, JobPosting
from .cv_personalizer import (
    JobRequirementsAnalyzer, 
    CVPersonalizationService
)


class TestJobRequirementsAnalyzer(TestCase):
    """Tests para el analizador de requisitos del puesto."""
    
    def setUp(self):
        self.analyzer = JobRequirementsAnalyzer()
    
    def test_analyze_job_requirements_basic(self):
        """Test análisis básico de requisitos."""
        job_posting = Mock()
        job_posting.id = 1
        job_posting.title = "Desarrollador Python Senior"
        job_posting.description = """
        Buscamos Desarrollador Python Senior con 5+ años de experiencia.
        
        Requisitos:
        - Python, Django, PostgreSQL
        - React, JavaScript
        - Docker, AWS
        - Experiencia con APIs REST
        
        Responsabilidades:
        - Desarrollo de aplicaciones web
        - Mantenimiento de sistemas existentes
        - Colaboración con equipo de desarrollo
        
        Beneficios:
        - Trabajo remoto
        - Seguro médico
        - Vacaciones pagadas
        """
        
        result = self.analyzer.analyze_job_requirements(job_posting)
        
        self.assertEqual(result['title'], "Desarrollador Python Senior")
        self.assertIn('Python', result['required_skills'])
        self.assertIn('Django', result['required_skills'])
        self.assertEqual(result['experience_level'], 'Senior')
        self.assertIn('Python', result['technologies'])
        self.assertIn('Django', result['technologies'])
        self.assertGreater(len(result['key_responsibilities']), 0)
        self.assertIn('Remoto', result['benefits'])
    
    def test_extract_required_skills(self):
        """Test extracción de habilidades requeridas."""
        description = """
        Necesitamos alguien con experiencia en:
        - Python y Django
        - JavaScript y React
        - PostgreSQL y MongoDB
        - Docker y Kubernetes
        - AWS y Azure
        """
        
        result = self.analyzer._extract_required_skills(description)
        
        self.assertIn('Python', result)
        self.assertIn('Django', result)
        self.assertIn('Javascript', result)
        self.assertIn('React', result)
        self.assertIn('Postgresql', result)
        self.assertIn('Mongodb', result)
    
    def test_extract_experience_level(self):
        """Test extracción de nivel de experiencia."""
        # Test Senior
        description_senior = "Buscamos Desarrollador Senior con 5+ años de experiencia"
        result = self.analyzer._extract_experience_level(description_senior)
        self.assertEqual(result, 'Senior')
        
        # Test Junior
        description_junior = "Posición para Desarrollador Junior, entry-level"
        result = self.analyzer._extract_experience_level(description_junior)
        self.assertEqual(result, 'Junior')
        
        # Test Mid-level
        description_mid = "Desarrollador Mid-level con 3 años de experiencia"
        result = self.analyzer._extract_experience_level(description_mid)
        self.assertEqual(result, 'Mid-level')
    
    def test_extract_technologies(self):
        """Test extracción de tecnologías."""
        description = """
        Tecnologías que manejamos:
        - React y Angular
        - Django y Flask
        - PostgreSQL y Redis
        - Docker y Kubernetes
        - AWS y GCP
        """
        
        result = self.analyzer._extract_technologies(description)
        
        self.assertIn('React', result)
        self.assertIn('Angular', result)
        self.assertIn('Django', result)
        self.assertIn('Flask', result)
        self.assertIn('Postgresql', result)
        self.assertIn('Redis', result)
    
    def test_extract_responsibilities(self):
        """Test extracción de responsabilidades."""
        description = """
        Responsabilidades:
        - Desarrollo de aplicaciones web
        - Mantenimiento de sistemas
        - Colaboración con equipo
        - Code reviews
        - Documentación técnica
        
        Requisitos:
        - Python, Django
        """
        
        result = self.analyzer._extract_responsibilities(description)
        
        self.assertGreater(len(result), 0)
        self.assertTrue(any('desarrollo' in resp.lower() for resp in result))
        self.assertTrue(any('mantenimiento' in resp.lower() for resp in result))
    
    def test_extract_benefits(self):
        """Test extracción de beneficios."""
        description = """
        Ofrecemos:
        - Trabajo remoto
        - Seguro médico
        - Vacaciones pagadas
        - Bonos por desempeño
        - Capacitación continua
        """
        
        result = self.analyzer._extract_benefits(description)
        
        self.assertIn('Remoto', result)
        self.assertIn('Vacaciones', result)
        self.assertIn('Bonus', result)
    
    def test_determine_company_type(self):
        """Test determinación de tipo de empresa."""
        # Test Startup
        description_startup = "Somos una startup innovadora"
        result = self.analyzer._determine_company_type(description_startup)
        self.assertEqual(result, 'startup')
        
        # Test Corporate
        description_corporate = "Empresa corporativa multinacional"
        result = self.analyzer._determine_company_type(description_corporate)
        self.assertEqual(result, 'corporate')
        
        # Test Fintech
        description_fintech = "Empresa fintech líder en el sector financiero"
        result = self.analyzer._determine_company_type(description_fintech)
        self.assertEqual(result, 'fintech')


class TestCVPersonalizationService(TestCase):
    """Tests para el servicio de personalización de CV."""
    
    def setUp(self):
        self.service = CVPersonalizationService()
        
        # Mock UserCV
        self.user_cv = Mock()
        self.user_cv.id = 1
        self.user_cv.skills_list = ['Python', 'Django', 'PostgreSQL', 'React']
        self.user_cv.skills_categories = {'backend': ['Python', 'Django'], 'frontend': ['React']}
        self.user_cv.parsed_text = """
        Juan Pérez
        Desarrollador Python con 3 años de experiencia
        Universidad de Buenos Aires - Ingeniería en Sistemas
        Proyecto: Sistema de gestión de inventario en Django
        """
        self.user_cv.original_file.name = 'cvs/2025/01/01/juan_cv.pdf'
        
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
        with patch.object(self.service, '_generate_personalized_cv') as mock_generate:
            mock_generate.return_value = {
                'resumen_profesional': 'Desarrollador Python con experiencia sólida',
                'habilidades_destacadas': ['Python', 'Django'],
                'experiencia_relevante': '3 años desarrollando aplicaciones web',
                'proyectos_relevantes': ['Sistema de gestión'],
                'educacion_adaptada': 'Ingeniería en Sistemas',
                'puntos_clave': ['Experiencia en Python', 'Conocimiento en Django']
            }
            
            result = self.service.personalize_cv_for_job(self.user_cv, self.job_posting)
            
            self.assertTrue(result['success'])
            self.assertIsNotNone(result['personalized_cv'])
            self.assertIsNotNone(result['job_requirements'])
            self.assertIsNotNone(result['cv_data'])
            self.assertGreater(result['match_score'], 0)
    
    def test_extract_cv_data(self):
        """Test extracción de datos del CV."""
        result = self.service._extract_cv_data(self.user_cv)
        
        self.assertEqual(result['skills'], ['Python', 'Django', 'PostgreSQL', 'React'])
        self.assertEqual(result['cv_id'], 1)
        self.assertEqual(result['experience_years'], 3)
        self.assertIn('Universidad', result['education'])
        self.assertIn('Sistema de gestión', result['projects'][0])
    
    def test_extract_experience_years(self):
        """Test extracción de años de experiencia."""
        parsed_text = "Desarrollador Python con 5 años de experiencia en desarrollo web"
        result = self.service._extract_experience_years(parsed_text)
        self.assertEqual(result, 5)
        
        parsed_text_no_years = "Desarrollador con experiencia en desarrollo"
        result = self.service._extract_experience_years(parsed_text_no_years)
        self.assertEqual(result, 0)
    
    def test_extract_education(self):
        """Test extracción de educación."""
        parsed_text = """
        Juan Pérez
        Desarrollador Python
        Universidad de Buenos Aires - Ingeniería en Sistemas
        """
        
        result = self.service._extract_education(parsed_text)
        self.assertIn('Universidad de Buenos Aires', result)
    
    def test_extract_projects(self):
        """Test extracción de proyectos."""
        parsed_text = """
        Juan Pérez
        Desarrollador Python
        Proyecto: Sistema de gestión de inventario
        Aplicación: Plataforma de e-commerce
        """
        
        result = self.service._extract_projects(parsed_text)
        self.assertGreater(len(result), 0)
        self.assertTrue(any('Sistema de gestión' in proj for proj in result))
    
    def test_create_cv_personalization_prompt(self):
        """Test creación de prompt para personalización."""
        cv_data = {
            'skills': ['Python', 'Django'],
            'experience_years': 3,
            'education': 'Ingeniería en Sistemas',
            'projects': ['Sistema de gestión']
        }
        
        job_requirements = {
            'title': 'Desarrollador Python',
            'experience_level': 'Senior',
            'required_skills': ['Python', 'Django'],
            'technologies': ['Python', 'Django', 'PostgreSQL'],
            'company_type': 'tech'
        }
        
        result = self.service._create_cv_personalization_prompt(cv_data, job_requirements)
        
        self.assertIn('Desarrollador Python', result)
        self.assertIn('Python', result)
        self.assertIn('Django', result)
        self.assertIn('JSON', result)
    
    def test_create_fallback_personalized_cv(self):
        """Test creación de CV personalizado de fallback."""
        cv_data = {
            'skills': ['Python', 'Django', 'PostgreSQL'],
            'experience_years': 3,
            'education': 'Ingeniería en Sistemas',
            'projects': ['Sistema de gestión']
        }
        
        job_requirements = {
            'required_skills': ['Python', 'Django'],
            'technologies': ['Python', 'Django'],
            'experience_level': 'Mid-level'
        }
        
        result = self.service._create_fallback_personalized_cv(cv_data, job_requirements)
        
        self.assertIsNotNone(result['resumen_profesional'])
        self.assertIn('Python', result['habilidades_destacadas'])
        self.assertIn('Django', result['habilidades_destacadas'])
        self.assertGreater(len(result['puntos_clave']), 0)
    
    def test_calculate_match_score(self):
        """Test cálculo de score de coincidencia."""
        cv_data = {
            'skills': ['Python', 'Django', 'PostgreSQL', 'React'],
            'experience_years': 3
        }
        
        job_requirements = {
            'required_skills': ['Python', 'Django', 'JavaScript'],
            'technologies': ['Python', 'Django', 'PostgreSQL'],
            'experience_level': 'Mid-level'
        }
        
        result = self.service._calculate_match_score(cv_data, job_requirements)
        
        self.assertGreater(result, 0)
        self.assertLessEqual(result, 100)
        # Debería tener buen score por coincidencias en habilidades y tecnologías
        self.assertGreater(result, 50)
    
    def test_personalize_cv_error_handling(self):
        """Test manejo de errores en personalización."""
        # Mock con error
        with patch.object(self.service, '_generate_personalized_cv') as mock_generate:
            mock_generate.side_effect = Exception("Error de IA")
            
            result = self.service.personalize_cv_for_job(self.user_cv, self.job_posting)
            
            self.assertFalse(result['success'])
            self.assertIn('error', result)
            self.assertIsNone(result['personalized_cv'])
            self.assertEqual(result['match_score'], 0)
