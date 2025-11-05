"""
Servicio de IA para generación de emails personalizados.
Maneja múltiples proveedores de IA y genera contenido personalizado.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from dataclasses import dataclass

import openai
import anthropic
from django.conf import settings
from matching.utils.anthropic_model_finder import create_model_finder

logger = logging.getLogger(__name__)


@dataclass
class EmailContent:
    """Contenido generado para un email."""
    subject: str
    body: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    error: Optional[str] = None


class AIProvider(ABC):
    """Interfaz abstracta para proveedores de IA."""
    
    @abstractmethod
    def generate_email_content(
        self, 
        job_description: str,
        cv_skills: Dict[str, Any],
        user_profile: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> EmailContent:
        """Genera contenido de email personalizado."""
        pass
    
    @abstractmethod
    def generate_with_vision(self, prompt: str, image_base64: str) -> str:
        """Genera texto a partir de una imagen usando visión."""
        pass
    
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        """Genera texto a partir de un prompt."""
        pass


class OpenAIProvider(AIProvider):
    """Proveedor OpenAI para generación de emails."""
    
    def __init__(self):
        # No cachear nada para reflejar cambios en tiempo real
        pass
    
    def _get_config(self):
        """Obtiene la configuración de IA desde la base de datos (sin caché)."""
        # IMPORTANTE: NO cachear la configuración para que siempre use la versión más reciente
        # Esto evita problemas cuando el usuario actualiza la API key en el admin
        try:
            from matching.models import AIConfiguration
            return AIConfiguration.get_config()
        except Exception as e:
            logger.error(f"Error obteniendo configuración IA: {e}")
            return None
    
    @property
    def client(self):
        """Lazy initialization del cliente OpenAI (sin caché para reflejar cambios de API key)."""
        # IMPORTANTE: Siempre crear un nuevo cliente para reflejar cambios en la API key
        # Sin esto, si el usuario actualiza la API key, seguiría usando la antigua
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("OpenAI API key no está configurada")
        # Timeouts cortos + pocos reintentos para evitar kills del worker
        return openai.OpenAI(api_key=api_key, timeout=20, max_retries=1)
    
    def _get_api_key(self):
        """Obtiene la API key de OpenAI desde la configuración."""
        config = self._get_config()
        if config and config.openai_enabled:
            return config.get_openai_key()
        # Fallback a variables de entorno
        return os.getenv('OPENAI_API_KEY')
    
    @property
    def model(self):
        """Obtiene el modelo de OpenAI desde la configuración (sin caché)."""
        # IMPORTANTE: Siempre obtener el modelo actual para reflejar cambios
        config = self._get_config()
        if config and config.openai_enabled:
            return config.openai_model
        else:
            # Fallback a variables de entorno
            return os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    def generate_email_content(
        self, 
        job_description: str,
        cv_skills: Dict[str, Any],
        user_profile: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> EmailContent:
        """Genera contenido de email usando OpenAI."""
        try:
            # Construir prompt personalizado
            prompt = self._build_prompt(
                job_description, cv_skills, user_profile, custom_prompt
            )
            
            # Llamar a OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente experto en recursos humanos que genera emails profesionales para postulaciones de trabajo. Genera contenido personalizado, profesional y convincente."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1000,
                temperature=0.7,
                timeout=20
            )
            
            # Extraer contenido de la respuesta
            content = response.choices[0].message.content
            
            # Parsear subject y body (asumiendo formato específico)
            subject, body = self._parse_email_content(content)
            
            return EmailContent(
                subject=subject,
                body=body,
                provider="openai",
                model=self.model,
                tokens_used=response.usage.total_tokens if response.usage else None
            )
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error generando email con OpenAI: {error_msg}")
            
            # Detectar errores específicos de cuota
            if "429" in error_msg or "quota" in error_msg.lower() or "exceeded" in error_msg.lower():
                error_msg = f"Error de cuota OpenAI: {error_msg}"
            
            return EmailContent(
                subject="",
                body="",
                provider="openai",
                model=self.model,
                error=error_msg
            )
    
    def _build_prompt(
        self, 
        job_description: str,
        cv_skills: Dict[str, Any],
        user_profile: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> str:
        """Construye el prompt para la generación de email."""
        # Si hay custom_prompt, usarlo como prompt principal
        if custom_prompt:
            logger.info(f"🔧 Usando custom_prompt para OpenAI: {len(custom_prompt)} caracteres")
            return custom_prompt
        
        # Si no hay custom_prompt, usar el prompt base para emails
        skills_text = ", ".join(cv_skills.get('skills', []))
        display_name = user_profile.get('display_name', '')
        
        base_prompt = f"""
Genera un email profesional para postular a un trabajo con el siguiente formato:

ASUNTO: [Asunto profesional y atractivo]
CUERPO: [Cuerpo del email]

Información del puesto:
{job_description}

Mis habilidades relevantes:
{skills_text}

Mi nombre para mostrar:
{display_name}

Requisitos:
- El email debe ser profesional y conciso
- Menciona habilidades específicas que coincidan con el puesto
- Muestra interés genuino por la posición
- Mantén un tono profesional pero cercano
- Máximo 200 palabras en el cuerpo
"""
        
        return base_prompt
    
    def _parse_email_content(self, content: str) -> tuple[str, str]:
        """Parsea el contenido generado para extraer subject y body."""
        lines = content.strip().split('\n')
        subject = ""
        body_lines = []
        
        in_body = False
        for line in lines:
            line = line.strip()
            if line.startswith('ASUNTO:'):
                subject = line.replace('ASUNTO:', '').strip()
            elif line.startswith('CUERPO:'):
                in_body = True
                body_content = line.replace('CUERPO:', '').strip()
                if body_content:
                    body_lines.append(body_content)
            elif in_body and line:
                body_lines.append(line)
        
        # Si no se encontró formato específico, usar todo como body
        if not subject and not body_lines:
            # Intentar extraer subject de la primera línea
            first_line = lines[0] if lines else ""
            if len(first_line) < 100:  # Probablemente es un subject
                subject = first_line
                body_lines = lines[1:] if len(lines) > 1 else []
            else:
                body_lines = lines
        
        body = '\n'.join(body_lines).strip()
        
        # Fallbacks
        if not subject:
            subject = "Postulación de trabajo"
        if not body:
            body = content.strip()
        
        return subject, body
    
    def generate_with_vision(self, prompt: str, image_base64: str) -> str:
        """Genera texto a partir de una imagen usando visión."""
        try:
            if not self._client:
                self._initialize_client()
            
            response = self._client.chat.completions.create(
                model="gpt-4o",  # Modelo con visión
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.1,
                timeout=20
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generando texto con visión OpenAI: {e}")
            # Formatear el error específico de OpenAI
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower():
                error_msg = "❌ OpenAI: Cuota agotada - Verifica tu plan y facturación"
            elif "401" in error_str or "invalid_api_key" in error_str.lower():
                error_msg = "❌ OpenAI: API key inválida - Verifica tu clave de API"
            elif "403" in error_str or "forbidden" in error_str.lower():
                error_msg = "❌ OpenAI: Acceso denegado - Verifica permisos de tu cuenta"
            elif "500" in error_str or "internal" in error_str.lower():
                error_msg = "❌ OpenAI: Error interno del servidor"
            elif "timeout" in error_str.lower():
                error_msg = "❌ OpenAI: Tiempo de espera agotado"
            else:
                error_msg = f"❌ OpenAI: {error_str}"
            raise Exception(error_msg)
    
    def generate_text(self, prompt: str) -> str:
        """Genera texto a partir de un prompt."""
        try:
            if not self._client:
                self._initialize_client()
            
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1,
                timeout=20
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generando texto OpenAI: {e}")
            raise
    
    def _initialize_client(self):
        """Inicializa el cliente OpenAI."""
        try:
            config = self._get_config()
            if config and config.openai_enabled:
                api_key = config.get_openai_key()
                if api_key:
                    self._client = openai.OpenAI(api_key=api_key)
                    self._model = config.openai_model or "gpt-4o"
                    logger.info(f"✅ Cliente OpenAI inicializado con modelo: {self._model}")
                else:
                    logger.warning("⚠️ OpenAI habilitado pero sin API key")
            else:
                logger.warning("⚠️ OpenAI no habilitado en configuración")
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente OpenAI: {e}")


class AnthropicProvider(AIProvider):
    """Proveedor Anthropic para generación de emails."""
    
    def __init__(self):
        # No cachear nada para reflejar cambios en tiempo real
        self._model_finder = None  # Este sí se cachea porque no cambia
    
    def _get_config(self):
        """Obtiene la configuración de IA desde la base de datos (sin caché)."""
        # IMPORTANTE: NO cachear la configuración para que siempre use la versión más reciente
        # Esto evita problemas cuando el usuario actualiza la API key en el admin
        try:
            from matching.models import AIConfiguration
            return AIConfiguration.get_config()
        except Exception as e:
            logger.error(f"Error obteniendo configuración IA: {e}")
            return None
    
    @property
    def client(self):
        """Lazy initialization del cliente Anthropic (sin caché para reflejar cambios de API key)."""
        # IMPORTANTE: Siempre crear un nuevo cliente para reflejar cambios en la API key
        # Sin esto, si el usuario actualiza la API key, seguiría usando la antigua
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError("Anthropic API key no está configurada")
        # Reducimos el timeout estricto para visión a 8s usando el cliente por defecto
        # (usaremos timeout por llamada en messages.create)
        return anthropic.Anthropic(api_key=api_key)
    
    def _get_api_key(self):
        """Obtiene la API key de Anthropic desde la configuración."""
        config = self._get_config()
        if config and config.anthropic_enabled:
            return config.get_anthropic_key()
        # Fallback a variables de entorno
        return os.getenv('ANTHROPIC_API_KEY')
    
    @property
    def model(self):
        """Obtiene el modelo de Anthropic desde la configuración (sin caché)."""
        # IMPORTANTE: Siempre obtener el modelo actual para reflejar cambios
        config = self._get_config()
        if config and config.anthropic_enabled:
            return config.anthropic_model
        else:
            # Fallback a variables de entorno
            return os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')
    
    def generate_email_content(
        self, 
        job_description: str,
        cv_skills: Dict[str, Any],
        user_profile: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> EmailContent:
        """Genera contenido de email usando Anthropic."""
        try:
            # Construir prompt personalizado
            prompt = self._build_prompt(
                job_description, cv_skills, user_profile, custom_prompt
            )
            
            # Llamar a Anthropic
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                timeout=20
            )
            
            # Extraer contenido de la respuesta
            content = response.content[0].text if response.content else ""
            
            # Parsear subject y body
            subject, body = self._parse_email_content(content)
            
            return EmailContent(
                subject=subject,
                body=body,
                provider="anthropic",
                model=self.model,
                tokens_used=response.usage.output_tokens if response.usage else None
            )
            
        except Exception as e:
            logger.error(f"Error generando email con Anthropic: {e}")
            return EmailContent(
                subject="",
                body="",
                provider="anthropic",
                model=self.model,
                error=str(e)
            )
    
    def _build_prompt(
        self, 
        job_description: str,
        cv_skills: Dict[str, Any],
        user_profile: Dict[str, Any],
        custom_prompt: Optional[str] = None
    ) -> str:
        """Construye el prompt para la generación de email."""
        if custom_prompt:
            # Si hay prompt personalizado, agregar instrucciones específicas para JSON
            logger.info(f"🔧 Usando custom_prompt para Anthropic: {len(custom_prompt)} caracteres")
            return f"""{custom_prompt}

IMPORTANTE: Responde ÚNICAMENTE con JSON válido. No incluyas texto adicional, explicaciones o comentarios. El formato debe ser exactamente:

{{
    "resumen_profesional": "...",
    "habilidades_destacadas": ["...", "..."],
    "experiencia_relevante": "...",
    "proyectos_relevantes": ["...", "..."],
    "educacion_adaptada": "...",
    "puntos_clave": ["...", "..."]
}}"""
        
        # Prompt por defecto para email
        return f"""
Genera un email personalizado para aplicar a este puesto:

PUESTO: {job_description}
CV: {cv_skills}
PERFIL: {user_profile}

Responde con JSON válido:
{{
    "subject": "Asunto del email",
    "body": "Cuerpo del email personalizado"
}}
"""
    
    def _parse_email_content(self, content: str) -> tuple[str, str]:
        """Parsea el contenido generado para extraer subject y body."""
        # Reutilizar la misma lógica que OpenAI
        openai_provider = OpenAIProvider()
        return openai_provider._parse_email_content(content)
    
    def generate_with_vision(self, prompt: str, image_base64: str) -> str:
        """Genera texto a partir de una imagen usando visión con reintentos."""
        import time
        
        max_retries = 3
        base_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔍 ANTHROPIC VISION: Intento {attempt + 1}/{max_retries}")
                if not self._client:
                    logger.info("🔍 ANTHROPIC VISION: Cliente no inicializado, inicializando...")
                    self._initialize_client()
                
                # Usar el modelo seleccionado dinámicamente
                model_to_use = self._model
                logger.info(f"🔍 ANTHROPIC VISION: Modelo: {model_to_use}")
                logger.info(f"🔍 ANTHROPIC VISION: Prompt: {len(prompt)} caracteres")
                logger.info(f"🔍 ANTHROPIC VISION: Imagen: {len(image_base64)} caracteres base64")
                logger.info("🔍 ANTHROPIC VISION: Enviando request a Anthropic...")
                
                response = self._client.messages.create(
                    model=model_to_use,
                    max_tokens=4000,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": image_base64
                                    }
                                }
                            ]
                        }
                    ],
                    timeout=60
                )
                
                logger.info("🔍 ANTHROPIC VISION: Respuesta recibida de Anthropic")
                result = response.content[0].text.strip()
                logger.info(f"✅ ANTHROPIC VISION: Texto extraído: {len(result)} caracteres")
                logger.info(f"✅ ANTHROPIC VISION: Preview: {result[:200]}...")
                return result
                
            except Exception as e:
                error_str = str(e)
                logger.error(f"❌ ANTHROPIC VISION ERROR (intento {attempt + 1}): {e}")
                logger.error(f"❌ ANTHROPIC VISION ERROR TYPE: {type(e)}")
                
                # Verificar si es un error recuperable (529 Overloaded, 500, timeout)
                is_retryable = (
                    "529" in error_str or 
                    "overloaded" in error_str.lower() or
                    "500" in error_str or
                    "internal" in error_str.lower() or
                    "timeout" in error_str.lower()
                )
                
                # Si es el último intento o no es recuperable, lanzar error
                if attempt == max_retries - 1 or not is_retryable:
                    logger.error(f"❌ ANTHROPIC VISION: Agotados {max_retries} intentos o error no recuperable")
                    break
                
                # Calcular delay con backoff exponencial
                delay = base_delay * (2 ** attempt)
                logger.warning(f"⏳ ANTHROPIC VISION: Esperando {delay}s antes de reintentar...")
                time.sleep(delay)
        
        # Si llegamos aquí, todos los intentos fallaron
        logger.error(f"❌ ANTHROPIC VISION ERROR FINAL: {e}")
        logger.error(f"❌ ANTHROPIC VISION ERROR TYPE FINAL: {type(e)}")
        
        # Verificar si es un error de modelo no encontrado
        if "404" in str(e) and "not_found_error" in str(e):
            logger.warning("⚠️ Modelo no encontrado, intentando fallback automático...")
            try:
                # Refrescar modelos y obtener uno alternativo
                if self._model_finder:
                    self._model_finder.refresh_models()
                    fallback_model = self._model_finder.get_vision_model()
                    if fallback_model and fallback_model != self._model:
                        logger.info(f"🔄 Intentando con modelo de fallback: {fallback_model}")
                        self._model = fallback_model
                        
                        # Reintentar con el modelo de fallback
                        response = self._client.messages.create(
                            model=fallback_model,
                            max_tokens=4000,
                            messages=[
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": prompt},
                                        {
                                            "type": "image",
                                            "source": {
                                                "type": "base64",
                                                "media_type": "image/png",
                                                "data": image_base64
                                            }
                                        }
                                    ]
                                }
                            ],
                            timeout=60
                        )
                        
                        logger.info("✅ ANTHROPIC VISION: Fallback exitoso")
                        result = response.content[0].text.strip()
                        logger.info(f"✅ ANTHROPIC VISION: Texto extraído con fallback: {len(result)} caracteres")
                        return result
                    else:
                        logger.error("❌ No se encontró modelo de fallback disponible")
                else:
                    logger.error("❌ Model finder no disponible para fallback")
            except Exception as fallback_error:
                logger.error(f"❌ Error en fallback automático: {fallback_error}")
        
        # Formatear el error específico de Anthropic
        error_str = str(e)
        logger.error(f"❌ ANTHROPIC VISION ERROR STRING: {error_str}")
        
        if "529" in error_str or "overloaded" in error_str.lower():
            error_msg = "❌ Anthropic: Servidores sobrecargados - Reintentando automáticamente"
            logger.error(f"❌ ANTHROPIC VISION: Error 529 Overloaded detectado")
        elif "429" in error_str or "quota" in error_str.lower():
            error_msg = "❌ Anthropic: Cuota agotada - Verifica tu plan y facturación"
            logger.error(f"❌ ANTHROPIC VISION: Error de cuota detectado")
        elif "401" in error_str or "invalid_api_key" in error_str.lower():
            error_msg = "❌ Anthropic: API key inválida - Verifica tu clave de API"
            logger.error(f"❌ ANTHROPIC VISION: Error de autenticación detectado")
        elif "403" in error_str or "forbidden" in error_str.lower():
            error_msg = "❌ Anthropic: Acceso denegado - Verifica permisos de tu cuenta"
            logger.error(f"❌ ANTHROPIC VISION: Error de permisos detectado")
        elif "500" in error_str or "internal" in error_str.lower():
            error_msg = "❌ Anthropic: Error interno del servidor"
            logger.error(f"❌ ANTHROPIC VISION: Error interno detectado")
        elif "timeout" in error_str.lower():
            error_msg = "❌ Anthropic: Tiempo de espera agotado"
            logger.error(f"❌ ANTHROPIC VISION: Error de timeout detectado")
        else:
            error_msg = f"❌ Anthropic: {error_str}"
            logger.error(f"❌ ANTHROPIC VISION: Error genérico")
        
        logger.error(f"❌ ANTHROPIC VISION: Error final formateado: {error_msg}")
        raise Exception(error_msg)


    def generate_text(self, prompt: str) -> str:
        """Genera texto a partir de un prompt con reintentos automáticos."""
        import time
        
        max_retries = 3
        retry_delays = [0, 2, 4]  # segundos
        
        for attempt in range(max_retries):
            try:
                if not self._client:
                    self._initialize_client()
                
                if attempt > 0:
                    logger.info(f"🔄 ANTHROPIC TEXT: Reintento {attempt + 1}/{max_retries}")
                
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=4000,
                    temperature=0.1,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=20
                )
                
                return response.content[0].text.strip()
                
            except Exception as e:
                error_str = str(e)
                is_last_attempt = (attempt == max_retries - 1)
                
                # Errores recuperables (reintentar)
                is_recoverable = (
                    "529" in error_str or  # Overloaded
                    "overloaded" in error_str.lower() or
                    "500" in error_str or  # Internal Server Error
                    "timeout" in error_str.lower()
                )
                
                # Errores no recuperables (fallar inmediatamente)
                is_fatal = (
                    "401" in error_str or  # Unauthorized
                    "403" in error_str or  # Forbidden
                    "invalid" in error_str.lower() and "api" in error_str.lower()
                )
                
                if is_fatal:
                    logger.error(f"❌ ANTHROPIC TEXT: Error fatal (no recuperable): {e}")
                    raise
                
                if is_recoverable and not is_last_attempt:
                    delay = retry_delays[attempt]
                    logger.warning(f"⚠️ ANTHROPIC TEXT: Error recuperable en intento {attempt + 1}: {e}")
                    logger.info(f"⏳ Esperando {delay}s antes de reintentar...")
                    time.sleep(delay)
                    continue
                
                # Si llegamos aquí, todos los intentos fallaron
                logger.error(f"❌ ANTHROPIC TEXT: Error después de {max_retries} intentos: {e}")
                
                # Formatear error específico para el usuario
                if "529" in error_str or "overloaded" in error_str.lower():
                    raise Exception("❌ Anthropic: Servidores sobrecargados - Intenta nuevamente en unos minutos")
                elif "500" in error_str:
                    raise Exception("❌ Anthropic: Error interno del servidor - Intenta nuevamente")
                elif "timeout" in error_str.lower():
                    raise Exception("❌ Anthropic: Tiempo de espera agotado - La solicitud tardó demasiado")
                else:
                    raise Exception(f"❌ Anthropic: {error_str}")
    
    def _initialize_client(self):
        """Inicializa el cliente Anthropic."""
        try:
            config = self._get_config()
            if config and config.anthropic_enabled:
                api_key = config.get_anthropic_key()
                if api_key:
                    self._client = anthropic.Anthropic(api_key=api_key)
                    # Crear model finder para obtener modelos disponibles
                    self._model_finder = create_model_finder(api_key)
                    # Obtener el mejor modelo disponible
                    self._model = self._model_finder.get_vision_model()
                    if not self._model:
                        # Fallback a modelo por defecto si no se encuentra ninguno
                        self._model = config.anthropic_model or "claude-3-5-sonnet-20240620"
                    logger.info(f"✅ Cliente Anthropic inicializado con modelo: {self._model}")
                else:
                    logger.warning("⚠️ Anthropic habilitado pero sin API key")
            else:
                logger.warning("⚠️ Anthropic no habilitado en configuración")
        except Exception as e:
            logger.error(f"❌ Error inicializando cliente Anthropic: {e}")


class AIEmailService:
    """Servicio principal para generación de emails con IA."""
    
    def __init__(self):
        self.providers = {
            'openai': OpenAIProvider(),
            'anthropic': AnthropicProvider()
        }
        # No cachear configuración para reflejar cambios en tiempo real
        self.default_provider = self._get_default_provider()

    # Utilidad: ejecutar una llamada potencialmente lenta con timeout duro
    def _call_with_timeout(self, func, *args, timeout_seconds: int = 20, **kwargs):
        import threading

        result_container = {"result": None, "error": None}

        def _runner():
            try:
                result_container["result"] = func(*args, **kwargs)
            except Exception as e:  # Propagar error capturado
                result_container["error"] = e

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join(timeout_seconds)

        if t.is_alive():
            # No esperamos más; informamos timeout claro para el frontend
            raise TimeoutError(f"Tiempo de espera agotado ({timeout_seconds}s)")

        if result_container["error"] is not None:
            raise result_container["error"]

        return result_container["result"]
    
    def _get_config(self):
        """Obtiene la configuración de IA desde la base de datos (sin caché)."""
        # IMPORTANTE: NO cachear la configuración para que siempre use la versión más reciente
        # Esto evita problemas cuando el usuario actualiza la API key en el admin
        try:
            from matching.models import AIConfiguration
            return AIConfiguration.get_config()
        except Exception as e:
            logger.error(f"Error obteniendo configuración IA: {e}")
            return None
    
    def _get_default_provider(self):
        """Obtiene el proveedor por defecto desde la configuración."""
        config = self._get_config()
        if config:
            return config.default_provider
        return os.getenv('AI_PROVIDER', 'openai')
    
    def generate_email(
        self, 
        job_description: str,
        cv_skills: Dict[str, Any],
        user_profile: Dict[str, Any],
        provider: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        use_fallback: bool = True
    ) -> EmailContent:
        """
        Genera contenido de email usando el proveedor especificado.
        
        Args:
            job_description: Descripción del puesto de trabajo
            cv_skills: Habilidades extraídas del CV
            user_profile: Perfil del usuario
            provider: Proveedor de IA a usar ('openai' o 'anthropic')
            custom_prompt: Prompt personalizado adicional
            use_fallback: Si True, intenta con otro proveedor si el primero falla
        
        Returns:
            EmailContent: Contenido generado del email
        """
        provider_name = provider or self.default_provider
        
        if provider_name not in self.providers:
            logger.error(f"Proveedor de IA no disponible: {provider_name}")
            return EmailContent(
                subject="",
                body="",
                provider=provider_name,
                model="unknown",
                error=f"Proveedor no disponible: {provider_name}"
            )
        
        # Intentar con el proveedor principal
        try:
            result = self.providers[provider_name].generate_email_content(
                job_description, cv_skills, user_profile, custom_prompt
            )
            
            # Si hay error, intentar con el proveedor alternativo (solo si use_fallback=True)
            if result.error and use_fallback and len(self.providers) > 1:
                fallback_provider = next(
                    (p for p in self.providers.keys() if p != provider_name), 
                    None
                )
                
                if fallback_provider and self.is_provider_configured(fallback_provider):
                    logger.warning(
                        f"Error con {provider_name}, intentando con {fallback_provider}"
                    )
                    result = self.providers[fallback_provider].generate_email_content(
                        job_description, cv_skills, user_profile, custom_prompt
                    )
            
            return result
            
        except ValueError as e:
            # Error de configuración (API key faltante)
            logger.error(f"Error de configuración con {provider_name}: {e}")
            return EmailContent(
                subject="",
                body="",
                provider=provider_name,
                model="unknown",
                error=f"Proveedor no configurado: {str(e)}"
            )
        except Exception as e:
            # Otros errores
            logger.error(f"Error en servicio de IA: {e}")
            return EmailContent(
                subject="",
                body="",
                provider=provider_name,
                model="unknown",
                error=str(e)
            )
    
    def get_available_providers(self) -> list[str]:
        """Retorna lista de proveedores disponibles."""
        return list(self.providers.keys())
    
    def is_provider_configured(self, provider: str) -> bool:
        """Verifica si un proveedor está configurado correctamente."""
        config = self._get_config()
        
        if config:
            # Usar configuración de la base de datos
            if provider == 'openai':
                return config.openai_enabled and bool(config.get_openai_key())
            elif provider == 'anthropic':
                return config.anthropic_enabled and bool(config.get_anthropic_key())
        else:
            # Fallback a variables de entorno
            if provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
                return bool(api_key and api_key != 'your-openai-api-key-here')
            elif provider == 'anthropic':
                api_key = os.getenv('ANTHROPIC_API_KEY')
                return bool(api_key and api_key != 'your-anthropic-api-key-here')
        
        return False
    
    def generate_with_vision(self, prompt: str, image_base64: str) -> str:
        """Genera texto a partir de una imagen usando visión con fallback automático."""
        # Intentar con OpenAI primero
        if self.is_provider_configured('openai'):
            try:
                provider = self.providers['openai']
                result = provider.generate_with_vision(prompt, image_base64)
                logger.info("✅ Texto con visión generado con OpenAI")
                return result
            except Exception as e:
                # El error ya viene formateado correctamente del OpenAIProvider
                openai_error = str(e)
                logger.warning(f"⚠️ Error con OpenAI visión: {openai_error}")

                # Intentar con Anthropic como fallback real
                if self.is_provider_configured('anthropic'):
                    try:
                        logger.info("🔄 Intentando con Anthropic como fallback...")
                        provider = self.providers['anthropic']
                        result = provider.generate_with_vision(prompt, image_base64)
                        logger.info("✅ Texto con visión generado con Anthropic (FALLBACK)")
                        return result
                    except Exception as e2:
                        # Anthropic también falló
                        anthropic_error = str(e2)
                        logger.error(f"❌ Error con Anthropic visión: {anthropic_error}")

                        # Combinar errores sin duplicar
                        full_error = f"{openai_error}. {anthropic_error}"
                        logger.error(f"🔴 ERROR COMPLETO DE IA: {full_error}")
                        raise Exception(f"IA_DETALLADO: {full_error}")
                else:
                    # Anthropic no está configurado
                    anthropic_error = "❌ Anthropic no configurado"
                    logger.error(f"❌ Error con Anthropic visión: {anthropic_error}")

                    # Combinar errores sin duplicar
                    full_error = f"{openai_error}. {anthropic_error}"
                    logger.error(f"🔴 ERROR COMPLETO DE IA: {full_error}")
                    raise Exception(f"IA_DETALLADO: {full_error}")

        # Si OpenAI no está configurado, intentar solo con Anthropic
        elif self.is_provider_configured('anthropic'):
            try:
                provider = self.providers['anthropic']
                result = provider.generate_with_vision(prompt, image_base64)
                logger.info("✅ Texto con visión generado con Anthropic")
                return result
            except Exception as e:
                anthropic_error = str(e)
                logger.error(f"❌ Error con Anthropic visión: {anthropic_error}")
                raise Exception(f"IA_DETALLADO: {anthropic_error}")

        # Si ningún proveedor está configurado
        else:
            raise Exception("❌ IA no disponible - No hay proveedores de IA configurados")
    
    def _get_specific_openai_error(self, error: Exception) -> str:
        """Obtiene un mensaje de error específico para OpenAI."""
        error_str = str(error)
        
        if "429" in error_str or "quota" in error_str.lower():
            return "❌ OpenAI: Cuota agotada - Verifica tu plan y facturación"
        elif "401" in error_str or "invalid_api_key" in error_str.lower():
            return "❌ OpenAI: API key inválida - Verifica tu clave de API"
        elif "403" in error_str or "forbidden" in error_str.lower():
            return "❌ OpenAI: Acceso denegado - Verifica permisos de tu cuenta"
        elif "500" in error_str or "internal" in error_str.lower():
            return "❌ OpenAI: Error interno del servidor"
        elif "timeout" in error_str.lower():
            return "❌ OpenAI: Tiempo de espera agotado"
        else:
            return f"❌ OpenAI: {error_str}"
    
    def generate_with_vision_and_track_fallback(self, prompt: str, image_base64: str, progress_tracker=None) -> tuple:
        """Genera texto a partir de una imagen y retorna información sobre el fallback usado."""
        # Intentar con OpenAI primero
        if self.is_provider_configured('openai'):
            try:
                provider = self.providers['openai']
                result = provider.generate_with_vision(prompt, image_base64)
                logger.info("✅ Texto con visión generado con OpenAI")
                return result, False  # No se usó fallback
            except Exception as e:
                # El error ya viene formateado correctamente del OpenAIProvider
                openai_error = str(e)
                logger.warning(f"⚠️ Error con OpenAI visión: {openai_error}")

                # Formatear mensaje de error para el usuario
                error_message = self._get_specific_openai_error(e)
                
                # Extraer solo el mensaje sin el prefijo "❌ OpenAI:"
                clean_error = error_message.replace("❌ OpenAI: ", "")

                # Actualizar progreso ANTES de intentar con Anthropic
                if progress_tracker:
                    progress_tracker.update_step("openai_vision", "error", f"OpenAI falló: {clean_error}")
                    progress_tracker.update_step("anthropic_vision", "in_progress", "Procesando con Anthropic")

                # Intentar con Anthropic como fallback real
                if self.is_provider_configured('anthropic'):
                    try:
                        logger.info("🔄 Intentando con Anthropic como fallback...")
                        provider = self.providers['anthropic']
                        result = provider.generate_with_vision(prompt, image_base64)
                        logger.info("✅ Texto con visión generado con Anthropic (FALLBACK)")
                        return result, True  # Se usó fallback
                    except Exception as e2:
                        # Anthropic también falló
                        anthropic_error = str(e2)
                        logger.error(f"❌ Error con Anthropic visión: {anthropic_error}")

                        # Combinar errores sin duplicar
                        full_error = f"{openai_error}. {anthropic_error}"
                        logger.error(f"🔴 ERROR COMPLETO DE IA: {full_error}")
                        raise Exception(f"IA_DETALLADO: {full_error}")
                else:
                    # Anthropic no está configurado
                    anthropic_error = "❌ Anthropic no configurado"
                    logger.error(f"❌ Error con Anthropic visión: {anthropic_error}")

                    # Combinar errores sin duplicar
                    full_error = f"{openai_error}. {anthropic_error}"
                    logger.error(f"🔴 ERROR COMPLETO DE IA: {full_error}")
                    raise Exception(f"IA_DETALLADO: {full_error}")

        # Si OpenAI no está configurado, intentar solo con Anthropic
        elif self.is_provider_configured('anthropic'):
            try:
                provider = self.providers['anthropic']
                result = provider.generate_with_vision(prompt, image_base64)
                logger.info("✅ Texto con visión generado con Anthropic")
                return result, False  # No se usó fallback (Anthropic fue la primera opción)
            except Exception as e:
                anthropic_error = str(e)
                logger.error(f"❌ Error con Anthropic visión: {anthropic_error}")
                raise Exception(f"IA_DETALLADO: {anthropic_error}")

        # Si ningún proveedor está configurado
        else:
            raise Exception("❌ IA no disponible - No hay proveedores de IA configurados")
    
    def generate_text(self, prompt: str) -> str:
        """Genera texto a partir de un prompt con fallback automático."""
        # Intentar con OpenAI primero
        if self.is_provider_configured('openai'):
            try:
                provider = self.providers['openai']
                result = self._call_with_timeout(
                    provider.generate_text, prompt, timeout_seconds=20
                )
                logger.info("✅ Texto generado con OpenAI")
                return result
            except Exception as e:
                logger.warning(f"⚠️ Error con OpenAI: {e}")
                # Fallback a Anthropic si OpenAI falla
                if self.is_provider_configured('anthropic'):
                    try:
                        logger.info("🔄 Intentando con Anthropic como fallback...")
                        provider = self.providers['anthropic']
                        result = self._call_with_timeout(
                            provider.generate_text, prompt, timeout_seconds=20
                        )
                        logger.info("✅ Texto generado con Anthropic (FALLBACK USADO)")
                        return result
                    except Exception as e2:
                        logger.error(f"❌ Error con Anthropic: {e2}")
                        raise Exception(f"Error con ambos proveedores: OpenAI ({e}), Anthropic ({e2})")
                else:
                    raise Exception(f"Error con OpenAI y Anthropic no configurado: {e}")
        
        # Si OpenAI no está configurado, intentar con Anthropic
        elif self.is_provider_configured('anthropic'):
            try:
                provider = self.providers['anthropic']
                result = provider.generate_text(prompt)
                logger.info("✅ Texto generado con Anthropic")
                return result
            except Exception as e:
                logger.error(f"❌ Error con Anthropic: {e}")
                raise Exception(f"Error con Anthropic: {e}")
        else:
            raise Exception("No hay proveedores de IA configurados")
    
    def generate_text_and_track_fallback(self, prompt: str) -> tuple:
        """Genera texto a partir de un prompt y retorna información sobre el fallback usado."""
        # Intentar con OpenAI primero
        if self.is_provider_configured('openai'):
            try:
                provider = self.providers['openai']
                result = self._call_with_timeout(
                    provider.generate_text, prompt, timeout_seconds=20
                )
                logger.info("✅ Texto generado con OpenAI")
                return result, False  # No se usó fallback
            except Exception as e:
                logger.warning(f"⚠️ Error con OpenAI: {e}")
                # Fallback a Anthropic si OpenAI falla
                if self.is_provider_configured('anthropic'):
                    try:
                        logger.info("🔄 Intentando con Anthropic como fallback...")
                        provider = self.providers['anthropic']
                        result = self._call_with_timeout(
                            provider.generate_text, prompt, timeout_seconds=20
                        )
                        logger.info("✅ Texto generado con Anthropic (FALLBACK USADO)")
                        return result, True  # Se usó fallback
                    except Exception as e2:
                        logger.error(f"❌ Error con Anthropic: {e2}")
                        raise Exception(f"Error con ambos proveedores: OpenAI ({e}), Anthropic ({e2})")
                else:
                    raise Exception(f"Error con OpenAI y Anthropic no configurado: {e}")
        
        # Si OpenAI no está configurado, intentar con Anthropic
        elif self.is_provider_configured('anthropic'):
            try:
                provider = self.providers['anthropic']
                result = provider.generate_text(prompt)
                logger.info("✅ Texto generado con Anthropic")
                return result, False  # No se usó fallback (Anthropic fue la primera opción)
            except Exception as e:
                logger.error(f"❌ Error con Anthropic: {e}")
                raise Exception(f"Error con Anthropic: {e}")
        else:
            raise Exception("No hay proveedores de IA configurados")


# Instancia global del servicio
ai_email_service = AIEmailService()
