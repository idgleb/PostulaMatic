"""
Servicio para calcular coincidencias entre CVs y ofertas de trabajo.
Implementa diferentes estrategias de matching intercambiables.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from abc import ABC, abstractmethod

from ..models import UserCV, JobPosting, MatchScore, UserProfile
from .skills_extractor import skills_extractor

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Resultado de un cálculo de matching."""
    score: float  # 0-100
    details: Dict[str, Any]
    confidence: float  # 0-1
    matched_skills: List[str]
    missing_skills: List[str]
    extra_skills: List[str]


class MatchingStrategy(ABC):
    """Estrategia base para cálculo de matching."""
    
    @abstractmethod
    def calculate_match(self, cv_skills: Dict[str, Any], job_description: str, 
                       required_skills: Optional[List[str]] = None) -> MatchResult:
        """Calcula el score de matching entre CV y oferta."""
        pass


class BasicSkillsMatchingStrategy(MatchingStrategy):
    """Estrategia básica de matching por coincidencia de habilidades."""
    
    def __init__(self, skill_weight: float = 1.0, bonus_skills_weight: float = 0.5):
        self.skill_weight = skill_weight
        self.bonus_skills_weight = bonus_skills_weight
    
    def calculate_match(self, cv_skills: Dict[str, Any], job_description: str, 
                       required_skills: Optional[List[str]] = None) -> MatchResult:
        """
        Calcula matching básico basado en coincidencia de habilidades.
        
        Args:
            cv_skills: Habilidades del CV
            job_description: Descripción del trabajo
            required_skills: Habilidades requeridas explícitas (opcional)
            
        Returns:
            Resultado del matching
        """
        # Extraer habilidades de la descripción del trabajo
        job_skills_data = skills_extractor.extract_skills(job_description, min_confidence=0.5)
        job_skills = set(job_skills_data['skills'])
        
        # Obtener habilidades del CV
        cv_skill_list = cv_skills.get('skills', [])
        cv_skills_set = set(cv_skill_list)
        
        # Si se proporcionan habilidades requeridas, usarlas
        if required_skills:
            job_skills.update(required_skills)
        
        # Calcular intersección y diferencias
        matched_skills = list(cv_skills_set.intersection(job_skills))
        missing_skills = list(job_skills - cv_skills_set)
        extra_skills = list(cv_skills_set - job_skills)
        
        # Calcular score base
        if not job_skills:
            # Si no hay habilidades en el trabajo, score neutro
            base_score = 50.0
            confidence = 0.3
        else:
            # Score basado en porcentaje de habilidades coincidentes
            match_ratio = len(matched_skills) / len(job_skills)
            base_score = match_ratio * 100
            
            # Bonus por habilidades extra
            if len(extra_skills) > 0:
                extra_bonus = min(len(extra_skills) * self.bonus_skills_weight, 20)
                base_score = min(base_score + extra_bonus, 100)
            
            # Confianza basada en número de coincidencias
            confidence = min(len(matched_skills) / max(len(job_skills), 1), 1.0)
        
        # Penalizar si faltan habilidades críticas
        critical_skills = self._identify_critical_skills(job_skills)
        missing_critical = set(missing_skills).intersection(critical_skills)
        if missing_critical:
            penalty = len(missing_critical) * 15
            base_score = max(base_score - penalty, 0)
            confidence = max(confidence - 0.2, 0.1)
        
        # Crear detalles del matching
        details = {
            'strategy': 'basic_skills',
            'job_skills_count': len(job_skills),
            'cv_skills_count': len(cv_skill_list),
            'matched_count': len(matched_skills),
            'missing_count': len(missing_skills),
            'extra_count': len(extra_skills),
            'critical_missing': list(missing_critical),
            'job_categories': job_skills_data.get('categories', {}),
            'cv_categories': cv_skills.get('categories', {})
        }
        
        return MatchResult(
            score=round(base_score, 1),
            details=details,
            confidence=round(confidence, 2),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            extra_skills=extra_skills
        )
    
    def _identify_critical_skills(self, job_skills: set) -> set:
        """
        Identifica habilidades críticas basándose en patrones comunes.
        
        Args:
            job_skills: Conjunto de habilidades del trabajo
            
        Returns:
            Conjunto de habilidades consideradas críticas
        """
        critical_patterns = [
            # Lenguajes de programación
            r'^(python|java|javascript|typescript|c\+\+|c#|php|ruby|go|rust|kotlin|swift)$',
            # Frameworks principales
            r'^(react|angular|vue|django|flask|spring|laravel|rails|express)$',
            # Bases de datos
            r'^(mysql|postgresql|mongodb|redis|oracle|sqlite)$',
            # Cloud/DevOps
            r'^(aws|azure|gcp|docker|kubernetes|terraform)$',
            # Mobile
            r'^(android|ios|react.native|flutter)$'
        ]
        
        import re
        critical_skills = set()
        
        for skill in job_skills:
            skill_lower = skill.lower()
            for pattern in critical_patterns:
                if re.match(pattern, skill_lower):
                    critical_skills.add(skill)
                    break
        
        return critical_skills


class MatchingService:
    """Servicio principal para cálculo de matching."""
    
    def __init__(self, strategy: Optional[MatchingStrategy] = None):
        """
        Inicializa el servicio de matching.
        
        Args:
            strategy: Estrategia de matching a usar (por defecto: BasicSkillsMatchingStrategy)
        """
        self.strategy = strategy or BasicSkillsMatchingStrategy()
    
    def calculate_cv_job_match(self, cv: UserCV, job: JobPosting) -> MatchResult:
        """
        Calcula el matching entre un CV y una oferta de trabajo.
        
        Args:
            cv: CV del usuario
            job: Oferta de trabajo
            
        Returns:
            Resultado del matching
        """
        if not cv.skills_list:
            logger.warning(f"CV {cv.id} no tiene habilidades detectadas")
            return MatchResult(
                score=0.0,
                details={'error': 'CV sin habilidades detectadas'},
                confidence=0.0,
                matched_skills=[],
                missing_skills=[],
                extra_skills=[]
            )
        
        # Combinar descripción y título del trabajo
        job_text = f"{job.title} {job.description}".strip()
        
        return self.strategy.calculate_match(
            cv_skills=cv.skills,
            job_description=job_text,
            required_skills=None  # Podríamos extraer esto del HTML en el futuro
        )
    
    def calculate_user_job_matches(self, user_profile: UserProfile, job: JobPosting) -> List[Tuple[UserCV, MatchResult]]:
        """
        Calcula matching para todas las CVs de un usuario contra una oferta.
        
        Args:
            user_profile: Perfil del usuario
            job: Oferta de trabajo
            
        Returns:
            Lista de tuplas (CV, MatchResult) ordenadas por score descendente
        """
        user_cvs = UserCV.objects.filter(user=user_profile.user, parsed_text__isnull=False).exclude(parsed_text='')
        
        matches = []
        for cv in user_cvs:
            try:
                match_result = self.calculate_cv_job_match(cv, job)
                matches.append((cv, match_result))
            except Exception as e:
                logger.error(f"Error calculando match para CV {cv.id} y job {job.id}: {e}")
                continue
        
        # Ordenar por score descendente
        matches.sort(key=lambda x: x[1].score, reverse=True)
        
        return matches
    
    def save_match_score(self, user: UserProfile, cv: UserCV, job: JobPosting, 
                        match_result: MatchResult) -> MatchScore:
        """
        Guarda el resultado de matching en la base de datos.
        
        Args:
            user: Perfil del usuario
            cv: CV usado para el matching
            job: Oferta de trabajo
            match_result: Resultado del cálculo de matching
            
        Returns:
            Instancia de MatchScore guardada
        """
        match_score, created = MatchScore.objects.update_or_create(
            user=user,
            cv=cv,
            job_posting=job,
            defaults={
                'score': match_result.score,
                'details': match_result.details
            }
        )
        
        if created:
            logger.info(f"Nuevo match score creado: {match_result.score}% para job {job.id}")
        else:
            logger.info(f"Match score actualizado: {match_result.score}% para job {job.id}")
        
        return match_score
    
    def get_high_matches(self, user_profile: UserProfile, threshold: float = 70.0) -> List[MatchScore]:
        """
        Obtiene matches que superan el umbral del usuario.
        
        Args:
            user_profile: Perfil del usuario
            threshold: Umbral mínimo de score (por defecto usa el del perfil)
            
        Returns:
            Lista de MatchScore que superan el umbral
        """
        if threshold is None:
            threshold = user_profile.match_threshold
        
        return MatchScore.objects.filter(
            user=user_profile.user,
            score__gte=threshold
        ).order_by('-score', '-created_at')


# Instancia global del servicio
matching_service = MatchingService()
