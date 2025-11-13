"""
Servicio de personalización de CV basado en requisitos del puesto.
Genera versiones personalizadas del CV original destacando habilidades relevantes.
"""

import json
import logging
import re
from typing import Dict, List, Optional

from matching.models import JobPosting, UserCV

from .ai_service import ai_email_service
from .ats_matcher import KeywordExtractor, ats_matcher

logger = logging.getLogger(__name__)


class CVPersonalizationService:
    """Servicio principal de personalización de CV."""

    def __init__(self):
        self.ai_email_service = ai_email_service

    def personalize_cv_for_job(
        self,
        user_cv: UserCV,
        job_posting: JobPosting,
        user_profile: Optional[Dict] = None,
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
        process_logs = []

        try:
            logger.info("🔧 Iniciando personalización de CV")
            process_logs.append("🔍 Preparando datos para IA...")

            # Validar que el CV tenga texto parseado
            if not user_cv.parsed_text:
                error_msg = (
                    "❌ El CV no tiene texto parseado. Por favor, vuelve a subir el CV."
                )
                logger.error(error_msg)
                process_logs.append(error_msg)
                return self._error_response(error_msg, process_logs)

            # Preparar datos
            job_data = {
                "title": job_posting.title,
                "description": job_posting.description,
                "mail": getattr(job_posting, "contact_email", "N/A"),
            }
            cv_data = {"parsed_text": user_cv.parsed_text}

            process_logs.append(f"📋 Puesto: {job_data['title']}")
            process_logs.append(
                f"📊 CV preparado: {len(cv_data['parsed_text'])} caracteres"
            )

            # Generar CV personalizado
            process_logs.append("🤖 Generando CV personalizado con IA...")
            personalized_cv = self._generate_personalized_cv(
                cv_data, job_data, user_profile, process_logs
            )

            # Crear archivo personalizado
            process_logs.append("📁 Creando archivo personalizado...")
            personalized_file = self._create_personalized_file(
                user_cv, personalized_cv, job_posting
            )

            # Calcular scores (original y personalizado)
            process_logs.append("📊 Calculando scores ATS...")
            # ✅ IMPORTANTE: Usar None para que el algoritmo busque estructura en el texto
            # Esto es más realista y consistente con "Mis Matches" (ambos tendrán el mismo score)
            original_score_data = self._calculate_ats_score(
                cv_data,
                job_data,
                None,  # Deja que el algoritmo busque en el texto (como ATS real)
            )
            personalized_score_data = self._calculate_ats_score(
                cv_data, job_data, personalized_cv
            )

            original_score = original_score_data["total"]
            match_score = personalized_score_data["total"]
            improvement = match_score - original_score

            process_logs.append(f"📊 Score Original: {original_score}%")
            process_logs.append(f"📊 Score Personalizado: {match_score}%")
            process_logs.append(f"📈 Mejora: +{improvement}%")

            return {
                "success": True,
                "personalized_cv": personalized_cv,
                "personalized_file": personalized_file,
                "job_requirements": job_data,
                "cv_data": cv_data,
                "match_score": match_score,
                "match_score_breakdown": personalized_score_data["breakdown"],
                "missing_keywords": personalized_score_data["missing_keywords"],
                "job_keywords": personalized_score_data["job_keywords"],
                "original_score": original_score,
                "improvement": improvement,
                "process_logs": process_logs,
            }

        except Exception as e:
            logger.error(
                f"Error personalizando CV {user_cv.id} para puesto {job_posting.id}: {e}"
            )
            return self._error_response(str(e), process_logs)

    def _generate_personalized_cv(
        self,
        cv_data: Dict,
        job_data: Dict,
        user_profile: Optional[Dict] = None,
        process_logs: Optional[List] = None,
    ) -> Dict:
        """Genera CV personalizado usando IA."""
        try:
            logger.info("🔧 Iniciando generación de CV personalizado")

            # Normalizar cv_data
            cv_data = self._normalize_cv_data(cv_data)

            # Validar que tenga parsed_text
            if (
                not cv_data.get("parsed_text")
                or len(cv_data["parsed_text"].strip()) < 100
            ):
                raise ValueError(
                    "❌ ERROR: El texto del CV original está vacío o es muy corto.\n"
                    "Por favor, recarga el CV o sube uno nuevo."
                )

            # Crear prompt
            prompt = self._create_cv_personalization_prompt(
                cv_data, job_data, user_profile
            )
            logger.info(f"🔧 Prompt creado: {len(prompt)} caracteres")

            if process_logs:
                process_logs.append(f"🔧 Prompt creado ({len(prompt)} caracteres)")

            # Llamar a IA
            ai_response = self._call_ai_for_cv(prompt, process_logs)

            if process_logs:
                process_logs.append(
                    f"🤖 Respuesta recibida ({len(ai_response)} caracteres)"
                )

            # Parsear respuesta
            if process_logs:
                process_logs.append("🔍 Parseando respuesta JSON de IA...")
            personalized_cv = self._parse_ai_cv_response(ai_response)

            if process_logs:
                process_logs.append("✅ JSON parseado correctamente")

            # Validar que tenga datos reales
            if process_logs:
                process_logs.append("🔍 Validando datos del CV...")
            self._validate_cv_has_real_data(personalized_cv)

            if process_logs:
                process_logs.append("✅ Validación exitosa")

            # Optimizar para ATS
            if process_logs:
                process_logs.append("🔧 Optimizando CV para ATS...")
            job_keywords = KeywordExtractor.extract_keywords(job_data["description"])
            personalized_cv = self._optimize_cv_for_ats(
                personalized_cv, job_keywords, cv_data
            )

            if process_logs:
                process_logs.append("✅ Optimización ATS completada")
                process_logs.append("✅ CV personalizado generado exitosamente")

            return personalized_cv

        except Exception as e:
            logger.error(f"Error generando CV personalizado: {e}")
            raise e

    def _create_cv_personalization_prompt(
        self, cv_data: Dict, job_requirements: Dict, user_profile: Optional[Dict] = None
    ) -> str:
        """Crea prompt para personalización de CV."""

        parsed_text = cv_data.get("parsed_text", "")

        # Extraer keywords del puesto
        keywords_list = KeywordExtractor.extract_keywords(
            job_requirements["description"]
        )
        keywords_str = ", ".join(keywords_list[:10])

        # Preparar datos para el prompt
        job_json = {
            "title": job_requirements["title"],
            "description": job_requirements["description"],
            "mail": job_requirements.get("mail", "N/A"),
        }

        user_cv_data = {"parsed_text": parsed_text}

        prompt = f"""ROL: Eres un experto en Recursos Humanos y redacción de CVs ATS-friendly. Actúas como "composer" que adapta un CV existente al texto de un puesto específico SIN inventar datos.

OBJETIVO: Personalizar el CV para el puesto dado y devolver ÚNICAMENTE un JSON válido conforme al esquema indicado.

⚠️ CRÍTICO: DEBES usar TODOS los datos reales del CV original (nombre, email, teléfono, experiencias, proyectos, etc.). NO uses placeholders como "NOMBRE APELLIDO" o "EMPRESA | Cargo". USA LOS DATOS REALES del parsed_text.

DATOS DE ENTRADA:
- JOB: {json.dumps(job_json, ensure_ascii=False)}
- USER_CV: {json.dumps(user_cv_data, ensure_ascii=False)}

⚠️ SI NO ENCUENTRAS UN DATO EN parsed_text, USA null. NUNCA uses placeholders genéricos.

IDIOMA DE SALIDA:
- Si JOB.description está mayormente en español → escribe en español.
- Si está mayormente en otro idioma → escribe en ese idioma.

REGLAS CRÍTICAS:
1) NO INVENTES: Usa EXACTAMENTE la información presente en USER_CV.parsed_text
2) ENLACES: INCLUYE TODOS los enlaces del CV original (LinkedIn, GitHub, Portfolio)
3) FECHAS: Solo usa fechas explícitas del parsed_text
4) EMAILS Y PAÍSES: USA EXACTAMENTE el email y país del CV original
5) FORMATO: Bullets concisos (≤220 caracteres). Sin tablas, emojis ni markdown
6) DEVOLUCIÓN: Responde ÚNICAMENTE con JSON válido

ESTRATEGIA ATS (CRÍTICO - MAXIMIZAR SCORE):
**KEYWORDS CRÍTICAS**: {keywords_str}

⚠️ OBJETIVO: Incluir AL MENOS 80% de estas keywords en el CV (mínimo {int(len(keywords_list) * 0.8)} de {len(keywords_list)})

INSTRUCCIONES PARA KEYWORDS (MÁS AGRESIVAS):
1. REGLA DE ORO: Menciona TODAS las keywords posibles con conexión técnica
2. RELACIONES VÁLIDAS Y SINÓNIMOS:
   - Android/Kotlin → Java, Mobile, Desarrollo móvil, Material Design
   - React → JavaScript, TypeScript, Frontend, Web Development
   - Django/Flask → Python, Backend, APIs REST, Web Framework
   - Git → Version Control, CI/CD, GitLab, GitHub, DevOps
   - SQLite/Room → SQL, Bases de datos, MySQL, PostgreSQL
   - Firebase → Cloud, Backend, AWS, Azure, GCP
   - Jetpack Compose → UI, Frontend, HTML, CSS (conceptos UI)
   
3. DISTRIBUCIÓN AGRESIVA (MÍNIMOS):
   - SUMMARY: AL MENOS 5 keywords principales
   - SKILLS: AL MENOS 12 keywords (incluye sinónimos y expansiones)
   - EXPERIENCE: AL MENOS 4 keywords por experiencia (en bullets)
   - PROJECTS: AL MENOS 6 keywords por proyecto (máxima creatividad)
   
4. HONESTIDAD ESTRATÉGICA FLEXIBLE:
   - Usa: "con conocimientos de", "experiencia en", "familiarizado con"
   - Busca TRANSFERIBILIDAD AGRESIVA:
     * SQLite → MySQL, PostgreSQL, SQL, Bases de datos relacionales
     * Firebase → AWS, Cloud, Backend as a Service
     * Kotlin → Java, JVM, Android Development
     * APIs REST (consumo) → Backend, Node.js, Django, Express
   - Menciona tecnologías relacionadas en PROYECTOS (más flexible)
   
5. TÉCNICAS PARA AUMENTAR SCORE:
   - Repite keywords importantes 2-3 veces en diferentes secciones
   - Usa verbos de acción con keywords: "Implementé Python", "Desarrollé con JavaScript"
   - Agrega keywords en contexto técnico: "arquitectura cloud (AWS/Firebase)"
   - En PROJECTS, menciona "prototipo con X", "evaluando Y", "migración a Z"

FORMATO DE SALIDA:
NOMBRE APELLIDO
Ciudad, País | Teléfono | email@dominio.com | LinkedIn | GitHub | Portfolio

TÍTULO / ROL OBJETIVO

RESUMEN (⚠️ CRÍTICO - INCLUIR 5-7 KEYWORDS)
Profesional con [X] años en [área con keyword]. Especializado en [keyword1, keyword2, keyword3]. Experiencia en [keyword4, keyword5, keyword6]. Logros: [métrica con keyword].

Ejemplo para Desarrollo Web:
"Desarrollador con 3 años en desarrollo web full-stack, especializado en Python, Django, JavaScript y APIs RESTful. Experiencia en bases de datos MySQL/PostgreSQL, frontend HTML5/CSS3 y metodologías ágiles. Desarrollé 10+ proyectos web optimizando rendimiento 40%."

COMPETENCIAS (⚠️ MÍNIMO 12 KEYWORDS)
[Keyword1] · [Keyword2] · [Keyword3] · [Sinónimo1] · [Sinónimo2] · [Expansión1] · [Expansión2] · [Relacionada1] · [Relacionada2] · [Relacionada3] · [Relacionada4] · [Relacionada5]

EXPERIENCIA (⚠️ 4+ KEYWORDS POR BULLET)
EMPRESA | Cargo — Ciudad, País | AAAA-MM – AAAA-MM
• Implementé [keyword1] con [keyword2], logrando [métrica] en [keyword3] y [keyword4]
• Desarrollé [keyword5] usando [keyword6] y [keyword7], reduciendo [X]% en [keyword8]

PROYECTOS (⚠️ 6+ KEYWORDS POR PROYECTO - MÁXIMA CREATIVIDAD)
Proyecto | [keyword1], [keyword2], [keyword3], [keyword4], [keyword5], [keyword6]
• [Problema] → Implementé con [keywords] → [Resultado cuantificable]. Evaluando migración a [keyword relacionada]. URL: [link]

EDUCACIÓN (⚠️ SOLO SI EXISTE EN CV ORIGINAL)
Título — Institución | Ciudad | AAAA-MM – AAAA-MM

⚠️ CRÍTICO: Si NO hay educación en el CV original, el array "education" debe estar VACÍO []. 
NO uses placeholders como "Título — Institución | Ciudad".

IDIOMAS (⚠️ CRÍTICO - NUNCA USAR "(nivel)" GENÉRICO)
[Idioma] ([Nivel específico])

**REGLAS PARA IDIOMAS**:
1. NUNCA uses "(nivel)" genérico - SIEMPRE especifica el nivel real
2. Si el CV tiene nivel explícito → úsalo tal cual (ej: "Nativo", "Avanzado", "B2", "C1")
3. Si NO hay nivel explícito:
   - Idioma del país de origen → "Nativo" (ej: Español para Argentina)
   - Otros idiomas mencionados → "Intermedio" (default razonable)
4. Niveles válidos: "Nativo", "Avanzado", "Intermedio", "Básico", "A1", "A2", "B1", "B2", "C1", "C2"

Ejemplo CORRECTO:
- Español (Nativo)
- Inglés (Intermedio)
- Ruso (Avanzado)

Ejemplo INCORRECTO:
- Español (nivel)  ❌
- Inglés (nivel)   ❌

ESQUEMA JSON:
{{
  "header": {{
    "full_name": string | null,
    "city": string | null,
    "country": string | null,
    "phone": string | null,
    "email": string | null,
    "links": {{
      "linkedin": string | null,
      "portfolio": string | null,
      "github": string | null,
      "other": [string]
    }},
    "target_title": string | null
  }},
  "summary": string,
  "skills": [string],
  "experience": [
    {{
      "company": string | null,
      "role": string | null,
      "city": string | null,
      "country": string | null,
      "start_date": string | null,
      "end_date": string | null,
      "context": string | null,
      "bullets": [string]
    }}
  ],
  "projects": [
    {{
      "name": string,
      "role": string | null,
      "tools": [string],
      "date": string | null,
      "bullet": string,
      "url": string | null
    }}
  ],
  "education": [
    {{
      "degree": string,
      "institution": string,
      "city": string | null,
      "country": string | null,
      "start_date": string | null,
      "end_date": string | null,
      "details": string | null
    }}
  ],  // ⚠️ Si NO hay educación en CV original, este array debe estar VACÍO: "education": []
  "certifications": [
    {{ "name": string, "issuer": string | null, "year": string | null, "id": string | null }}
  ],
  "languages": [
    {{ "language": string, "level": string }}   // ⚠️ CRÍTICO: level NUNCA debe ser "(nivel)" genérico. Usa nivel REAL del CV (ej: "Nativo", "Avanzado", "Intermedio", "Básico", "B2", "C1"). Si no hay nivel explícito en CV: país de origen → "Nativo", otros → "Intermedio" (default razonable)
  ],
  "extras": {{
    "awards": [string],
    "volunteering": [string],
    "availability": string | null,
    "work_permit": [string]
  }},
  "tailoring_meta": {{
    "job_title": string | null,
    "job_description_excerpt": string | null,
    "job_mail": string | null,
    "keywords_matched": [string],
    "alignment_score": integer,
    "warnings": [string]
  }}
}}

VALIDACIÓN:
- JSON sintácticamente válido
- Todas las keys presentes
- summary ≤ 650 caracteres; bullets ≤ 220; skills ≤ 25
- Skills SOLO basadas en CV original

SALIDA:
Devuelve únicamente el JSON final."""

        return prompt

    def _optimize_cv_for_ats(
        self, personalized_cv: Dict, job_keywords: List[str], cv_data: Dict
    ) -> Dict:
        """Valida y limpia el CV generado (MÁS FLEXIBLE)."""
        try:
            original_cv_text = self._extract_text_from_cv_data(cv_data).lower()

            # Diccionario de relaciones técnicas válidas (expandido)
            valid_expansions = {
                "javascript": [
                    "kotlin",
                    "java",
                    "android",
                    "mobile",
                    "frontend",
                    "web",
                ],
                "html5": ["android", "mobile", "ui", "frontend", "jetpack compose"],
                "css3": ["android", "mobile", "ui", "frontend", "material design"],
                "python": ["backend", "api", "desarrollo", "programación"],
                "sql": ["sqlite", "room", "base de datos", "database"],
                "mysql": ["sqlite", "room", "sql", "base de datos"],
                "postgresql": ["sqlite", "room", "sql", "base de datos"],
                "node.js": ["backend", "api", "rest", "servidor"],
                "express": ["backend", "api", "rest", "servidor"],
                "django": ["backend", "api", "rest", "python"],
                "flask": ["backend", "api", "rest", "python"],
                "react": ["frontend", "ui", "javascript", "web"],
                "angular": ["frontend", "ui", "javascript", "web"],
                "vue": ["frontend", "ui", "javascript", "web"],
                "aws": ["cloud", "firebase", "backend", "servidor"],
                "azure": ["cloud", "firebase", "backend", "servidor"],
                "gcp": ["cloud", "firebase", "backend", "servidor"],
                "docker": ["devops", "ci/cd", "deployment"],
                "kubernetes": ["devops", "ci/cd", "deployment", "docker"],
            }

            # 1. Validar skills (MÁS FLEXIBLE)
            current_skills = personalized_cv.get("skills", [])
            validated_skills = []
            removed_count = 0

            for skill in current_skills:
                skill_lower = skill.lower()
                skill_words = skill_lower.split()

                # Buscar en CV original
                found_in_original = any(
                    word in original_cv_text for word in skill_words if len(word) > 3
                )

                # Si no está en original, verificar si es una expansión válida
                is_valid_expansion = False
                if not found_in_original and skill_lower in valid_expansions:
                    # Verificar si alguna de las tecnologías relacionadas está en el CV
                    for related_tech in valid_expansions[skill_lower]:
                        if related_tech in original_cv_text:
                            is_valid_expansion = True
                            logger.info(
                                f"✅ Skill '{skill}' aceptada - expansión válida de '{related_tech}'"
                            )
                            break

                # Si está en keywords del job, ser más flexible
                is_job_keyword = skill_lower in [kw.lower() for kw in job_keywords]

                if (
                    found_in_original
                    or is_valid_expansion
                    or (is_job_keyword and len(validated_skills) < 15)
                ):
                    validated_skills.append(skill)
                else:
                    logger.warning(
                        f"⚠️ Skill '{skill}' removida - no aparece en CV ni es expansión válida"
                    )
                    removed_count += 1

            personalized_cv["skills"] = validated_skills[:25]

            if removed_count > 0:
                logger.info(
                    f"✅ {removed_count} skills inventadas removidas. Skills validadas: {len(validated_skills)}"
                )

            # 2. Limpiar ubicaciones duplicadas
            for exp in personalized_cv.get("experience", []):
                location = exp.get("location", "")
                parts = [p.strip() for p in location.split(",")]
                if len(parts) >= 2 and parts[-1] == parts[-2]:
                    exp["location"] = ", ".join(parts[:-1])

            # 3. Truncar bullets largos
            for exp in personalized_cv.get("experience", []):
                exp["bullets"] = [
                    bullet[:217] + "..." if len(bullet) > 220 else bullet
                    for bullet in exp.get("bullets", [])
                ]

            return personalized_cv

        except Exception as e:
            logger.error(f"Error optimizando CV para ATS: {e}")
            return personalized_cv

    def _validate_cv_has_real_data(self, personalized_cv: Dict) -> None:
        """Valida que el CV tenga datos reales y no placeholders."""
        errors = []

        # Validar header
        header = personalized_cv.get("header", {})
        full_name = header.get("full_name", "")
        if not full_name or re.search(
            r"NOMBRE|APELLIDO|nombre apellido", full_name, re.IGNORECASE
        ):
            errors.append("❌ Nombre: placeholder detectado")

        email = header.get("email", "")
        if not email or "@" not in email:
            errors.append("❌ Email: no válido o vacío")

        # Validar summary
        summary = personalized_cv.get("summary", "")
        if not summary or len(summary.strip()) < 50:
            errors.append("❌ Summary: vacío o muy corto")
        elif re.search(
            r"Profesional con \[X\]|Foco en \[competencias|Logros: \[métrica", summary
        ):
            errors.append("❌ Summary: contiene placeholders sin reemplazar")

        # Validar experience
        experiences = personalized_cv.get("experience", [])
        if experiences:
            for i, exp in enumerate(experiences[:3]):
                company = exp.get("company", "")
                role = exp.get("role", "")

                if not company or re.search(r"EMPRESA|empresa", company, re.IGNORECASE):
                    errors.append(f"❌ Experiencia #{i+1}: empresa es placeholder")

                if not role or re.search(r"Cargo|cargo", role, re.IGNORECASE):
                    errors.append(f"❌ Experiencia #{i+1}: cargo es placeholder")

        if errors:
            error_msg = (
                "❌ ERROR: La IA generó un CV con placeholders.\n\n"
                "Problemas:\n" + "\n".join(errors) + "\n\n"
                "Por favor, contacta al administrador."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("✅ Validación exitosa: CV contiene datos reales")

    def _parse_ai_cv_response(self, ai_response: str) -> Dict:
        """Parsea la respuesta de IA para extraer CV personalizado."""
        try:
            logger.info(f"🔍 Parseando respuesta de IA ({len(ai_response)} caracteres)")

            cleaned_response = ai_response.strip()

            # Remover bloques markdown
            if "```" in cleaned_response:
                logger.info("🔍 Detectado bloque markdown, extrayendo JSON...")
                code_match = re.search(
                    r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_response, re.DOTALL
                )
                if code_match:
                    cleaned_response = code_match.group(1).strip()
                else:
                    cleaned_response = re.sub(r"```(?:json)?", "", cleaned_response)
                    cleaned_response = re.sub(r"```", "", cleaned_response).strip()

            # Intentar parsear JSON directo
            if cleaned_response.startswith("{"):
                try:
                    parsed = json.loads(cleaned_response)
                    required_keys = ["header", "summary", "skills", "experience"]
                    if all(key in parsed for key in required_keys):
                        logger.info("✅ JSON válido parseado")
                        return parsed
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Error parseando JSON: {e}")

            # Buscar JSON con balance de llaves
            logger.info("🔍 Buscando JSON con balance de llaves...")
            start_idx = cleaned_response.find("{")
            if start_idx != -1:
                brace_count = 0
                in_string = False
                escape_next = False

                for i in range(start_idx, len(cleaned_response)):
                    char = cleaned_response[i]

                    if char == '"' and not escape_next:
                        in_string = not in_string
                    elif char == "\\" and not escape_next:
                        escape_next = True
                        continue

                    escape_next = False

                    if not in_string:
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1

                            if brace_count == 0:
                                json_str = cleaned_response[start_idx : i + 1]
                                try:
                                    parsed = json.loads(json_str)
                                    if all(
                                        key in parsed
                                        for key in [
                                            "header",
                                            "summary",
                                            "skills",
                                            "experience",
                                        ]
                                    ):
                                        logger.info("✅ JSON balanceado válido")
                                        return parsed
                                except json.JSONDecodeError:
                                    pass
                                break

            # Si llegamos aquí, el JSON está malformado
            raise ValueError(
                "❌ La IA generó un JSON incompleto o malformado. "
                "Por favor, intenta nuevamente."
            )

        except Exception as e:
            logger.error(f"❌ Error parseando respuesta de IA: {e}")
            raise e

    def _call_ai_for_cv(self, prompt: str, process_logs: Optional[List] = None) -> str:
        """Llama a los proveedores de IA para generar CV."""
        try:
            from matching.models import AIConfiguration

            config = AIConfiguration.objects.first()

            if not config:
                raise Exception("No hay configuración de IA disponible")

            # Intentar OpenAI primero
            openai_error = None
            if config.openai_enabled and config.openai_api_key:
                try:
                    if process_logs:
                        process_logs.append("🤖 Llamando a OpenAI...")

                    import openai

                    decrypted_key = config._decrypt_key(config.openai_api_key)
                    openai.api_key = decrypted_key

                    response = openai.chat.completions.create(
                        model=config.openai_model or "gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": "Eres un experto en RR.HH. que genera CVs personalizados. Responde ÚNICAMENTE con JSON válido.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=8000,
                        temperature=0.7,
                    )

                    response_text = response.choices[0].message.content
                    logger.info(
                        f"✅ CV generado con OpenAI: {len(response_text)} caracteres"
                    )
                    if process_logs:
                        process_logs.append(
                            f"✅ OpenAI respondió exitosamente ({len(response_text)} caracteres)"
                        )
                    return response_text

                except Exception as e:
                    openai_error = str(e)
                    logger.warning(f"❌ Error con OpenAI: {openai_error}")

                    if process_logs:
                        if "429" in openai_error or "quota" in openai_error.lower():
                            process_logs.append("⚠️ OpenAI: Cuota agotada")
                        elif "401" in openai_error or "invalid" in openai_error.lower():
                            process_logs.append("⚠️ OpenAI: API key inválida")
                        else:
                            process_logs.append(f"⚠️ OpenAI: {openai_error[:100]}")

                    # SIEMPRE intentar con Anthropic si OpenAI falla
                    logger.info(
                        "🔄 OpenAI falló, intentando con Anthropic como fallback..."
                    )
                    if process_logs:
                        process_logs.append("🔄 Intentando con Anthropic...")

            # Fallback a Anthropic
            if config.anthropic_enabled and config.anthropic_api_key:
                try:
                    logger.info("🔄 Usando Anthropic...")
                    if process_logs:
                        process_logs.append("🤖 Llamando a Anthropic...")

                    import anthropic

                    decrypted_key = config._decrypt_key(config.anthropic_api_key)
                    client = anthropic.Anthropic(api_key=decrypted_key)

                    response = client.messages.create(
                        model=config.anthropic_model or "claude-3-haiku-20240307",
                        max_tokens=8000,
                        temperature=0.7,
                        messages=[{"role": "user", "content": prompt}],
                    )

                    response_text = response.content[0].text
                    logger.info(
                        f"✅ CV generado con Anthropic: {len(response_text)} caracteres"
                    )
                    if process_logs:
                        process_logs.append(
                            f"✅ Anthropic respondió exitosamente ({len(response_text)} caracteres)"
                        )
                    return response_text

                except Exception as e:
                    anthropic_error = str(e)
                    logger.error(f"❌ Error con Anthropic: {anthropic_error}")
                    if process_logs:
                        process_logs.append(f"❌ Anthropic: {anthropic_error[:100]}")

                    # Si ambos proveedores fallaron, lanzar error combinado
                    if openai_error:
                        combined_error = f"Error de IA: {openai_error}"
                        raise Exception(combined_error)
                    else:
                        raise Exception(f"Error de IA: {anthropic_error}")

            # Si OpenAI falló y Anthropic no está configurado
            if openai_error:
                raise Exception(f"Error de IA: {openai_error}")

            raise Exception("No hay proveedores de IA disponibles")

        except Exception as e:
            logger.error(f"Error llamando a IA: {e}")
            raise e

    def _create_personalized_file(
        self, user_cv: UserCV, personalized_cv: Dict, job_posting: JobPosting
    ) -> Optional[str]:
        """Crea archivo personalizado del CV."""
        try:
            # Por ahora, retornar el archivo original
            # TODO: Implementar generación de PDF personalizado
            if user_cv.original_file:
                return user_cv.original_file.path
            return None
        except Exception as e:
            logger.error(f"Error creando archivo personalizado: {e}")
            return None

    def _calculate_ats_score(
        self, cv_data: Dict, job_data: Dict, personalized_cv: Dict
    ) -> Dict:
        """Calcula score ATS usando el módulo unificado."""
        try:
            cv_text = self._extract_text_from_cv_data(cv_data)

            return ats_matcher.calculate_score(
                cv_text=cv_text,
                job_description=job_data["description"],
                cv_structured=personalized_cv,
            )
        except Exception as e:
            logger.error(f"Error calculando score ATS: {e}")
            return {
                "total": 0,
                "breakdown": {},
                "keywords_found": 0,
                "keywords_total": 0,
                "missing_keywords": [],
                "job_keywords": [],
            }

    # === MÉTODOS AUXILIARES ===

    def _normalize_cv_data(self, cv_data) -> Dict:
        """Normaliza cv_data a Dict."""
        if isinstance(cv_data, str):
            logger.warning("⚠️ cv_data recibido como string, convirtiendo a dict")
            return {"parsed_text": cv_data}
        elif isinstance(cv_data, dict):
            return cv_data
        else:
            raise ValueError(f"❌ cv_data tiene tipo inválido: {type(cv_data)}")

    def _extract_text_from_cv_data(self, cv_data) -> str:
        """Extrae texto del CV de forma segura."""
        if isinstance(cv_data, str):
            return cv_data
        elif isinstance(cv_data, dict):
            return cv_data.get("parsed_text", "")
        return ""

    # DEPRECATED: Ya no se usa porque penaliza artificialmente el score
    # Se mantiene comentado por si se necesita en el futuro
    # def _create_minimal_cv_structure_from_text(self, cv_data: Dict) -> Dict:
    #     """Crea estructura mínima del CV desde texto plano."""
    #     cv_text = self._extract_text_from_cv_data(cv_data)
    #     return {
    #         'skills': [],
    #         'summary': cv_text[:500],
    #         'experience': [],
    #         'projects': []
    #     }

    def _error_response(self, error_msg: str, process_logs: List[str]) -> Dict:
        """Genera respuesta de error estandarizada."""
        return {
            "success": False,
            "error": error_msg,
            "personalized_cv": None,
            "personalized_file": None,
            "job_requirements": {},
            "cv_data": {},
            "match_score": 0,
            "process_logs": process_logs,
        }


# Instancia global del servicio
cv_personalization_service = CVPersonalizationService()
