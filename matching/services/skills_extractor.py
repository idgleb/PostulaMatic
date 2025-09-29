"""
Servicio para extraer habilidades de CVs usando técnicas básicas de procesamiento de texto.
Esta es la versión inicial sin IA, preparada para futuras integraciones con LLMs.
"""
import re
import logging
from typing import List, Dict, Set, Tuple, Any
from collections import Counter

logger = logging.getLogger(__name__)


class SkillsExtractorError(Exception):
    """Excepción personalizada para errores del extractor de skills."""
    pass


class SkillsExtractor:
    """Extractor de habilidades usando técnicas básicas de NLP."""
    
    def __init__(self):
        # Base de datos básica de habilidades comunes en español/inglés
        self.skills_database = self._load_skills_database()
        self.synonyms = self._load_synonyms()
        self.stop_words = self._load_stop_words()
    
    def _load_skills_database(self) -> Dict[str, List[str]]:
        """Carga la base de datos básica de habilidades."""
        return {
            # Programación y Tecnologías
            'programming': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
                'kotlin', 'swift', 'scala', 'r', 'matlab', 'sql', 'html', 'css', 'react', 'angular',
                'vue', 'node.js', 'django', 'flask', 'spring', 'laravel', 'express', 'rails',
                'retrofit', 'okhttp', 'coroutines', 'flow', 'dagger', 'hilt', 'room', 'sharedpreferences'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle', 'sqlite',
                'mariadb', 'cassandra', 'neo4j', 'dynamodb'
            ],
            'cloud': [
                'aws', 'azure', 'gcp', 'google cloud', 'amazon web services', 'docker', 'kubernetes',
                'terraform', 'ansible', 'jenkins', 'gitlab ci', 'github actions'
            ],
            'mobile': [
                'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic', 'cordova',
                'jetpack compose', 'viewmodel', 'navigation component', 'workmanager', 'jsoup'
            ],
            
            # Análisis de Datos y IA
            'data_science': [
                'machine learning', 'deep learning', 'pandas', 'numpy', 'scikit-learn', 'tensorflow',
                'pytorch', 'keras', 'jupyter', 'spark', 'hadoop', 'tableau', 'power bi', 'excel'
            ],
            'ai_ml': [
                'artificial intelligence', 'neural networks', 'nlp', 'computer vision', 'opencv',
                'nltk', 'spacy', 'transformers', 'bert', 'gpt'
            ],
            
            # Diseño y UX/UI
            'design': [
                'photoshop', 'illustrator', 'figma', 'sketch', 'adobe xd', 'invision', 'canva',
                'ui design', 'ux design', 'wireframing', 'prototyping', 'material design'
            ],
            
            # Marketing Digital
            'marketing': [
                'google analytics', 'google ads', 'facebook ads', 'seo', 'sem', 'content marketing',
                'social media', 'email marketing', 'hubspot', 'salesforce', 'mailchimp'
            ],
            
            # Gestión de Proyectos
            'project_management': [
                'agile', 'scrum', 'kanban', 'jira', 'trello', 'asana', 'confluence', 'slack',
                'monday.com', 'notion'
            ],
            
            # Idiomas
            'languages': [
                'español', 'inglés', 'francés', 'alemán', 'italiano', 'portugués', 'chino', 'japonés',
                'spanish', 'english', 'french', 'german', 'italian', 'portuguese', 'chinese', 'japanese'
            ],
            
            # Habilidades Blandas
            'soft_skills': [
                'liderazgo', 'trabajo en equipo', 'comunicación', 'resolución de problemas',
                'pensamiento crítico', 'adaptabilidad', 'gestión del tiempo', 'negociación',
                'leadership', 'teamwork', 'communication', 'problem solving', 'critical thinking',
                'adaptability', 'time management', 'negotiation'
            ],
            
            # Arquitectura y Patrones
            'architecture': [
                'mvvm', 'mvc', 'mvp', 'clean architecture', 'repository pattern', 'factory pattern',
                'singleton pattern', 'observer pattern', 'dependency injection', 'rest api',
                'graphql', 'microservices', 'soa'
            ],
            
            # === CARRERAS DAVINCI ===
            
            # Diseño Multimedial
            'multimedia_design': [
                'after effects', 'premiere pro', 'final cut pro', 'davinci resolve', 'adobe creative suite',
                'motion graphics', 'video editing', 'audio editing', 'sound design', 'color grading',
                'compositing', 'visual effects', 'vfx', '3d modeling', 'blender', 'maya', 'cinema 4d',
                'motion capture', 'green screen', 'chroma key', 'rotoscoping', 'match moving',
                'particle systems', 'fluid simulation', 'rigging', 'animation', 'character animation',
                'storyboarding', 'previsualization', 'post production', 'editing', 'color correction'
            ],
            
            # Diseño Gráfico Artístico Digital
            'digital_art': [
                'photoshop', 'illustrator', 'indesign', 'corel draw', 'affinity designer', 'procreate',
                'digital painting', 'vector graphics', 'raster graphics', 'typography', 'branding',
                'logo design', 'poster design', 'book design', 'magazine design', 'packaging design',
                'ui design', 'ux design', 'wireframing', 'prototyping', 'figma', 'sketch', 'adobe xd',
                'color theory', 'composition', 'visual hierarchy', 'grid systems', 'print design',
                'web design', 'mobile design', 'responsive design', 'accessibility design'
            ],
            
            # Programación de Videojuegos
            'game_development': [
                'unity', 'unreal engine', 'godot', 'game maker studio', 'construct 3', 'rpg maker',
                'c#', 'c++', 'javascript', 'lua', 'python', 'blueprint', 'visual scripting',
                'game design', 'level design', 'game mechanics', 'gameplay programming', 'ai programming',
                'physics programming', 'rendering', 'shaders', 'opengl', 'directx', 'vulkan',
                'game engines', 'asset pipeline', 'optimization', 'performance', 'memory management',
                'collision detection', 'pathfinding', 'state machines', 'game loops', 'frameworks',
                'mobile games', 'pc games', 'console games', 'indie games', 'serious games'
            ],
            
            # Cine de Animación y Posproducción
            'animation_cinema': [
                'maya', 'blender', '3ds max', 'cinema 4d', 'houdini', 'zbrush', 'mudbox',
                'character rigging', 'character animation', 'facial animation', 'motion capture',
                'keyframe animation', 'procedural animation', 'particle systems', 'fluid dynamics',
                'cloth simulation', 'hair simulation', 'fur simulation', 'crowd simulation',
                'rendering', 'arnold', 'vray', 'cycles', 'octane', 'redshift', 'mental ray',
                'compositing', 'nuke', 'fusion', 'after effects', 'flame', 'smoke',
                'color grading', 'davinci resolve', 'color correction', 'color space',
                'stereoscopic', 'vr', 'ar', '360 video', 'spherical video'
            ],
            
            # Diseño y Programación Web
            'web_development': [
                'html', 'css', 'javascript', 'typescript', 'react', 'angular', 'vue', 'svelte',
                'node.js', 'express', 'django', 'flask', 'laravel', 'rails', 'spring boot',
                'php', 'python', 'ruby', 'java', 'c#', 'asp.net', 'wordpress', 'drupal',
                'frontend', 'backend', 'full stack', 'responsive design', 'mobile first',
                'progressive web apps', 'pwa', 'spa', 'ssr', 'ssg', 'api', 'rest api',
                'graphql', 'microservices', 'docker', 'kubernetes', 'aws', 'azure', 'gcp',
                'databases', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
                'version control', 'git', 'github', 'gitlab', 'ci/cd', 'devops', 'testing'
            ],
            
            # Analista de Sistemas
            'systems_analysis': [
                'uml', 'bpmn', 'use cases', 'user stories', 'requirements analysis', 'system design',
                'database design', 'er diagrams', 'data modeling', 'normalization', 'sql',
                'business analysis', 'process modeling', 'workflow design', 'system architecture',
                'software engineering', 'agile', 'scrum', 'kanban', 'waterfall', 'iterative',
                'testing', 'unit testing', 'integration testing', 'system testing', 'user acceptance',
                'quality assurance', 'qa', 'bug tracking', 'jira', 'confluence', 'documentation',
                'technical writing', 'project management', 'stakeholder management', 'communication'
            ],
            
            # Cine y Nuevos Formatos
            'cinema_new_formats': [
                'cinematography', 'camera operation', 'lighting', 'sound recording', 'boom operator',
                'directing', 'screenwriting', 'script writing', 'storytelling', 'narrative structure',
                'pre production', 'production', 'post production', 'editing', 'color grading',
                'sound design', 'music composition', 'foley', 'adr', 'voice over', 'dubbing',
                'vr filmmaking', '360 video', 'spherical video', 'immersive media', 'interactive media',
                'documentary', 'fiction', 'experimental', 'short films', 'feature films',
                'streaming', 'youtube', 'netflix', 'amazon prime', 'disney plus', 'platforms',
                'distribution', 'marketing', 'social media', 'content creation', 'influencer'
            ],
            
            # Herramientas Específicas DaVinci
            'davinci_tools': [
                'adobe creative suite', 'autodesk maya', 'autodesk 3ds max', 'blender', 'cinema 4d',
                'houdini', 'zbrush', 'substance painter', 'substance designer', 'mari', 'mudbox',
                'nuke', 'fusion', 'after effects', 'premiere pro', 'davinci resolve', 'final cut pro',
                'photoshop', 'illustrator', 'indesign', 'figma', 'sketch', 'adobe xd',
                'unity', 'unreal engine', 'godot', 'visual studio', 'visual studio code',
                'intellij idea', 'eclipse', 'netbeans', 'android studio', 'xcode'
            ]
        }
    
    def _load_synonyms(self) -> Dict[str, str]:
        """Carga sinónimos comunes para normalizar habilidades."""
        return {
            # Normalizaciones comunes
            'js': 'javascript',
            'react.js': 'react',
            'node': 'node.js',
            'postgres': 'postgresql',
            'ai': 'artificial intelligence',
            'ml': 'machine learning',
            'dl': 'deep learning',
            'cv': 'computer vision',
            'nlp': 'natural language processing',
            'ui/ux': 'ui design',
            'ux/ui': 'ux design',
            'pm': 'project management',
            'git': 'version control',
            'api': 'application programming interface',
            'rest': 'rest api',
            'graphql': 'graphql api',
            'microservices': 'microservices architecture',
            'devops': 'devops',
            'ci/cd': 'continuous integration',
            'tdd': 'test driven development',
            'bdd': 'behavior driven development',
            
            # Sinónimos específicos DaVinci
            'ae': 'after effects',
            'pr': 'premiere pro',
            'ps': 'photoshop',
            'ai': 'illustrator',
            'id': 'indesign',
            'figma': 'figma',
            'sketch': 'sketch',
            'xd': 'adobe xd',
            'unity': 'unity',
            'ue': 'unreal engine',
            'maya': 'autodesk maya',
            '3ds': '3ds max',
            'c4d': 'cinema 4d',
            'blender': 'blender',
            'houdini': 'houdini',
            'zbrush': 'zbrush',
            'nuke': 'nuke',
            'fusion': 'fusion',
            'resolve': 'davinci resolve',
            'fcp': 'final cut pro',
            'motion': 'motion graphics',
            'vfx': 'visual effects',
            '3d': '3d modeling',
            'rigging': 'character rigging',
            'animation': 'character animation',
            'mocap': 'motion capture',
            'compositing': 'compositing',
            'color': 'color grading',
            'editing': 'video editing',
            'sound': 'sound design',
            'audio': 'audio editing',
            'ui': 'ui design',
            'ux': 'ux design',
            'wireframe': 'wireframing',
            'prototype': 'prototyping',
            'branding': 'brand design',
            'logo': 'logo design',
            'typography': 'typography',
            'game': 'game development',
            'gamedev': 'game development',
            'unity': 'unity',
            'unreal': 'unreal engine',
            'godot': 'godot',
            'blueprint': 'blueprint',
            'shader': 'shaders',
            'rendering': 'rendering',
            'optimization': 'performance optimization',
            'collision': 'collision detection',
            'pathfinding': 'pathfinding',
            'ai': 'artificial intelligence',
            'physics': 'physics programming',
            'mobile': 'mobile development',
            'web': 'web development',
            'frontend': 'frontend development',
            'backend': 'backend development',
            'fullstack': 'full stack development',
            'api': 'api development',
            'rest': 'rest api',
            'graphql': 'graphql',
            'database': 'database design',
            'sql': 'sql',
            'mysql': 'mysql',
            'postgresql': 'postgresql',
            'mongodb': 'mongodb',
            'redis': 'redis',
            'docker': 'docker',
            'kubernetes': 'kubernetes',
            'aws': 'amazon web services',
            'azure': 'microsoft azure',
            'gcp': 'google cloud platform',
            'git': 'git',
            'github': 'github',
            'gitlab': 'gitlab',
            'testing': 'software testing',
            'qa': 'quality assurance',
            'agile': 'agile methodology',
            'scrum': 'scrum',
            'kanban': 'kanban',
            'jira': 'jira',
            'confluence': 'confluence',
            'documentation': 'technical documentation',
            'uml': 'uml',
            'bpmn': 'bpmn',
            'cinematography': 'cinematography',
            'camera': 'camera operation',
            'lighting': 'lighting',
            'sound': 'sound recording',
            'directing': 'directing',
            'screenwriting': 'screenwriting',
            'script': 'script writing',
            'storytelling': 'storytelling',
            'narrative': 'narrative structure',
            'preproduction': 'pre production',
            'production': 'production',
            'postproduction': 'post production',
            'editing': 'video editing',
            'color': 'color grading',
            'sound': 'sound design',
            'music': 'music composition',
            'foley': 'foley',
            'adr': 'adr',
            'voice': 'voice over',
            'dubbing': 'dubbing',
            'vr': 'virtual reality',
            'ar': 'augmented reality',
            '360': '360 video',
            'spherical': 'spherical video',
            'immersive': 'immersive media',
            'interactive': 'interactive media',
            'documentary': 'documentary',
            'fiction': 'fiction',
            'experimental': 'experimental',
            'short': 'short films',
            'feature': 'feature films',
            'streaming': 'streaming',
            'youtube': 'youtube',
            'netflix': 'netflix',
            'amazon': 'amazon prime',
            'disney': 'disney plus',
            'platforms': 'streaming platforms',
            'distribution': 'distribution',
            'marketing': 'marketing',
            'social': 'social media',
            'content': 'content creation',
            'influencer': 'influencer'
        }
    
    def _load_stop_words(self) -> Set[str]:
        """Carga palabras de parada para filtrar ruido."""
        return {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'el', 'la', 'los', 'las', 'de', 'del', 'en', 'con', 'para', 'por', 'sobre',
            'y', 'o', 'pero', 'sin', 'entre', 'hasta', 'desde', 'hacia', 'durante'
        }
    
    def extract_skills(self, cv_text: str, min_confidence: float = 0.3) -> Dict[str, Any]:
        """
        Extrae habilidades del texto del CV.
        
        Args:
            cv_text: Texto del CV normalizado
            min_confidence: Umbral mínimo de confianza (0.0 - 1.0)
            
        Returns:
            Dict con skills encontradas, categorías y metadatos
        """
        if not cv_text or not cv_text.strip():
            return {
                'skills': [],
                'categories': {},
                'confidence_scores': {},
                'total_skills': 0,
                'extraction_method': 'basic_keyword_matching'
            }
        
        # Normalizar texto para búsqueda
        normalized_text = self._normalize_for_search(cv_text)
        
        # Extraer habilidades por diferentes métodos
        exact_matches = self._extract_exact_matches(normalized_text)
        keyword_matches = self._extract_keyword_matches(normalized_text)
        context_matches = self._extract_context_matches(normalized_text)
        
        # Combinar y puntuar resultados
        all_skills = self._combine_and_score_skills(
            exact_matches, keyword_matches, context_matches, min_confidence
        )
        
        # Organizar por categorías
        categorized_skills = self._categorize_skills(all_skills)
        
        return {
            'skills': list(all_skills.keys()),
            'categories': categorized_skills,
            'confidence_scores': all_skills,
            'total_skills': len(all_skills),
            'extraction_method': 'basic_keyword_matching',
            'details': {
                'exact_matches': len(exact_matches),
                'keyword_matches': len(keyword_matches),
                'context_matches': len(context_matches)
            }
        }
    
    def _normalize_for_search(self, text: str) -> str:
        """Normaliza el texto para búsqueda de habilidades."""
        # Convertir a minúsculas
        text = text.lower()
        
        # Remover caracteres especiales excepto espacios y guiones
        text = re.sub(r'[^\w\s\-/]', ' ', text)
        
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _extract_exact_matches(self, text: str) -> Dict[str, float]:
        """Extrae coincidencias exactas con la base de datos."""
        matches = {}
        
        for category, skills in self.skills_database.items():
            for skill in skills:
                # Buscar la skill exacta
                if re.search(r'\b' + re.escape(skill.lower()) + r'\b', text):
                    matches[skill] = 1.0  # Máxima confianza para coincidencias exactas
        
        return matches
    
    def _extract_keyword_matches(self, text: str) -> Dict[str, float]:
        """Extrae coincidencias por palabras clave."""
        matches = {}
        words = text.split()
        word_count = Counter(words)
        
        for category, skills in self.skills_database.items():
            for skill in skills:
                skill_words = skill.lower().split()
                
                # Si la skill es una sola palabra, buscar directamente
                if len(skill_words) == 1:
                    if skill_words[0] in word_count:
                        # Confianza basada en frecuencia
                        confidence = min(word_count[skill_words[0]] * 0.3, 0.8)
                        matches[skill] = confidence
                
                # Si la skill tiene múltiples palabras, buscar secuencias
                else:
                    skill_pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                    if re.search(skill_pattern, text):
                        matches[skill] = 0.9
        
        return matches
    
    def _extract_context_matches(self, text: str) -> Dict[str, float]:
        """Extrae habilidades basándose en contexto (patrones comunes)."""
        matches = {}
        
        # Patrones de contexto para diferentes tipos de habilidades
        context_patterns = {
            'experience_with': r'(?:experience|experiencia|conocimiento|knowledge|skills|habilidades).*?(?:with|en|de)\s+([a-zA-Z\s]+)',
            'proficient_in': r'(?:proficient|competent|skilled|experto|experta).*?(?:in|en)\s+([a-zA-Z\s]+)',
            'worked_with': r'(?:worked|trabajé|trabajado).*?(?:with|con)\s+([a-zA-Z\s]+)',
            'technologies': r'(?:technologies|tecnologías|tools|herramientas):\s*([a-zA-Z\s,]+)',
        }
        
        for pattern_name, pattern in context_patterns.items():
            found_matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in found_matches:
                # Limpiar y dividir el match
                skills_found = [s.strip() for s in re.split(r'[,;]', match)]
                
                for skill in skills_found:
                    if len(skill) > 2 and skill not in self.stop_words:
                        # Verificar si coincide con alguna skill conocida
                        for category, known_skills in self.skills_database.items():
                            for known_skill in known_skills:
                                if known_skill.lower() in skill.lower() or skill.lower() in known_skill.lower():
                                    matches[known_skill] = 0.6  # Confianza media por contexto
        
        return matches
    
    def _combine_and_score_skills(self, exact_matches: Dict[str, float], 
                                 keyword_matches: Dict[str, float],
                                 context_matches: Dict[str, float],
                                 min_confidence: float) -> Dict[str, float]:
        """Combina y puntúa todas las habilidades encontradas."""
        combined_skills = {}
        
        # Combinar todas las habilidades con sus puntuaciones
        all_matches = {**exact_matches, **keyword_matches, **context_matches}
        
        for skill, confidence in all_matches.items():
            if confidence >= min_confidence:
                # Aplicar sinónimos
                normalized_skill = self.synonyms.get(skill.lower(), skill)
                
                # Mantener la mayor confianza si hay duplicados
                if normalized_skill in combined_skills:
                    combined_skills[normalized_skill] = max(combined_skills[normalized_skill], confidence)
                else:
                    combined_skills[normalized_skill] = confidence
        
        return combined_skills
    
    def _categorize_skills(self, skills: Dict[str, float]) -> Dict[str, List[str]]:
        """Categoriza las habilidades encontradas."""
        categorized = {category: [] for category in self.skills_database.keys()}
        categorized['other'] = []
        
        for skill, confidence in skills.items():
            categorized_flag = False
            
            for category, category_skills in self.skills_database.items():
                if skill.lower() in [s.lower() for s in category_skills]:
                    categorized[category].append(skill)
                    categorized_flag = True
                    break
            
            if not categorized_flag:
                categorized['other'].append(skill)
        
        # Remover categorías vacías
        return {k: v for k, v in categorized.items() if v}


# Instancia global del extractor
skills_extractor = SkillsExtractor()
