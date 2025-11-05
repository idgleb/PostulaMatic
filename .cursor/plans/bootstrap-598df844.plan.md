<!-- 598df844-721a-44c8-a4ad-28c0db022a95 26267b51-51b0-4b50-a492-dd6fd98ef9bb -->
# Plan: Optimización de CVs para ATS

## 1. Agregar Extracción Híbrida de Keywords

**Archivo**: `matching/services/cv_personalizer.py`

Agregar nuevo método después de la línea 275 (antes de `CVPersonalizationService`):

```python
def _extract_keywords_from_job(self, job_description: str) -> List[str]:
    """Extrae keywords del puesto sin IA - rápido y gratis."""
    import re
    from collections import Counter
    
    # Diccionario expandido de keywords técnicas
    tech_keywords = {
        # Lenguajes
        'python', 'java', 'javascript', 'typescript', 'kotlin', 'swift', 'go', 'rust', 'c++', 'c#', 'php', 'ruby',
        # Frameworks
        'django', 'flask', 'fastapi', 'spring', 'react', 'angular', 'vue', 'next.js', 'node.js', 'express',
        # Bases de datos
        'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'cassandra', 'dynamodb',
        # Cloud/DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform', 'ansible', 'jenkins', 'ci/cd', 'git',
        # Mobile
        'android', 'ios', 'react native', 'flutter', 'jetpack compose', 'swiftui',
        # Data/ML
        'machine learning', 'deep learning', 'data science', 'pandas', 'numpy', 'tensorflow', 'pytorch',
        # Metodologías
        'agile', 'scrum', 'kanban', 'devops', 'tdd', 'microservices', 'rest api', 'graphql',
        # Soft skills
        'liderazgo', 'comunicación', 'trabajo en equipo', 'resolución de problemas'
    }
    
    text = job_description.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    
    found_keywords = []
    for keyword in tech_keywords:
        if keyword in text:
            count = text.count(keyword)
            found_keywords.append((keyword, count))
    
    found_keywords.sort(key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in found_keywords[:15]]

def _extract_keywords_hybrid(self, job_description: str) -> Dict[str, List[str]]:
    """Extrae keywords con enfoque híbrido: Reglas + IA opcional."""
    basic_keywords = self._extract_keywords_from_job(job_description)
    ai_keywords = []
    
    # Solo usar IA si hay pocas keywords básicas
    if len(basic_keywords) < 5 and len(job_description.split()) > 500:
        try:
            prompt = f"""Extrae SOLO las 5 habilidades técnicas más importantes.

Descripción: {job_description[:1000]}

Responde SOLO con lista separada por comas, sin explicaciones.
Ejemplo: Python, React, AWS, Docker, Agile"""
            
            response = self.ai_email_service.generate_text(prompt)
            ai_keywords = [kw.strip() for kw in response.split(',')]
            logger.info(f"✅ Keywords IA: {ai_keywords}")
        except Exception as e:
            logger.warning(f"⚠️ IA keywords falló: {e}")
    
    all_keywords = basic_keywords + [kw for kw in ai_keywords if kw.lower() not in [k.lower() for k in basic_keywords]]
    
    return {
        'basic': basic_keywords,
        'ai_enhanced': ai_keywords,
        'combined': all_keywords[:15]
    }
```

## 2. Inyectar Keywords en el Prompt de IA

**Archivo**: `matching/services/cv_personalizer.py`

Modificar `_create_cv_personalization_prompt` (línea 556):

1. Antes de crear el prompt (después de línea 574), agregar:
```python
# Extraer keywords del puesto
job_keywords = self._extract_keywords_hybrid(job_requirements['description'])
keywords_list = job_keywords['combined']
```

2. Modificar el prompt (línea 576) para inyectar keywords después de "REGLAS CRÍTICAS":
```python
prompt = f"""ROL: Eres un experto en Recursos Humanos y redacción de CVs ATS-friendly...

[contenido existente hasta REGLAS CRÍTICAS]

ESTRATEGIA ATS (APPLICANT TRACKING SYSTEM):
1) KEYWORDS CRÍTICAS: Incluye estas keywords del puesto en el CV:
   {', '.join(keywords_list)}
   
2) DISTRIBUCIÓN DE KEYWORDS:
   - skills: Incluye AL MENOS las primeras 5 keywords
   - summary: Usa AL MENOS 3 keywords naturalmente
   - experience bullets: Incluye AL MENOS 2 keywords por bullet
   
3) FORMATO ATS-FRIENDLY:
   - Sin tablas, gráficos, columnas múltiples
   - Bullets simples (•, -, *)
   - Secciones en MAYÚSCULAS
   
4) MÉTRICAS CUANTIFICABLES:
   - Incluye números/porcentajes cuando sea posible
   - Ejemplo: "Desarrollé APIs REST con Python/Django, reduciendo latencia 40%"

KEYWORDS DETECTADAS: {keywords_list}
INSTRUCCIÓN: Usa AL MENOS 70% de estas keywords en el CV.

[resto del prompt existente]
"""
```


## 3. Reemplazar Score Simplificado con Score Avanzado

**Archivo**: `matching/services/cv_personalizer.py`

Reemplazar `_calculate_match_score_simplified` (línea 1192) con:

```python
def _calculate_match_score_advanced(self, cv_data: Dict, job_data: Dict, personalized_cv: Dict) -> Dict:
    """Calcula score avanzado con desglose detallado."""
    import json
    
    try:
        # Extraer keywords del puesto
        job_keywords_data = self._extract_keywords_hybrid(job_data['description'])
        job_keywords = job_keywords_data['combined']
        cv_text = json.dumps(personalized_cv).lower()
        
        # 1. KEYWORD COVERAGE (40%)
        keywords_found = sum(1 for kw in job_keywords if kw in cv_text)
        keyword_score = (keywords_found / len(job_keywords)) * 40 if job_keywords else 0
        
        # 2. KEYWORD DENSITY (20%)
        keyword_density = sum(cv_text.count(kw) for kw in job_keywords)
        optimal_density = len(job_keywords) * 2.5
        density_ratio = keyword_density / optimal_density if optimal_density > 0 else 0
        density_score = 20 * (1 - abs(density_ratio - 1)) if density_ratio <= 2 else 0
        density_score = max(0, min(20, density_score))
        
        # 3. STRUCTURE QUALITY (20%)
        structure_score = 0
        if personalized_cv.get('experience') and len(personalized_cv['experience']) > 0:
            structure_score += 5
        if personalized_cv.get('skills') and len(personalized_cv['skills']) >= 10:
            structure_score += 5
        if personalized_cv.get('summary') and len(personalized_cv['summary']) > 100:
            structure_score += 5
        if personalized_cv.get('projects') and len(personalized_cv['projects']) > 0:
            structure_score += 5
        
        # 4. QUANTIFIABLE ACHIEVEMENTS (20%)
        achievement_count = 0
        for exp in personalized_cv.get('experience', []):
            for bullet in exp.get('bullets', []):
                if re.search(r'\d+%|\d+x|\$\d+|\d+ (usuarios|clientes|proyectos)', bullet.lower()):
                    achievement_count += 1
        achievement_score = min(20, achievement_count * 2)
        
        total_score = keyword_score + density_score + structure_score + achievement_score
        
        missing_keywords = [kw for kw in job_keywords if kw not in cv_text]
        
        logger.info(f"📊 Score Avanzado: {int(total_score)}% (Keywords: {int(keyword_score)}, Density: {int(density_score)}, Structure: {int(structure_score)}, Achievements: {int(achievement_score)})")
        
        return {
            'total': int(total_score),
            'breakdown': {
                'keyword_coverage': int(keyword_score),
                'keyword_density': int(density_score),
                'structure': int(structure_score),
                'achievements': int(achievement_score)
            },
            'keywords_found': keywords_found,
            'keywords_total': len(job_keywords),
            'missing_keywords': missing_keywords,
            'job_keywords': job_keywords
        }
        
    except Exception as e:
        logger.error(f"Error calculando score avanzado: {e}")
        return {
            'total': 0,
            'breakdown': {},
            'keywords_found': 0,
            'keywords_total': 0,
            'missing_keywords': [],
            'job_keywords': []
        }
```

Actualizar llamada en `personalize_cv_for_job` (línea 338):

```python
# Calcular score avanzado
match_score_data = self._calculate_match_score_advanced(cv_data, job_data, personalized_cv)
match_score = match_score_data['total']
process_logs.append(f"📊 Score: {match_score}% (Keywords: {match_score_data['breakdown'].get('keyword_coverage', 0)}%)")
```

Actualizar return (línea 341):

```python
return {
    'success': True,
    'personalized_cv': personalized_cv,
    'personalized_file': personalized_file,
    'job_requirements': job_data,
    'cv_data': cv_data,
    'match_score': match_score,
    'match_score_breakdown': match_score_data['breakdown'],  # NUEVO
    'missing_keywords': match_score_data['missing_keywords'],  # NUEVO
    'job_keywords': match_score_data['job_keywords'],  # NUEVO
    'process_logs': process_logs
}
```

## 4. Agregar Optimización Post-IA para ATS

**Archivo**: `matching/services/cv_personalizer.py`

Agregar método después de `_generate_personalized_cv_simplified` (alrededor línea 774):

```python
def _optimize_cv_for_ats(self, personalized_cv: Dict, job_keywords: List[str]) -> Dict:
    """Optimiza el CV generado para ATS."""
    import re
    
    try:
        # 1. INYECTAR KEYWORDS FALTANTES EN SKILLS
        current_skills = set(s.lower() for s in personalized_cv.get('skills', []))
        missing_keywords = [kw for kw in job_keywords if kw.lower() not in current_skills]
        
        if missing_keywords:
            personalized_cv['skills'] = missing_keywords[:5] + personalized_cv.get('skills', [])
            logger.info(f"✅ Inyectadas {len(missing_keywords[:5])} keywords en skills")
        
        # 2. OPTIMIZAR SUMMARY
        summary = personalized_cv.get('summary', '')
        keywords_in_summary = sum(1 for kw in job_keywords[:3] if kw.lower() in summary.lower())
        
        if keywords_in_summary < 2 and job_keywords:
            for keyword in job_keywords[:2]:
                if keyword.lower() not in summary.lower():
                    summary = summary.replace('.', f', con experiencia en {keyword}.', 1)
                    break
            personalized_cv['summary'] = summary
            logger.info(f"✅ Keywords agregadas al summary")
        
        # 3. VALIDAR BULLETS
        for exp in personalized_cv.get('experience', []):
            optimized_bullets = []
            for bullet in exp.get('bullets', []):
                # Truncar si es muy largo
                if len(bullet) > 220:
                    bullet = bullet[:217] + '...'
                
                # Asegurar keyword en bullet
                has_keyword = any(kw.lower() in bullet.lower() for kw in job_keywords)
                if not has_keyword and job_keywords:
                    bullet = f"{bullet.rstrip('.')}. Tecnologías: {job_keywords[0]}."
                
                optimized_bullets.append(bullet)
            exp['bullets'] = optimized_bullets
        
        # 4. LIMITAR SKILLS A 25
        if len(personalized_cv.get('skills', [])) > 25:
            personalized_cv['skills'] = personalized_cv['skills'][:25]
            logger.info(f"✅ Skills limitadas a 25")
        
        return personalized_cv
        
    except Exception as e:
        logger.error(f"Error optimizando CV para ATS: {e}")
        return personalized_cv
```

Integrar en `_generate_personalized_cv_simplified` (después de línea 759):

```python
# Parsear respuesta
personalized_cv = self._parse_ai_cv_response(ai_response)

# NUEVO: Optimizar para ATS
job_keywords_data = self._extract_keywords_hybrid(job_data['description'])
personalized_cv = self._optimize_cv_for_ats(personalized_cv, job_keywords_data['combined'])

if process_logs:
    process_logs.append("✅ CV optimizado para ATS")
```

## 5. Actualizar Response JSON en Views

**Archivo**: `matching/views_cv_personalization.py`

Modificar response_data (línea 88):

```python
response_data = {
    'success': True,
    'personalized_cv': result['personalized_cv'],
    'job_requirements': result['job_requirements'],
    'cv_data': result['cv_data'],
    'match_score': result['match_score'],
    'user_cv_skills': user_cv.skills_list if hasattr(user_cv, 'skills_list') else [],
    'message': f'CV personalizado generado exitosamente. Score: {result["match_score"]}%',
    'process_logs': result.get('process_logs', []),
    
    # NUEVO: Análisis ATS detallado
    'ats_analysis': {
        'score_breakdown': result.get('match_score_breakdown', {}),
        'missing_keywords': result.get('missing_keywords', []),
        'job_keywords': result.get('job_keywords', []),
        'suggestions': [
            f"✅ {len(result['personalized_cv'].get('skills', []))} habilidades incluidas",
            f"{'✅' if result['match_score'] >= 70 else '⚠️'} Match score: {result['match_score']}%",
            f"{'✅' if len(result.get('missing_keywords', [])) == 0 else '⚠️'} Keywords faltantes: {len(result.get('missing_keywords', []))}"
        ]
    }
}
```

## Orden de Implementación

1. Agregar `_extract_keywords_from_job` y `_extract_keywords_hybrid`
2. Modificar `_create_cv_personalization_prompt` para inyectar keywords
3. Reemplazar `_calculate_match_score_simplified` con `_calculate_match_score_advanced`
4. Agregar `_optimize_cv_for_ats`
5. Integrar optimización en `_generate_personalized_cv_simplified`
6. Actualizar response en `views_cv_personalization.py`
7. Probar con CV real y puesto de trabajo

## Impacto Esperado

- +25-40% en match score ATS
- Keywords estratégicas inyectadas automáticamente
- Score detallado con breakdown por categoría
- CVs optimizados post-generación
- Feedback específico sobre keywords faltantes

### To-dos

- [ ] Agregar métodos _extract_keywords_from_job y _extract_keywords_hybrid en cv_personalizer.py
- [ ] Modificar _create_cv_personalization_prompt para inyectar keywords en el prompt de IA
- [ ] Reemplazar _calculate_match_score_simplified con _calculate_match_score_advanced
- [ ] Agregar método _optimize_cv_for_ats para post-procesamiento
- [ ] Integrar _optimize_cv_for_ats en _generate_personalized_cv_simplified
- [ ] Actualizar response JSON en views_cv_personalization.py con ats_analysis
- [ ] Probar con CV real y verificar mejoras en match score y keywords