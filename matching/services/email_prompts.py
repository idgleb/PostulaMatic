"""
Templates de prompts para generación de emails personalizados.
"""

from typing import Dict, List


class EmailPromptTemplates:
    """Templates de prompts para diferentes tipos de emails."""
    
    @staticmethod
    def get_base_template() -> str:
        """Template base para generación de emails."""
        return """
Genera un email profesional para postular a un trabajo con el siguiente formato:

ASUNTO: [Asunto profesional y atractivo]
CUERPO: [Cuerpo del email]

Información del puesto:
{job_description}

Mis habilidades relevantes:
{cv_skills}

Mi nombre para mostrar:
{display_name}

Requisitos generales:
- El email debe ser profesional y conciso
- Menciona habilidades específicas que coincidan con el puesto
- Muestra interés genuino por la posición
- Mantén un tono profesional pero cercano
- Máximo 200 palabras en el cuerpo
- Incluye una llamada a la acción clara
"""

    @staticmethod
    def get_formal_template() -> str:
        """Template para emails más formales."""
        return """
Genera un email formal para postular a un trabajo con el siguiente formato:

ASUNTO: [Asunto formal y profesional]
CUERPO: [Cuerpo del email]

Información del puesto:
{job_description}

Mis habilidades relevantes:
{cv_skills}

Mi nombre para mostrar:
{display_name}

Requisitos específicos:
- Usa un tono muy formal y respetuoso
- Estructura clásica: saludo, presentación, habilidades, interés, cierre
- Menciona específicamente cómo tus habilidades se alinean con el puesto
- Demuestra conocimiento sobre la empresa/rol
- Termina con una llamada a la acción profesional
- Máximo 250 palabras
"""

    @staticmethod
    def get_creative_template() -> str:
        """Template para emails más creativos."""
        return """
Genera un email creativo pero profesional para postular a un trabajo con el siguiente formato:

ASUNTO: [Asunto creativo y memorable]
CUERPO: [Cuerpo del email]

Información del puesto:
{job_description}

Mis habilidades relevantes:
{cv_skills}

Mi nombre para mostrar:
{display_name}

Requisitos específicos:
- Usa un tono más cercano y personal
- Puedes ser creativo en el asunto y apertura
- Muestra personalidad pero mantén profesionalismo
- Menciona una experiencia o proyecto específico
- Demuestra pasión por el rol
- Máximo 180 palabras
"""

    @staticmethod
    def get_technical_template() -> str:
        """Template para puestos técnicos."""
        return """
Genera un email técnico para postular a un puesto de desarrollo/tecnología con el siguiente formato:

ASUNTO: [Asunto técnico y específico]
CUERPO: [Cuerpo del email]

Información del puesto:
{job_description}

Mis habilidades técnicas:
{cv_skills}

Mi nombre para mostrar:
{display_name}

Requisitos específicos:
- Enfócate en habilidades técnicas específicas
- Menciona tecnologías, frameworks, herramientas
- Incluye métricas o logros técnicos si es relevante
- Demuestra experiencia práctica
- Usa terminología técnica apropiada
- Máximo 200 palabras
"""

    @staticmethod
    def get_startup_template() -> str:
        """Template para startups o empresas pequeñas."""
        return """
Genera un email dinámico para postular a una startup o empresa pequeña con el siguiente formato:

ASUNTO: [Asunto dinámico y directo]
CUERPO: [Cuerpo del email]

Información del puesto:
{job_description}

Mis habilidades relevantes:
{cv_skills}

Mi nombre para mostrar:
{display_name}

Requisitos específicos:
- Usa un tono más directo y dinámico
- Muestra iniciativa y proactividad
- Menciona cómo puedes contribuir inmediatamente
- Demuestra flexibilidad y adaptabilidad
- Enfatiza tu capacidad de trabajar en equipo pequeño
- Máximo 150 palabras
"""

    @staticmethod
    def get_corporate_template() -> str:
        """Template para empresas corporativas grandes."""
        return """
Genera un email corporativo para postular a una empresa grande con el siguiente formato:

ASUNTO: [Asunto corporativo y profesional]
CUERPO: [Cuerpo del email]

Información del puesto:
{job_description}

Mis habilidades relevantes:
{cv_skills}

Mi nombre para mostrar:
{display_name}

Requisitos específicos:
- Usa un tono muy profesional y corporativo
- Estructura clara y organizada
- Menciona experiencia en entornos corporativos si aplica
- Demuestra capacidad de trabajar en equipos grandes
- Enfatiza resultados y logros cuantificables
- Máximo 220 palabras
"""

    @classmethod
    def get_template(cls, template_type: str) -> str:
        """Obtiene un template específico por tipo."""
        templates = {
            'base': cls.get_base_template(),
            'formal': cls.get_formal_template(),
            'creative': cls.get_creative_template(),
            'technical': cls.get_technical_template(),
            'startup': cls.get_startup_template(),
            'corporate': cls.get_corporate_template()
        }
        return templates.get(template_type, cls.get_base_template())
    
    @classmethod
    def get_available_templates(cls) -> List[str]:
        """Retorna lista de templates disponibles."""
        return ['base', 'formal', 'creative', 'technical', 'startup', 'corporate']


class PromptCustomizer:
    """Utilidades para personalizar prompts."""
    
    @staticmethod
    def add_company_info(prompt: str, company_name: str = "", industry: str = "") -> str:
        """Agrega información de la empresa al prompt."""
        if company_name or industry:
            company_info = f"\nInformación de la empresa:\n"
            if company_name:
                company_info += f"- Nombre: {company_name}\n"
            if industry:
                company_info += f"- Industria: {industry}\n"
            return prompt + company_info
        return prompt
    
    @staticmethod
    def add_urgency(prompt: str, is_urgent: bool = False) -> str:
        """Agrega urgencia al prompt si es necesario."""
        if is_urgent:
            return prompt + "\n- Menciona disponibilidad inmediata si es relevante"
        return prompt
    
    @staticmethod
    def add_location(prompt: str, location: str = "") -> str:
        """Agrega información de ubicación al prompt."""
        if location:
            return prompt + f"\n- Ubicación del puesto: {location}"
        return prompt
    
    @staticmethod
    def add_salary_expectation(prompt: str, salary_range: str = "") -> str:
        """Agrega expectativas salariales al prompt si es apropiado."""
        if salary_range:
            return prompt + f"\n- Rango salarial mencionado: {salary_range}"
        return prompt


class EmailPersonalizationData:
    """Estructura para datos de personalización de emails."""
    
    def __init__(
        self,
        job_description: str,
        cv_skills: Dict,
        user_profile: Dict,
        template_type: str = "base",
        custom_instructions: str = "",
        company_info: Dict = None,
        job_metadata: Dict = None
    ):
        self.job_description = job_description
        self.cv_skills = cv_skills
        self.user_profile = user_profile
        self.template_type = template_type
        self.custom_instructions = custom_instructions
        self.company_info = company_info or {}
        self.job_metadata = job_metadata or {}
    
    def build_prompt(self) -> str:
        """Construye el prompt final personalizado."""
        # Obtener template base
        prompt = EmailPromptTemplates.get_template(self.template_type)
        
        # Agregar información de empresa
        prompt = PromptCustomizer.add_company_info(
            prompt, 
            self.company_info.get('name', ''),
            self.company_info.get('industry', '')
        )
        
        # Agregar ubicación
        prompt = PromptCustomizer.add_location(
            prompt,
            self.job_metadata.get('location', '')
        )
        
        # Agregar urgencia
        prompt = PromptCustomizer.add_urgency(
            prompt,
            self.job_metadata.get('urgent', False)
        )
        
        # Agregar instrucciones personalizadas
        if self.custom_instructions:
            prompt += f"\nInstrucciones personalizadas: {self.custom_instructions}"
        
        # Formatear con datos
        skills_text = ", ".join(self.cv_skills.get('skills', []))
        display_name = self.user_profile.get('display_name', '')
        
        return prompt.format(
            job_description=self.job_description,
            cv_skills=skills_text,
            display_name=display_name
        )

