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


class OpenAIProvider(AIProvider):
    """Proveedor OpenAI para generación de emails."""
    
    def __init__(self):
        self._client = None
        self._model = None
        self._config = None
    
    def _get_config(self):
        """Obtiene la configuración de IA desde la base de datos."""
        if self._config is None:
            try:
                from matching.models import AIConfiguration
                self._config = AIConfiguration.get_config()
            except Exception as e:
                logger.error(f"Error obteniendo configuración IA: {e}")
                self._config = None
        return self._config
    
    @property
    def client(self):
        """Lazy initialization del cliente OpenAI."""
        if self._client is None:
            api_key = self._get_api_key()
            if not api_key:
                raise ValueError("OpenAI API key no está configurada")
            self._client = openai.OpenAI(api_key=api_key)
        return self._client
    
    def _get_api_key(self):
        """Obtiene la API key de OpenAI desde la configuración."""
        config = self._get_config()
        if config and config.openai_enabled:
            return config.get_openai_key()
        # Fallback a variables de entorno
        return os.getenv('OPENAI_API_KEY')
    
    @property
    def model(self):
        """Obtiene el modelo de OpenAI desde la configuración."""
        if self._model is None:
            config = self._get_config()
            if config and config.openai_enabled:
                self._model = config.openai_model
            else:
                # Fallback a variables de entorno
                self._model = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        return self._model
    
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
                temperature=0.7
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
            logger.error(f"Error generando email con OpenAI: {e}")
            return EmailContent(
                subject="",
                body="",
                provider="openai",
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
        
        if custom_prompt:
            base_prompt += f"\nInstrucciones adicionales: {custom_prompt}"
        
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


class AnthropicProvider(AIProvider):
    """Proveedor Anthropic para generación de emails."""
    
    def __init__(self):
        self._client = None
        self._model = None
        self._config = None
    
    def _get_config(self):
        """Obtiene la configuración de IA desde la base de datos."""
        if self._config is None:
            try:
                from matching.models import AIConfiguration
                self._config = AIConfiguration.get_config()
            except Exception as e:
                logger.error(f"Error obteniendo configuración IA: {e}")
                self._config = None
        return self._config
    
    @property
    def client(self):
        """Lazy initialization del cliente Anthropic."""
        if self._client is None:
            api_key = self._get_api_key()
            if not api_key:
                raise ValueError("Anthropic API key no está configurada")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client
    
    def _get_api_key(self):
        """Obtiene la API key de Anthropic desde la configuración."""
        config = self._get_config()
        if config and config.anthropic_enabled:
            return config.get_anthropic_key()
        # Fallback a variables de entorno
        return os.getenv('ANTHROPIC_API_KEY')
    
    @property
    def model(self):
        """Obtiene el modelo de Anthropic desde la configuración."""
        if self._model is None:
            config = self._get_config()
            if config and config.anthropic_enabled:
                self._model = config.anthropic_model
            else:
                # Fallback a variables de entorno
                self._model = os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')
        return self._model
    
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
                ]
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
        # Reutilizar la misma lógica que OpenAI
        openai_provider = OpenAIProvider()
        return openai_provider._build_prompt(
            job_description, cv_skills, user_profile, custom_prompt
        )
    
    def _parse_email_content(self, content: str) -> tuple[str, str]:
        """Parsea el contenido generado para extraer subject y body."""
        # Reutilizar la misma lógica que OpenAI
        openai_provider = OpenAIProvider()
        return openai_provider._parse_email_content(content)


class AIEmailService:
    """Servicio principal para generación de emails con IA."""
    
    def __init__(self):
        self.providers = {
            'openai': OpenAIProvider(),
            'anthropic': AnthropicProvider()
        }
        self._config = None  # Cache de configuración
        self.default_provider = self._get_default_provider()
    
    def _get_config(self):
        """Obtiene la configuración de IA desde la base de datos."""
        if self._config is None:
            try:
                from matching.models import AIConfiguration
                self._config = AIConfiguration.get_config()
            except Exception as e:
                logger.error(f"Error obteniendo configuración IA: {e}")
                self._config = None
        return self._config
    
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
        custom_prompt: Optional[str] = None
    ) -> EmailContent:
        """
        Genera contenido de email usando el proveedor especificado.
        
        Args:
            job_description: Descripción del puesto de trabajo
            cv_skills: Habilidades extraídas del CV
            user_profile: Perfil del usuario
            provider: Proveedor de IA a usar ('openai' o 'anthropic')
            custom_prompt: Prompt personalizado adicional
        
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
            
            # Si hay error, intentar con el proveedor alternativo
            if result.error and len(self.providers) > 1:
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


# Instancia global del servicio
ai_email_service = AIEmailService()
