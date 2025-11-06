"""
Servicio compartido para generación de cartas de presentación con IA.
"""
import logging

from .ai_service import ai_email_service

logger = logging.getLogger(__name__)


def generate_cover_letter_with_ai(
    user_name,
    job_title,
    job_description,
    cv_summary,
    email_template='base'
):
    """
    Genera una carta de presentación personalizada con IA según el template seleccionado.
    
    Args:
        user_name: Nombre del candidato
        job_title: Título del puesto
        job_description: Descripción del puesto
        cv_summary: Resumen del CV (primeros 500 caracteres)
        email_template: Template a usar (base, formal, creative, technical)
    
    Returns:
        str: Carta de presentación generada
    """
    
    # Definir estilos por template
    template_styles = {
        'base': {
            'tono': 'profesional y equilibrado',
            'estilo': 'formal pero cálido',
            'longitud': '250-300 palabras',
            'enfoque': 'Destacar coincidencias entre perfil y puesto de forma balanceada',
            'saludo': 'Estimado/a equipo de contratación,',
            'despedida': 'Atentamente,'
        },
        'formal': {
            'tono': 'muy formal y corporativo',
            'estilo': 'serio, profesional y respetuoso',
            'longitud': '200-250 palabras',
            'enfoque': 'Énfasis en experiencia, logros cuantificables y trayectoria profesional. Usar lenguaje corporativo.',
            'saludo': 'Estimado/a equipo de contratación,',
            'despedida': 'Atentamente,'
        },
        'creative': {
            'tono': 'entusiasta, dinámico y apasionado',
            'estilo': 'creativo pero profesional, con energía',
            'longitud': '300-350 palabras',
            'enfoque': 'Mostrar pasión por el rol, innovación, fit cultural y entusiasmo genuino. Usar lenguaje más cercano.',
            'saludo': 'Estimado/a equipo de contratación,',
            'despedida': 'Con entusiasmo,'
        },
        'technical': {
            'tono': 'técnico, preciso y directo',
            'estilo': 'orientado a resultados y stack tecnológico',
            'longitud': '250-300 palabras',
            'enfoque': 'Destacar tecnologías específicas, arquitecturas, métricas de rendimiento y proyectos técnicos. Usar terminología técnica.',
            'saludo': 'Estimado/a equipo de contratación,',
            'despedida': 'Saludos,'
        }
    }
    
    style = template_styles.get(email_template, template_styles['base'])
    
    prompt = f"""Genera una carta de presentación personalizada para una postulación de trabajo.

DATOS DEL CANDIDATO:
- Nombre: {user_name}
- Puesto al que postula: {job_title}
- Descripción del puesto: {job_description[:300]}
- Resumen del CV: {cv_summary}

TEMPLATE SELECCIONADO: "{email_template.upper()}"
Debes adaptar completamente el tono y contenido a este template:

- Tono: {style['tono']}
- Estilo: {style['estilo']}
- Longitud: {style['longitud']}
- Enfoque: {style['enfoque']}

INSTRUCCIONES ESPECÍFICAS POR TEMPLATE:

{_get_template_specific_instructions(email_template)}

INSTRUCCIONES GENERALES:
- Expresar interés genuino por el puesto
- Incluir llamado a la acción apropiado al template
- En español
- Sin inventar datos, usar SOLO lo proporcionado
- Adaptar COMPLETAMENTE el tono al template seleccionado

FORMATO REQUERIDO:
- NO incluyas títulos, encabezados ni formato Markdown (como "# Carta de Presentación")
- Comienza directamente con el saludo
- Usa SOLO texto plano, sin asteriscos (**) ni símbolos de formato
- La carta debe tener esta estructura EXACTA:

{style['saludo']}

[Cuerpo de la carta adaptado al template {email_template}]

{style['despedida']}
{user_name}
"""
    
    try:
        # Generar con IA (con fallback automático OpenAI -> Anthropic)
        # Retorna tupla: (texto, usó_fallback)
        result, used_fallback = ai_email_service.generate_text_and_track_fallback(prompt)
        
        # Determinar qué proveedor se usó realmente
        actual_provider = 'anthropic' if used_fallback else 'openai'
        
        logger.info(f"✅ Carta generada con IA (template: {email_template}, proveedor: {actual_provider})")
        return result, actual_provider
    except Exception as e:
        logger.error(f"❌ Error generando carta con IA: {e}")
        # Fallback: carta genérica adaptada al template
        return _get_fallback_letter(user_name, job_title, email_template), 'fallback'


def _get_template_specific_instructions(template):
    """Retorna instrucciones específicas para cada template."""
    instructions = {
        'base': """
- Usar lenguaje profesional estándar
- Balance entre formalidad y calidez
- Mencionar 2-3 puntos clave del CV relevantes al puesto
- Cerrar con solicitud de entrevista de forma cordial
""",
        'formal': """
- Usar frases como "Por la presente", "Me permito expresar", "Quedo a su disposición"
- Enfatizar años de experiencia y logros medibles
- Mencionar trayectoria profesional de forma estructurada
- Evitar contracciones y lenguaje coloquial
- Cerrar con "Quedo a su disposición para una entrevista formal"
""",
        'creative': """
- Usar frases como "¡Me emociona!", "Me apasiona", "Estoy entusiasmado/a"
- Mostrar personalidad y fit cultural
- Mencionar por qué la empresa/proyecto te atrae específicamente
- Usar lenguaje más cercano y dinámico
- Cerrar con pregunta abierta tipo "¿Cuándo podemos charlar sobre...?"
""",
        'technical': """
- Listar stack tecnológico específico (lenguajes, frameworks, herramientas)
- Mencionar arquitecturas, patrones de diseño, metodologías
- Incluir métricas técnicas (uptime, performance, reducción de tiempos)
- Usar bullet points si es apropiado
- Mencionar repositorios/proyectos técnicos
- Cerrar con "Disponible para discusión técnica" o similar
"""
    }
    return instructions.get(template, instructions['base'])


def _get_fallback_letter(user_name, job_title, template):
    """Genera carta de fallback adaptada al template."""
    fallbacks = {
        'base': f"""Estimado/a equipo de contratación,

Me dirijo a ustedes para expresar mi interés en la posición de {job_title}.

Con mi experiencia y habilidades técnicas, creo que puedo aportar valor significativo a su equipo. Adjunto mi CV para su consideración.

Quedo a disposición para una entrevista en la que podamos discutir cómo mi perfil se alinea con sus necesidades.

Atentamente,
{user_name}
""",
        'formal': f"""Estimado/a equipo de contratación,

Por la presente, me permito expresar mi formal interés en la posición de {job_title}.

Mi trayectoria profesional y experiencia técnica me posicionan como un candidato calificado para contribuir efectivamente a su organización.

Adjunto mi currículum vitae para su consideración y quedo a su disposición para una entrevista formal.

Atentamente,
{user_name}
""",
        'creative': f"""Estimado/a equipo de contratación,

¡Me entusiasma enormemente la oportunidad de unirme a su equipo como {job_title}!

Mi pasión por la tecnología y mi experiencia creando soluciones innovadoras me motivan a contribuir al éxito de sus proyectos.

¿Cuándo podemos charlar sobre cómo puedo aportar valor a su equipo?

Con entusiasmo,
{user_name}
""",
        'technical': f"""Estimado/a equipo de contratación,

Mi experiencia técnica y stack tecnológico me posicionan idealmente para el rol de {job_title}.

Adjunto mi CV con detalles técnicos de proyectos y experiencia relevante para su revisión.

Disponible para discusión técnica.

Saludos,
{user_name}
"""
    }
    return fallbacks.get(template, fallbacks['base'])


