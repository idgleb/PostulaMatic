"""
Servicio de personalización de CV basado en requisitos del puesto.
Genera versiones personalizadas del CV original destacando habilidades relevantes.
"""

import logging
import os
import tempfile
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re

from django.contrib.auth.models import User
from django.core.files.base import ContentFile

from matching.models import UserCV, JobPosting
from .ai_service import ai_email_service

logger = logging.getLogger(__name__)


class JobRequirementsAnalyzer:
    """Analizador de requisitos del puesto de trabajo."""
    
    @staticmethod
    def analyze_job_requirements(job_posting: JobPosting) -> Dict:
        """
        Analiza los requisitos del puesto y extrae información clave.
        
        Args:
            job_posting: Instancia de JobPosting
            
        Returns:
            Dict con requisitos analizados
        """
        try:
            description = job_posting.description
            
            # Extraer habilidades requeridas
            required_skills = JobRequirementsAnalyzer._extract_required_skills(description)
            
            # Extraer nivel de experiencia requerido
            experience_level = JobRequirementsAnalyzer._extract_experience_level(description)
            
            # Extraer tecnologías específicas
            technologies = JobRequirementsAnalyzer._extract_technologies(description)
            
            # Extraer responsabilidades clave
            key_responsibilities = JobRequirementsAnalyzer._extract_responsibilities(description)
            
            # Extraer beneficios y características del puesto
            benefits = JobRequirementsAnalyzer._extract_benefits(description)
            
            # Determinar tipo de empresa (startup, corporate, etc.)
            company_type = JobRequirementsAnalyzer._determine_company_type(description)
            
            return {
                'required_skills': required_skills,
                'experience_level': experience_level,
                'technologies': technologies,
                'key_responsibilities': key_responsibilities,
                'benefits': benefits,
                'company_type': company_type,
                'title': job_posting.title,
                'description': description,
                'job_id': job_posting.id
            }
            
        except Exception as e:
            logger.error(f"Error analizando requisitos del puesto {job_posting.id}: {e}")
            return {
                'required_skills': [],
                'experience_level': '',
                'technologies': [],
                'key_responsibilities': [],
                'benefits': [],
                'company_type': 'unknown',
                'title': job_posting.title,
                'description': job_posting.description,
                'job_id': job_posting.id
            }
    
    @staticmethod
    def _extract_required_skills(description: str) -> List[str]:
        """Extrae habilidades requeridas de la descripción."""
        if not description:
            return []
        
        description_lower = description.lower()
        
        # Lista de habilidades técnicas comunes
        tech_skills = [
            'python', 'javascript', 'java', 'c#', 'php', 'ruby', 'go', 'rust', 'kotlin', 'swift',
            'django', 'flask', 'fastapi', 'react', 'angular', 'vue', 'node.js', 'express',
            'postgresql', 'mysql', 'mongodb', 'redis', 'sqlite', 'elasticsearch',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'terraform',
            'git', 'jenkins', 'ci/cd', 'agile', 'scrum', 'devops',
            'machine learning', 'ai', 'data science', 'analytics', 'big data',
            'rest api', 'graphql', 'microservices', 'serverless'
        ]
        
        found_skills = []
        for skill in tech_skills:
            if skill in description_lower:
                found_skills.append(skill.title())
        
        return found_skills[:15]  # Máximo 15 habilidades
    
    @staticmethod
    def _extract_experience_level(description: str) -> str:
        """Extrae nivel de experiencia requerido."""
        if not description:
            return 'No especificado'
        
        description_lower = description.lower()
        
        # Patrones para diferentes niveles
        senior_patterns = ['senior', 'sr', 'lead', 'principal', 'experto', 'avanzado', '5+ años', '5+ years']
        junior_patterns = ['junior', 'jr', 'trainee', 'intern', 'inicial', 'entry-level', '1-2 años', '1-2 years']
        mid_patterns = ['mid', 'middle', 'intermedio', 'semi-senior', '3-4 años', '3-4 years']
        
        # Verificar en orden de prioridad
        if any(pattern in description_lower for pattern in senior_patterns):
            return 'Senior'
        elif any(pattern in description_lower for pattern in junior_patterns):
            return 'Junior'
        elif any(pattern in description_lower for pattern in mid_patterns):
            return 'Mid-level'
        
        # Buscar por años de experiencia
        years_match = re.search(r'(\d+)\+?\s*(?:años?|years?)\s*(?:de\s*)?experiencia', description_lower)
        if years_match:
            years = int(years_match.group(1))
            if years >= 5:
                return 'Senior'
            elif years >= 2:
                return 'Mid-level'
            else:
                return 'Junior'
        
        return 'No especificado'
    
    @staticmethod
    def _extract_technologies(description: str) -> List[str]:
        """Extrae tecnologías específicas mencionadas."""
        if not description:
            return []
        
        description_lower = description.lower()
        
        # Tecnologías específicas
        technologies = [
            'python', 'javascript', 'java', 'c#', 'php', 'ruby', 'go', 'rust',
            'react', 'angular', 'vue', 'svelte', 'next.js', 'nuxt.js',
            'django', 'flask', 'fastapi', 'spring', 'laravel', 'rails',
            'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
            'docker', 'kubernetes', 'terraform', 'ansible',
            'aws', 'azure', 'gcp', 'firebase', 'vercel',
            'git', 'github', 'gitlab', 'bitbucket',
            'jenkins', 'circleci', 'travis', 'github actions'
        ]
        
        found_technologies = []
        for tech in technologies:
            if tech in description_lower:
                found_technologies.append(tech.title())
        
        return found_technologies[:10]  # Máximo 10 tecnologías
    
    @staticmethod
    def _extract_responsibilities(description: str) -> List[str]:
        """Extrae responsabilidades clave del puesto."""
        if not description:
            return []
        
        # Buscar secciones de responsabilidades
        responsibilities = []
        lines = description.split('\n')
        
        in_responsibilities_section = False
        for line in lines:
            line_lower = line.lower()
            line_stripped = line.strip()
            
            # Detectar inicio de sección de responsabilidades
            if any(keyword in line_lower for keyword in ['responsabilidades', 'responsibilities', 'funciones', 'tareas']):
                in_responsibilities_section = True
                continue
            
            # Detectar fin de sección
            if in_responsibilities_section and any(keyword in line_lower for keyword in ['requisitos', 'requirements', 'beneficios', 'benefits']):
                break
            
            # Extraer responsabilidades
            if in_responsibilities_section and line_stripped and len(line_stripped) > 10:
                # Filtrar viñetas y numeración
                clean_line = re.sub(r'^[\s\-\*\•\d\.\)]+', '', line_stripped)
                if clean_line and len(clean_line) > 10:
                    responsibilities.append(clean_line)
        
        return responsibilities[:8]  # Máximo 8 responsabilidades
    
    @staticmethod
    def _extract_benefits(description: str) -> List[str]:
        """Extrae beneficios mencionados."""
        if not description:
            return []
        
        description_lower = description.lower()
        
        benefits = []
        benefit_keywords = [
            'remoto', 'remote', 'home office', 'flexibilidad', 'flexible',
            'vacaciones', 'vacation', 'seguro médico', 'health insurance',
            'bonus', 'bono', 'comisiones', 'comissions', 'stock options',
            'capacitación', 'training', 'desarrollo', 'development',
            'equipo joven', 'young team', 'startup', 'crecimiento', 'growth'
        ]
        
        # Mapeo de beneficios para capitalización correcta
        benefit_mapping = {
            'remoto': 'Remoto',
            'remote': 'Remoto',
            'vacaciones': 'Vacaciones',
            'vacation': 'Vacaciones',
            'seguro médico': 'Seguro Médico',
            'health insurance': 'Seguro Médico',
            'bonus': 'Bonus',
            'bono': 'Bonus',
            'comisiones': 'Comisiones',
            'comissions': 'Comisiones',
            'stock options': 'Stock Options',
            'capacitación': 'Capacitación',
            'training': 'Capacitación',
            'desarrollo': 'Desarrollo',
            'development': 'Desarrollo',
            'equipo joven': 'Equipo Joven',
            'young team': 'Equipo Joven',
            'startup': 'Startup',
            'crecimiento': 'Crecimiento',
            'growth': 'Crecimiento',
            'flexibilidad': 'Flexibilidad',
            'flexible': 'Flexibilidad'
        }
        
        for benefit in benefit_keywords:
            if benefit in description_lower:
                mapped_benefit = benefit_mapping.get(benefit, benefit.title())
                if mapped_benefit not in benefits:  # Evitar duplicados
                    benefits.append(mapped_benefit)
        
        return benefits[:5]  # Máximo 5 beneficios
    
    @staticmethod
    def _determine_company_type(description: str) -> str:
        """Determina el tipo de empresa basado en la descripción."""
        if not description:
            return 'unknown'
        
        description_lower = description.lower()
        
        # Patrones para diferentes tipos de empresa
        if any(keyword in description_lower for keyword in ['startup', 'innovación', 'innovación', 'disruptivo']):
            return 'startup'
        elif any(keyword in description_lower for keyword in ['corporativo', 'corporation', 'multinacional', 'enterprise']):
            return 'corporate'
        elif any(keyword in description_lower for keyword in ['consultora', 'consulting', 'cliente', 'client']):
            return 'consulting'
        elif any(keyword in description_lower for keyword in ['fintech', 'financiero', 'bancario']):
            return 'fintech'
        elif any(keyword in description_lower for keyword in ['ecommerce', 'e-commerce', 'retail']):
            return 'ecommerce'
        else:
            return 'tech'


class CVPersonalizationService:
    """Servicio principal de personalización de CV."""
    
    def __init__(self):
        self.analyzer = JobRequirementsAnalyzer()
    
    def personalize_cv_for_job(
        self, 
        user_cv: UserCV, 
        job_posting: JobPosting,
        user_profile: Optional[Dict] = None
    ) -> Dict:
        """
        Personaliza un CV para un puesto específico.
        
        Args:
            user_cv: CV del usuario
            job_posting: Puesto de trabajo
            user_profile: Perfil del usuario (opcional)
            
        Returns:
            Dict con información de personalización
        """
        try:
            # Analizar requisitos del puesto
            job_requirements = self.analyzer.analyze_job_requirements(job_posting)
            
            # Extraer datos del CV
            cv_data = self._extract_cv_data(user_cv)
            
            # Generar CV personalizado usando IA
            personalized_cv = self._generate_personalized_cv(
                cv_data, job_requirements, user_profile
            )
            
            # Crear archivo personalizado
            personalized_file = self._create_personalized_file(
                user_cv, personalized_cv, job_posting
            )
            
            return {
                'success': True,
                'personalized_cv': personalized_cv,
                'personalized_file': personalized_file,
                'job_requirements': job_requirements,
                'cv_data': cv_data,
                'match_score': self._calculate_match_score(cv_data, job_requirements)
            }
            
        except Exception as e:
            logger.error(f"Error personalizando CV {user_cv.id} para puesto {job_posting.id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'personalized_cv': None,
                'personalized_file': None,
                'job_requirements': {},
                'cv_data': {},
                'match_score': 0
            }
    
    def _extract_cv_data(self, user_cv: UserCV) -> Dict:
        """Extrae datos estructurados del CV."""
        try:
            return {
                'skills': user_cv.skills_list,
                'skills_categories': user_cv.skills_categories,
                'parsed_text': user_cv.parsed_text,
                'experience_years': self._extract_experience_years(user_cv.parsed_text),
                'education': self._extract_education(user_cv.parsed_text),
                'projects': self._extract_projects(user_cv.parsed_text),
                'cv_id': user_cv.id,
                'filename': user_cv.original_file.name.split('/')[-1] if user_cv.original_file else 'CV'
            }
        except Exception as e:
            logger.error(f"Error extrayendo datos del CV {user_cv.id}: {e}")
            return {
                'skills': user_cv.skills_list,
                'skills_categories': user_cv.skills_categories,
                'parsed_text': user_cv.parsed_text or '',
                'experience_years': 0,
                'education': '',
                'projects': [],
                'cv_id': user_cv.id,
                'filename': 'CV'
            }
    
    def _extract_experience_years(self, parsed_text: str) -> int:
        """Extrae años de experiencia del texto parseado."""
        if not parsed_text:
            return 0
        
        # Buscar patrones de años de experiencia
        years_match = re.search(r'(\d+)\+?\s*(?:años?|years?)\s*(?:de\s*)?experiencia', parsed_text.lower())
        if years_match:
            return int(years_match.group(1))
        
        return 0
    
    def _extract_education(self, parsed_text: str) -> str:
        """Extrae información de educación."""
        if not parsed_text:
            return ''
        
        education_keywords = ['universidad', 'university', 'ingeniería', 'engineering', 'licenciatura', 'degree']
        
        lines = parsed_text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in education_keywords):
                return line.strip()
        
        return ''
    
    def _extract_projects(self, parsed_text: str) -> List[str]:
        """Extrae proyectos del CV."""
        if not parsed_text:
            return []
        
        projects = []
        project_keywords = ['proyecto', 'project', 'aplicación', 'application', 'sistema', 'system']
        
        lines = parsed_text.split('\n')
        for line in lines:
            line_lower = line.lower()
            line_stripped = line.strip()
            
            # Filtrar líneas de educación y experiencia general
            education_keywords = ['universidad', 'university', 'ingeniería', 'engineering']
            experience_keywords = ['desarrollador', 'developer', 'analista', 'ingeniero', 'programador', 'años', 'experiencia']
            
            if any(keyword in line_lower for keyword in education_keywords):
                continue
            if any(keyword in line_lower for keyword in experience_keywords) and not any(proj_keyword in line_lower for proj_keyword in ['proyecto', 'project']):
                continue
            
            if any(keyword in line_lower for keyword in project_keywords):
                if len(line_stripped) > 10 and not line_stripped.endswith(':'):
                    projects.append(line_stripped)
        
        return projects[:3]  # Máximo 3 proyectos
    
    def _generate_personalized_cv(
        self, 
        cv_data: Dict, 
        job_requirements: Dict, 
        user_profile: Optional[Dict] = None
    ) -> Dict:
        """Genera CV personalizado usando IA."""
        try:
            # Crear prompt para personalización de CV
            prompt = self._create_cv_personalization_prompt(cv_data, job_requirements, user_profile)
            
            # Usar IA para generar CV personalizado
            result = ai_email_service.generate_email_content(
                job_description=job_requirements['description'],
                cv_skills=cv_data,
                user_profile=user_profile or {},
                custom_prompt=prompt
            )
            
            if result.error:
                raise Exception(f"Error de IA: {result.error}")
            
            # Parsear respuesta de IA
            personalized_content = self._parse_ai_cv_response(result.body)
            
            return personalized_content
            
        except Exception as e:
            logger.error(f"Error generando CV personalizado: {e}")
            # Fallback: usar datos originales con mejoras básicas
            return self._create_fallback_personalized_cv(cv_data, job_requirements)
    
    def _create_cv_personalization_prompt(
        self, 
        cv_data: Dict, 
        job_requirements: Dict, 
        user_profile: Optional[Dict] = None
    ) -> str:
        """Crea prompt específico para personalización de CV."""
        
        prompt = f"""
Eres un experto en recursos humanos y redacción de CVs. Tu tarea es personalizar un CV para destacar las habilidades y experiencia más relevantes para un puesto específico.

INFORMACIÓN DEL PUESTO:
- Título: {job_requirements['title']}
- Nivel: {job_requirements['experience_level']}
- Habilidades requeridas: {', '.join(job_requirements['required_skills'])}
- Tecnologías: {', '.join(job_requirements['technologies'])}
- Tipo de empresa: {job_requirements['company_type']}

INFORMACIÓN DEL CV ACTUAL:
- Habilidades: {', '.join(cv_data['skills'])}
- Años de experiencia: {cv_data['experience_years']}
- Educación: {cv_data['education']}
- Proyectos: {', '.join(cv_data['projects'])}

TAREA:
Personaliza el CV para este puesto específico. Responde en formato JSON con las siguientes secciones:

{{
    "resumen_profesional": "Resumen de 2-3 líneas destacando experiencia relevante para el puesto",
    "habilidades_destacadas": ["Lista de habilidades más relevantes para el puesto"],
    "experiencia_relevante": "Descripción de experiencia enfocada en el puesto",
    "proyectos_relevantes": ["Lista de proyectos más relevantes"],
    "educacion_adaptada": "Información de educación adaptada al contexto",
    "puntos_clave": ["3-4 puntos clave que lo hacen ideal para el puesto"]
}}

IMPORTANTE:
- Destaca las habilidades que coinciden con los requisitos
- Adapta el lenguaje al tipo de empresa y nivel del puesto
- Mantén información veraz pero enfócate en lo más relevante
- Usa un tono profesional apropiado para el nivel del puesto
"""

        return prompt
    
    def _parse_ai_cv_response(self, ai_response: str) -> Dict:
        """Parsea la respuesta de IA para extraer CV personalizado."""
        try:
            import json
            
            # Intentar parsear como JSON
            if ai_response.strip().startswith('{'):
                return json.loads(ai_response)
            
            # Si no es JSON, crear estructura básica
            return {
                'resumen_profesional': ai_response[:200] + '...' if len(ai_response) > 200 else ai_response,
                'habilidades_destacadas': [],
                'experiencia_relevante': ai_response,
                'proyectos_relevantes': [],
                'educacion_adaptada': '',
                'puntos_clave': []
            }
            
        except Exception as e:
            logger.error(f"Error parseando respuesta de IA: {e}")
            return {
                'resumen_profesional': ai_response[:200] + '...' if len(ai_response) > 200 else ai_response,
                'habilidades_destacadas': [],
                'experiencia_relevante': ai_response,
                'proyectos_relevantes': [],
                'educacion_adaptada': '',
                'puntos_clave': []
            }
    
    def _create_fallback_personalized_cv(self, cv_data: Dict, job_requirements: Dict) -> Dict:
        """Crea CV personalizado básico sin IA como fallback."""
        
        # Destacar habilidades que coinciden
        matching_skills = []
        for skill in cv_data['skills']:
            if any(req_skill.lower() in skill.lower() for req_skill in job_requirements['required_skills']):
                matching_skills.append(skill)
        
        return {
            'resumen_profesional': f"Profesional con {cv_data['experience_years']} años de experiencia en desarrollo de software.",
            'habilidades_destacadas': matching_skills[:5],
            'experiencia_relevante': f"Experiencia sólida en desarrollo con tecnologías modernas.",
            'proyectos_relevantes': cv_data['projects'][:2],
            'educacion_adaptada': cv_data['education'],
            'puntos_clave': [
                f"{cv_data['experience_years']} años de experiencia",
                f"Experto en {', '.join(matching_skills[:3])}" if matching_skills else "Habilidades técnicas sólidas",
                "Experiencia en proyectos complejos"
            ]
        }
    
    def _create_personalized_file(
        self, 
        user_cv: UserCV, 
        personalized_cv: Dict, 
        job_posting: JobPosting
    ) -> Optional[str]:
        """Crea archivo personalizado del CV."""
        try:
            # Por ahora, retornamos el archivo original
            # En el futuro se puede implementar generación de PDF personalizado
            if user_cv.original_file:
                return user_cv.original_file.path
            
            return None
            
        except Exception as e:
            logger.error(f"Error creando archivo personalizado: {e}")
            return None
    
    def _calculate_match_score(self, cv_data: Dict, job_requirements: Dict) -> int:
        """Calcula score de coincidencia entre CV y puesto."""
        try:
            score = 0
            
            # Coincidencia de habilidades (40% del score)
            matching_skills = 0
            for skill in cv_data['skills']:
                if any(req_skill.lower() in skill.lower() for req_skill in job_requirements['required_skills']):
                    matching_skills += 1
            
            if job_requirements['required_skills']:
                skill_score = (matching_skills / len(job_requirements['required_skills'])) * 40
                score += min(skill_score, 40)
            
            # Coincidencia de nivel de experiencia (30% del score)
            cv_years = cv_data['experience_years']
            required_level = job_requirements['experience_level']
            
            if required_level == 'Junior' and cv_years <= 3:
                score += 30
            elif required_level == 'Mid-level' and 2 <= cv_years <= 5:
                score += 30
            elif required_level == 'Senior' and cv_years >= 4:
                score += 30
            
            # Coincidencia de tecnologías (30% del score)
            matching_techs = 0
            for tech in job_requirements['technologies']:
                if any(tech.lower() in skill.lower() for skill in cv_data['skills']):
                    matching_techs += 1
            
            if job_requirements['technologies']:
                tech_score = (matching_techs / len(job_requirements['technologies'])) * 30
                score += min(tech_score, 30)
            
            return min(int(score), 100)
            
        except Exception as e:
            logger.error(f"Error calculando match score: {e}")
            return 0


# Instancia global del servicio
cv_personalization_service = CVPersonalizationService()
