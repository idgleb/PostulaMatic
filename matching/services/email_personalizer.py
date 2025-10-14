"""
Servicio de personalización de emails basado en CV y puestos de trabajo.
Integra el servicio de IA con los datos reales del sistema.
"""

import logging
from typing import Dict, List, Optional, Tuple
from django.contrib.auth.models import User

from matching.models import UserCV, JobPosting, MatchScore, UserProfile
from .ai_service import ai_email_service, EmailContent
from .email_prompts import EmailPersonalizationData, EmailPromptTemplates

logger = logging.getLogger(__name__)


class CVDataExtractor:
    """Extractor de datos relevantes del CV para personalización."""
    
    @staticmethod
    def extract_cv_data(user_cv: UserCV) -> Dict:
        """
        Extrae datos estructurados del CV para personalización.
        
        Args:
            user_cv: Instancia de UserCV
            
        Returns:
            Dict con datos estructurados del CV
        """
        try:
            # Habilidades básicas
            skills = user_cv.skills_list
            skills_categories = user_cv.skills_categories
            
            # Extraer experiencia del texto parseado
            experience_info = CVDataExtractor._extract_experience_info(user_cv.parsed_text)
            
            # Extraer educación
            education_info = CVDataExtractor._extract_education_info(user_cv.parsed_text)
            
            # Extraer proyectos relevantes
            projects_info = CVDataExtractor._extract_projects_info(user_cv.parsed_text)
            
            return {
                'skills': skills,
                'skills_categories': skills_categories,
                'experience_years': experience_info.get('years', 0),
                'experience_summary': experience_info.get('summary', ''),
                'education': education_info,
                'projects': projects_info,
                'parsed_text': user_cv.parsed_text,
                'total_skills': len(skills),
                'cv_id': user_cv.id,
                'cv_filename': user_cv.original_file.name.split('/')[-1] if user_cv.original_file else 'CV'
            }
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del CV {user_cv.id}: {e}")
            return {
                'skills': user_cv.skills_list,
                'skills_categories': user_cv.skills_categories,
                'experience_years': 0,
                'experience_summary': '',
                'education': '',
                'projects': [],
                'parsed_text': user_cv.parsed_text or '',
                'total_skills': len(user_cv.skills_list),
                'cv_id': user_cv.id,
                'cv_filename': 'CV'
            }
    
    @staticmethod
    def _extract_experience_info(parsed_text: str) -> Dict:
        """Extrae información de experiencia del texto parseado."""
        if not parsed_text:
            return {'years': 0, 'summary': ''}
        
        text_lower = parsed_text.lower()
        
        # Buscar años de experiencia
        years = 0
        for keyword in ['años', 'years', 'experiencia']:
            if keyword in text_lower:
                # Buscar números cerca de la palabra experiencia
                words = text_lower.split()
                for i, word in enumerate(words):
                    if keyword in word and i > 0:
                        try:
                            # Buscar número en las palabras anteriores
                            for j in range(max(0, i-3), i):
                                if words[j].isdigit():
                                    years = int(words[j])
                                    break
                        except ValueError:
                            continue
        
        # Crear resumen de experiencia
        experience_keywords = ['desarrollador', 'developer', 'analista', 'ingeniero', 'programador']
        summary_parts = []
        
        # Buscar líneas que contengan experiencia y tecnologías
        lines = parsed_text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in experience_keywords):
                # Extraer tecnologías de la línea
                tech_keywords = ['python', 'java', 'javascript', 'django', 'react', 'angular', 'vue', 'node', 'sql', 'postgresql', 'mysql']
                found_techs = []
                for tech in tech_keywords:
                    if tech in line_lower:
                        found_techs.append(tech.title())
                
                # Crear resumen combinando rol y tecnologías
                role_parts = []
                for keyword in experience_keywords:
                    if keyword in line_lower:
                        # Buscar la palabra tal como aparece
                        words = line.split()
                        for word in words:
                            if keyword in word.lower():
                                role_parts.append(word)
                                break
                
                if role_parts and found_techs:
                    summary_parts.append(f"{role_parts[0]} {', '.join(found_techs[:2])}")
                elif role_parts:
                    summary_parts.append(role_parts[0])
                elif found_techs:
                    summary_parts.append(f"Desarrollador {', '.join(found_techs[:2])}")
                else:
                    summary_parts.append(line.strip())
                break
        
        summary = ', '.join(summary_parts[:3]) if summary_parts else ''
        
        return {
            'years': years,
            'summary': summary
        }
    
    @staticmethod
    def _extract_education_info(parsed_text: str) -> str:
        """Extrae información de educación del texto parseado."""
        if not parsed_text:
            return ''
        
        text_lower = parsed_text.lower()
        
        education_keywords = [
            'universidad', 'university', 'ingeniería', 'engineering',
            'licenciatura', 'degree', 'título', 'degree'
        ]
        
        for keyword in education_keywords:
            if keyword in text_lower:
                # Buscar la línea que contiene la educación
                lines = parsed_text.split('\n')
                for line in lines:
                    if keyword in line.lower():
                        return line.strip()
        
        return ''
    
    @staticmethod
    def _extract_projects_info(parsed_text: str) -> List[str]:
        """Extrae información de proyectos del texto parseado."""
        if not parsed_text:
            return []
        
        text_lower = parsed_text.lower()
        projects = []
        
        project_keywords = ['proyecto', 'project', 'aplicación', 'application', 'sistema', 'system']
        
        lines = parsed_text.split('\n')
        for line in lines:
            line_lower = line.lower()
            line_stripped = line.strip()
            
            # Filtrar líneas que no son proyectos (educación, experiencia, etc.)
            education_keywords = ['universidad', 'university', 'ingeniería', 'engineering', 'licenciatura', 'degree']
            experience_keywords = ['desarrollador', 'developer', 'analista', 'ingeniero', 'programador', 'años', 'experiencia']
            
            # Saltar líneas de educación o experiencia general
            if any(keyword in line_lower for keyword in education_keywords):
                continue
            if any(keyword in line_lower for keyword in experience_keywords) and not any(proj_keyword in line_lower for proj_keyword in ['proyecto', 'project']):
                continue
            
            # Filtrar líneas de encabezado como "Proyectos realizados:"
            if any(keyword in line_lower for keyword in project_keywords):
                if len(line_stripped) > 10 and not line_stripped.endswith(':'):
                    projects.append(line_stripped)
                # Si es una línea de encabezado, buscar las siguientes líneas
                elif line_stripped.endswith(':'):
                    continue  # Saltar líneas de encabezado
        
        # Si no encontramos proyectos específicos, buscar cualquier línea que contenga palabras clave
        if not projects:
            for line in lines:
                line_lower = line.lower()
                line_stripped = line.strip()
                # Excluir líneas de educación y experiencia general
                if (not any(keyword in line_lower for keyword in education_keywords) and
                    not any(keyword in line_lower for keyword in experience_keywords) and
                    any(keyword in line_lower for keyword in project_keywords) and 
                    len(line_stripped) > 10 and not line_stripped.endswith(':')):
                    projects.append(line_stripped)
        
        return projects[:3]  # Máximo 3 proyectos


class JobDataExtractor:
    """Extractor de datos relevantes del puesto de trabajo."""
    
    @staticmethod
    def extract_job_data(job_posting: JobPosting) -> Dict:
        """
        Extrae datos estructurados del puesto de trabajo.
        
        Args:
            job_posting: Instancia de JobPosting
            
        Returns:
            Dict con datos estructurados del puesto
        """
        try:
            description = job_posting.description
            
            # Extraer tecnologías requeridas
            required_skills = JobDataExtractor._extract_required_skills(description)
            
            # Extraer nivel de experiencia requerido
            experience_level = JobDataExtractor._extract_experience_level(description)
            
            # Extraer tipo de trabajo
            work_type = JobDataExtractor._extract_work_type(description)
            
            # Extraer ubicación
            location = JobDataExtractor._extract_location(description)
            
            # Extraer beneficios
            benefits = JobDataExtractor._extract_benefits(description)
            
            return {
                'title': job_posting.title,
                'description': description,
                'required_skills': required_skills,
                'experience_level': experience_level,
                'work_type': work_type,
                'location': location,
                'benefits': benefits,
                'email': job_posting.email,
                'external_id': job_posting.external_id,
                'job_id': job_posting.id
            }
            
        except Exception as e:
            logger.error(f"Error extrayendo datos del puesto {job_posting.id}: {e}")
            return {
                'title': job_posting.title,
                'description': job_posting.description,
                'required_skills': [],
                'experience_level': '',
                'work_type': '',
                'location': '',
                'benefits': [],
                'email': job_posting.email,
                'external_id': job_posting.external_id,
                'job_id': job_posting.id
            }
    
    @staticmethod
    def _extract_required_skills(description: str) -> List[str]:
        """Extrae habilidades requeridas de la descripción."""
        if not description:
            return []
        
        description_lower = description.lower()
        
        # Lista de tecnologías comunes
        tech_skills = [
            'python', 'javascript', 'java', 'c#', 'php', 'ruby', 'go', 'rust',
            'django', 'flask', 'fastapi', 'react', 'angular', 'vue', 'node.js',
            'postgresql', 'mysql', 'mongodb', 'redis', 'sqlite',
            'docker', 'kubernetes', 'aws', 'azure', 'gcp',
            'git', 'jenkins', 'ci/cd', 'agile', 'scrum'
        ]
        
        found_skills = []
        for skill in tech_skills:
            if skill in description_lower:
                found_skills.append(skill.title())
        
        return found_skills[:10]  # Máximo 10 habilidades
    
    @staticmethod
    def _extract_experience_level(description: str) -> str:
        """Extrae nivel de experiencia requerido."""
        if not description:
            return 'No especificado'
        
        description_lower = description.lower()
        
        # Buscar patrones más específicos
        senior_patterns = ['senior', 'sr', 'lead', 'principal', 'experto', 'avanzado']
        junior_patterns = ['junior', 'jr', 'trainee', 'intern', 'inicial', 'entry-level']
        mid_patterns = ['mid', 'middle', 'intermedio', 'semi-senior']
        
        # Verificar en orden de prioridad
        if any(word in description_lower for word in senior_patterns):
            return 'Senior'
        elif any(word in description_lower for word in junior_patterns):
            return 'Junior'
        elif any(word in description_lower for word in mid_patterns):
            return 'Mid-level'
        
        # Buscar por años de experiencia
        import re
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
    def _extract_work_type(description: str) -> str:
        """Extrae tipo de trabajo."""
        if not description:
            return 'No especificado'
        
        description_lower = description.lower()
        
        # Buscar patrones más específicos
        remote_patterns = ['remoto', 'remote', 'home office', 'trabajo remoto', 'trabajo en casa']
        onsite_patterns = ['presencial', 'office', 'oficina', 'trabajo presencial', 'en oficina']
        hybrid_patterns = ['híbrido', 'hybrid', 'mixto', 'combinado', 'parcial', 'modalidad híbrida']
        
        # Verificar en orden de prioridad
        if any(word in description_lower for word in hybrid_patterns):
            return 'Híbrido'
        elif any(word in description_lower for word in remote_patterns):
            return 'Remoto'
        elif any(word in description_lower for word in onsite_patterns):
            return 'Presencial'
        
        return 'No especificado'
    
    @staticmethod
    def _extract_location(description: str) -> str:
        """Extrae ubicación del trabajo."""
        if not description:
            return ''
        
        # Buscar patrones de ubicación
        import re
        
        # Patrones comunes de ubicación
        location_patterns = [
            r'(?:Buenos Aires|CABA|Capital Federal|Córdoba|Rosario|Mendoza|Barcelona|Madrid|Lima|Santiago)',
            r'(?:en|ubicado en|localizado en)\s+([A-Z][a-záéíóúñ\s]+)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                # Si el patrón tiene un grupo de captura, usarlo
                if match.groups():
                    return match.group(1).strip()
                else:
                    # Si no, usar toda la coincidencia
                    return match.group(0).strip()
        
        return ''
    
    @staticmethod
    def _extract_benefits(description: str) -> List[str]:
        """Extrae beneficios mencionados."""
        if not description:
            return []
        
        description_lower = description.lower()
        
        benefits_keywords = [
            'flexible', 'home office', 'remoto', 'vacaciones', 'vacation',
            'seguro médico', 'health insurance', 'gym', 'bonus', 'bono',
            'capacitación', 'training', 'cursos', 'courses'
        ]
        
        found_benefits = []
        for benefit in benefits_keywords:
            if benefit in description_lower:
                found_benefits.append(benefit.title())
        
        return found_benefits[:5]  # Máximo 5 beneficios


class EmailPersonalizationService:
    """Servicio principal para personalización de emails."""
    
    def __init__(self):
        self.cv_extractor = CVDataExtractor()
        self.job_extractor = JobDataExtractor()
    
    def generate_personalized_email(
        self,
        user: User,
        user_cv: UserCV,
        job_posting: JobPosting,
        match_score: Optional[MatchScore] = None,
        template_type: str = 'base',
        custom_instructions: str = '',
        ai_provider: str = 'openai'
    ) -> EmailContent:
        """
        Genera un email personalizado basado en CV y puesto de trabajo.
        
        Args:
            user: Usuario que postula
            user_cv: CV del usuario
            job_posting: Puesto de trabajo
            match_score: Score de coincidencia (opcional)
            template_type: Tipo de template a usar
            custom_instructions: Instrucciones personalizadas
            ai_provider: Proveedor de IA a usar
            
        Returns:
            EmailContent generado
        """
        try:
            # Extraer datos del CV
            cv_data = self.cv_extractor.extract_cv_data(user_cv)
            
            # Extraer datos del puesto
            job_data = self.job_extractor.extract_job_data(job_posting)
            
            # Obtener perfil del usuario
            user_profile_data = self._get_user_profile_data(user)
            
            # Determinar template más apropiado
            optimal_template = self._select_optimal_template(
                cv_data, job_data, template_type
            )
            
            # Crear datos de personalización
            personalization_data = EmailPersonalizationData(
                job_description=job_data['description'],
                cv_skills=cv_data,
                user_profile=user_profile_data,
                template_type=optimal_template,
                custom_instructions=custom_instructions,
                company_info=self._extract_company_info(job_data),
                job_metadata={
                    'location': job_data['location'],
                    'work_type': job_data['work_type'],
                    'experience_level': job_data['experience_level'],
                    'match_score': match_score.score if match_score else 0,
                    'job_id': job_data['job_id']
                }
            )
            
            # Generar prompt personalizado
            custom_prompt = personalization_data.build_prompt()
            
            # Generar email con IA
            result = ai_email_service.generate_email(
                job_description=job_data['description'],
                cv_skills=cv_data,
                user_profile=user_profile_data,
                provider=ai_provider,
                custom_prompt=custom_prompt
            )
            
            # Log del resultado
            logger.info(
                f"Email personalizado generado para usuario {user.email}, "
                f"CV {user_cv.id}, puesto {job_posting.id}, "
                f"proveedor {result.provider}, template {optimal_template}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error generando email personalizado: {e}")
            return EmailContent(
                subject="Error generando email",
                body=f"Hubo un error generando el email personalizado: {str(e)}",
                provider=ai_provider,
                model="error",
                error=str(e)
            )
    
    def _get_user_profile_data(self, user: User) -> Dict:
        """Obtiene datos del perfil del usuario."""
        try:
            profile = user.profile
            return {
                'display_name': profile.display_name or user.first_name or user.username,
                'email': user.email,
                'user_id': user.id
            }
        except UserProfile.DoesNotExist:
            return {
                'display_name': user.first_name or user.username,
                'email': user.email,
                'user_id': user.id
            }
    
    def _select_optimal_template(
        self, 
        cv_data: Dict, 
        job_data: Dict, 
        requested_template: str
    ) -> str:
        """Selecciona el template más apropiado basado en el contexto."""
        
        # Si se especifica un template, usarlo
        if requested_template != 'base':
            return requested_template
        
        # Lógica para seleccionar template óptimo
        
        # Si es startup (empresa pequeña), usar template startup (prioridad alta)
        if len(job_data['description']) < 500:  # Descripciones cortas suelen ser startups
            return 'startup'
        
        # Si es puesto técnico específico con descripción detallada, usar template technical
        technical_keywords = ['desarrollador', 'developer', 'programador', 'ingeniero']
        if (any(keyword in job_data['title'].lower() for keyword in technical_keywords) and 
            len(job_data['description']) >= 500):  # Solo si la descripción es detallada
            return 'technical'
        
        # Si es empresa grande (descripción muy larga), usar corporate
        if len(job_data['description']) > 2000:
            return 'corporate'
        
        # Si el usuario tiene mucha experiencia, usar formal
        if cv_data.get('experience_years', 0) > 5:
            return 'formal'
        
        # Por defecto, usar creative
        return 'creative'
    
    def _extract_company_info(self, job_data: Dict) -> Dict:
        """Extrae información de la empresa del puesto."""
        # Por ahora, información básica
        # En el futuro se podría extraer de la descripción o usar APIs
        return {
            'name': '',  # Se podría extraer del email o descripción
            'industry': self._guess_industry(job_data['description'])
        }
    
    def _guess_industry(self, description: str) -> str:
        """Intenta adivinar la industria basada en la descripción."""
        if not description:
            return ''
        
        description_lower = description.lower()
        
        industries = {
            'Fintech': ['fintech', 'financiero', 'bancario', 'finanzas'],
            'E-Commerce': ['ecommerce', 'e-commerce', 'retail', 'ventas online'],
            'Healthcare': ['salud', 'healthcare', 'médico', 'hospital'],
            'Education': ['educación', 'education', 'universidad', 'colegio'],
            'Gaming': ['gaming', 'juegos', 'videojuegos', 'game'],
            'Technology': ['software', 'saas', 'plataforma', 'sistema', 'desarrollo', 'programación']
        }
        
        for industry, keywords in industries.items():
            if any(keyword in description_lower for keyword in keywords):
                return industry
        
        return 'Technology'  # Por defecto


# Instancia global del servicio
email_personalization_service = EmailPersonalizationService()

