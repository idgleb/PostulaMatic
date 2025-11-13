"""
Módulo unificado para cálculo de Score ATS (Applicant Tracking System).

Este módulo contiene el algoritmo avanzado de matching que se usa tanto en:
- Scraper (para calcular match inicial entre CV y job posting)
- Personalización de CV (para calcular score antes/después de personalizar)

El score ATS se calcula en base a 4 factores:
1. Keyword Coverage (40%): ¿Cuántas keywords del puesto aparecen en el CV?
2. Keyword Density (20%): ¿La densidad de keywords es óptima? (ni muy poco ni demasiado)
3. Structure Quality (20%): ¿El CV tiene secciones completas y bien estructuradas?
4. Quantifiable Achievements (20%): ¿Hay métricas cuantificables en la experiencia?
"""

import json
import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


class KeywordExtractor:
    """Extrae keywords técnicas de descripciones de puestos."""

    # Diccionario expandido de keywords técnicas
    TECH_KEYWORDS = {
        # Lenguajes de programación
        "python",
        "java",
        "javascript",
        "typescript",
        "kotlin",
        "swift",
        "go",
        "rust",
        "c++",
        "c#",
        "php",
        "ruby",
        "scala",
        "r",
        "matlab",
        "sql",
        # Frameworks web
        "django",
        "flask",
        "fastapi",
        "spring",
        "spring boot",
        "react",
        "angular",
        "vue",
        "vue.js",
        "next.js",
        "nuxt",
        "node.js",
        "express",
        "nest.js",
        "laravel",
        "rails",
        # Mobile
        "android",
        "ios",
        "react native",
        "flutter",
        "jetpack compose",
        "swiftui",
        "xamarin",
        "ionic",
        # Bases de datos
        "postgresql",
        "mysql",
        "mongodb",
        "redis",
        "elasticsearch",
        "cassandra",
        "dynamodb",
        "oracle",
        "sql server",
        "sqlite",
        "firestore",
        "firebase",
        # Cloud/DevOps
        "aws",
        "azure",
        "gcp",
        "google cloud",
        "docker",
        "kubernetes",
        "k8s",
        "terraform",
        "ansible",
        "jenkins",
        "ci/cd",
        "gitlab ci",
        "github actions",
        "circleci",
        "git",
        "linux",
        # Data/ML
        "machine learning",
        "deep learning",
        "data science",
        "pandas",
        "numpy",
        "tensorflow",
        "pytorch",
        "scikit-learn",
        "keras",
        "spark",
        "hadoop",
        "airflow",
        # Testing
        "junit",
        "pytest",
        "jest",
        "selenium",
        "cypress",
        "unittest",
        "tdd",
        "bdd",
        # Metodologías
        "agile",
        "scrum",
        "kanban",
        "devops",
        "microservices",
        "rest api",
        "graphql",
        "soap",
        "mvvm",
        "mvc",
        # Herramientas
        "jira",
        "confluence",
        "figma",
        "sketch",
        "postman",
        "swagger",
        # Soft skills
        "liderazgo",
        "comunicación",
        "trabajo en equipo",
        "resolución de problemas",
        "pensamiento crítico",
    }

    @classmethod
    def extract_keywords(
        cls, job_description: str, max_keywords: int = 15
    ) -> List[str]:
        """
        Extrae keywords del puesto sin IA - rápido y gratis.

        Args:
            job_description: Descripción del puesto
            max_keywords: Máximo número de keywords a retornar

        Returns:
            Lista de keywords encontradas, ordenadas por frecuencia
        """
        text = job_description.lower()
        text = re.sub(r"[^\w\s]", " ", text)

        found_keywords = []
        for keyword in cls.TECH_KEYWORDS:
            if keyword in text:
                count = text.count(keyword)
                found_keywords.append((keyword, count))

        # Ordenar por frecuencia (descendente)
        found_keywords.sort(key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in found_keywords[:max_keywords]]


class ATSMatcher:
    """
    Calculador unificado de Score ATS.

    Este es el único algoritmo de matching usado en todo el sistema.
    """

    def __init__(self):
        self.keyword_extractor = KeywordExtractor()

    def calculate_score(
        self,
        cv_text: str,
        job_description: str,
        cv_structured: Dict = None,
    ) -> Dict:
        """
        Calcula el score ATS entre un CV y un puesto (VERSIÓN MEJORADA Y MÁS FLEXIBLE).

        Args:
            cv_text: Texto plano del CV (parsed_text o JSON serializado)
            job_description: Descripción del puesto
            cv_structured: CV estructurado (opcional, para análisis de estructura)

        Returns:
            Dict con:
                - total: Score total (0-100)
                - breakdown: Desglose por categoría
                - keywords_found: Número de keywords encontradas
                - keywords_total: Total de keywords del puesto
                - missing_keywords: Keywords que faltan en el CV
                - job_keywords: Todas las keywords del puesto
        """
        try:
            # Extraer keywords del puesto
            job_keywords = self.keyword_extractor.extract_keywords(job_description)

            # Normalizar CV text
            if isinstance(cv_text, dict):
                cv_text = json.dumps(cv_text).lower()
            else:
                cv_text = cv_text.lower()

            # 1. KEYWORD COVERAGE (35%) - MEJORADO: Matching más flexible
            keywords_found_count, partial_matches = self._flexible_keyword_matching(
                cv_text, job_keywords
            )
            keyword_score = (
                (keywords_found_count / len(job_keywords)) * 35 if job_keywords else 0
            )

            # BONUS: +5% por matches parciales (sinónimos, variaciones)
            bonus_score = min(5, len(partial_matches) * 0.5)
            keyword_score += bonus_score

            # 2. KEYWORD DENSITY (15%) - MEJORADO: Rango óptimo más amplio
            keyword_density = sum(cv_text.count(kw) for kw in job_keywords)
            optimal_density = len(job_keywords) * 2.5
            density_ratio = (
                keyword_density / optimal_density if optimal_density > 0 else 0
            )
            # Rango óptimo: 0.5 - 2.0 (antes era muy estricto)
            if 0.5 <= density_ratio <= 2.0:
                density_score = 15 * (1 - abs(density_ratio - 1.25) / 0.75)
            else:
                density_score = max(0, 15 * (1 - abs(density_ratio - 1.25)))
            density_score = max(0, min(15, density_score))

            # 3. STRUCTURE QUALITY (25%) - MEJORADO: Más puntos por estructura
            structure_score = self._calculate_structure_score(cv_text, cv_structured)

            # 4. QUANTIFIABLE ACHIEVEMENTS (25%) - MEJORADO: Más puntos por logros
            achievement_score = self._calculate_achievement_score(
                cv_text, cv_structured
            )

            total_score = (
                keyword_score + density_score + structure_score + achievement_score
            )

            missing_keywords = [
                kw
                for kw in job_keywords
                if kw not in cv_text and kw not in partial_matches
            ]

            logger.info(
                f"📊 Score ATS: {int(total_score)}% "
                f"(Keywords: {int(keyword_score)}, "
                f"Density: {int(density_score)}, "
                f"Structure: {int(structure_score)}, "
                f"Achievements: {int(achievement_score)}) "
                f"[Matches: {keywords_found_count}/{len(job_keywords)}, Parciales: {len(partial_matches)}]"
            )

            return {
                "total": int(total_score),
                "breakdown": {
                    "keyword_coverage": int(keyword_score),
                    "keyword_density": int(density_score),
                    "structure": int(structure_score),
                    "achievements": int(achievement_score),
                },
                "keywords_found": keywords_found_count,
                "keywords_total": len(job_keywords),
                "missing_keywords": missing_keywords,
                "job_keywords": job_keywords,
                "partial_matches": partial_matches,  # NUEVO
            }

        except Exception as e:
            logger.error(f"❌ Error calculando score ATS: {e}", exc_info=True)
            return {
                "total": 0,
                "breakdown": {},
                "keywords_found": 0,
                "keywords_total": 0,
                "missing_keywords": [],
                "job_keywords": [],
                "partial_matches": [],
            }

    def _flexible_keyword_matching(
        self, cv_text: str, job_keywords: List[str]
    ) -> tuple:
        """
        Matching flexible de keywords con sinónimos y variaciones.

        Returns:
            (exact_matches_count, partial_matches_list)
        """
        exact_matches = 0
        partial_matches = []

        # Diccionario de sinónimos y variaciones
        synonyms = {
            "javascript": ["js", "ecmascript", "node", "nodejs"],
            "typescript": ["ts"],
            "python": ["py"],
            "postgresql": ["postgres", "psql"],
            "mongodb": ["mongo"],
            "kubernetes": ["k8s"],
            "docker": ["container", "containerization"],
            "react": ["reactjs", "react.js"],
            "angular": ["angularjs"],
            "vue": ["vuejs", "vue.js"],
            "django": ["python web", "python framework"],
            "flask": ["python web", "python framework"],
            "spring": ["spring boot", "java framework"],
            "android": ["mobile", "kotlin", "java mobile"],
            "ios": ["mobile", "swift", "objective-c"],
            "machine learning": ["ml", "ai", "artificial intelligence"],
            "deep learning": ["dl", "neural network"],
            "data science": ["data analysis", "analytics"],
            "rest api": ["api", "restful", "web service"],
            "graphql": ["api", "query language"],
            "ci/cd": ["continuous integration", "continuous deployment", "devops"],
            "agile": ["scrum", "kanban", "metodologías ágiles"],
            "git": ["version control", "github", "gitlab", "bitbucket"],
            "aws": ["amazon web services", "cloud", "ec2", "lambda", "s3"],
            "azure": ["microsoft azure", "cloud"],
            "gcp": ["google cloud", "cloud"],
        }

        for keyword in job_keywords:
            # Exact match
            if keyword in cv_text:
                exact_matches += 1
            # Partial match con sinónimos
            elif keyword in synonyms:
                for synonym in synonyms[keyword]:
                    if synonym in cv_text:
                        partial_matches.append(f"{keyword} (via {synonym})")
                        break

        return exact_matches, partial_matches

    def _calculate_structure_score(
        self, cv_text: str, cv_structured: Dict = None
    ) -> int:
        """
        Calcula el score de estructura del CV (0-25 puntos) - MEJORADO.

        Verifica (más flexible):
        - Tiene experiencia laboral (7 pts)
        - Tiene al menos 5 skills (6 pts) - Reducido de 10 a 5
        - Tiene summary/objetivo de al menos 50 caracteres (6 pts) - Reducido de 100 a 50
        - Tiene proyectos (6 pts)
        """
        structure_score = 0

        if cv_structured:
            # Si tenemos CV estructurado, usarlo
            if cv_structured.get("experience") and len(cv_structured["experience"]) > 0:
                structure_score += 7
            # MÁS FLEXIBLE: Solo 5 skills requeridas (antes 10)
            if cv_structured.get("skills") and len(cv_structured["skills"]) >= 5:
                structure_score += 6
            # MÁS FLEXIBLE: Solo 50 caracteres (antes 100)
            if cv_structured.get("summary") and len(cv_structured["summary"]) > 50:
                structure_score += 6
            if cv_structured.get("projects") and len(cv_structured["projects"]) > 0:
                structure_score += 6
        else:
            # Fallback: análisis de texto plano (MÁS FLEXIBLE)
            if (
                "experiencia" in cv_text
                or "experience" in cv_text
                or "trabajo" in cv_text
            ):
                structure_score += 7
            # Contar palabras únicas que parecen skills (más de 5, antes 10)
            words = set(cv_text.split())
            tech_words = words.intersection(KeywordExtractor.TECH_KEYWORDS)
            if len(tech_words) >= 5:
                structure_score += 6
            # Buscar sección de resumen/objetivo (más flexible)
            if (
                "resumen" in cv_text
                or "summary" in cv_text
                or "objetivo" in cv_text
                or "perfil" in cv_text
            ) and len(cv_text) > 300:
                structure_score += 6
            # Buscar proyectos (más flexible)
            if (
                "proyecto" in cv_text
                or "project" in cv_text
                or "desarrollé" in cv_text
                or "desarrolle" in cv_text
            ):
                structure_score += 6

        return structure_score

    def _calculate_achievement_score(
        self, cv_text: str, cv_structured: Dict = None
    ) -> int:
        """
        Calcula el score de logros cuantificables (0-25 puntos) - MEJORADO.

        Busca patrones más amplios:
        - Porcentajes: 40%, +25%, -15%
        - Multiplicadores: 2x, 3x, 10x
        - Dinero: $1000, USD 5000, €500
        - Números con contexto: 100 usuarios, 50 clientes, 10 proyectos, 5 años
        - Verbos de logro: implementé, desarrollé, optimicé, reduje, aumenté
        """
        achievement_count = 0

        # Patrones más amplios y flexibles
        achievement_patterns = [
            r"\d+%",  # Porcentajes
            r"\d+x",  # Multiplicadores
            r"[\$€£]\d+",  # Dinero
            r"\d+ (usuarios|clientes|proyectos|millones|miles|días|semanas|meses|años)",  # Números con contexto (español)
            r"\d+ (users|clients|projects|millions|thousands|days|weeks|months|years)",  # Números con contexto (inglés)
            r"(implementé|desarrollé|optimicé|reduje|aumenté|mejoré|logré|conseguí)\s+\w+",  # Verbos de logro (español)
            r"(implemented|developed|optimized|reduced|increased|improved|achieved|delivered)\s+\w+",  # Verbos de logro (inglés)
        ]

        if cv_structured and cv_structured.get("experience"):
            # Si tenemos CV estructurado, analizar bullets
            for exp in cv_structured["experience"]:
                for bullet in exp.get("bullets", []):
                    bullet_lower = bullet.lower()
                    for pattern in achievement_patterns:
                        if re.search(pattern, bullet_lower):
                            achievement_count += 1
                            break  # Solo contar una vez por bullet
        else:
            # Fallback: buscar en texto plano
            for pattern in achievement_patterns:
                matches = re.findall(pattern, cv_text.lower())
                achievement_count += len(matches)

        # Cada logro cuantificable suma 2.5 puntos, máximo 25
        achievement_score = min(25, achievement_count * 2.5)
        return int(achievement_score)


# Instancia global para uso conveniente
ats_matcher = ATSMatcher()


def calculate_ats_score(
    cv_text: str,
    job_description: str,
    cv_structured: Dict = None,
) -> Dict:
    """
    Función de conveniencia para calcular score ATS.

    Args:
        cv_text: Texto plano del CV
        job_description: Descripción del puesto
        cv_structured: CV estructurado (opcional)

    Returns:
        Dict con score total y desglose
    """
    return ats_matcher.calculate_score(cv_text, job_description, cv_structured)
