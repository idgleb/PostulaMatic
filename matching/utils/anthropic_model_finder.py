import logging
from typing import List, Optional, Tuple
from anthropic import Anthropic, NotFoundError

logger = logging.getLogger(__name__)


class AnthropicModelFinder:
    """Encuentra modelos de Anthropic disponibles y maneja fallbacks automáticos."""
    
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self._available_models = None
        self._model_preferences = [
            "claude-sonnet-4-5",      # Más reciente
            "claude-opus-4-1",        # Opus 4.1
            "claude-opus-4",          # Opus 4
            "claude-sonnet-4",        # Sonnet 4
            "claude-haiku-4-5",       # Haiku 4.5
            "claude-3-7-sonnet",      # Fallback a 3.7
            "claude-3-5-sonnet",      # Fallback a 3.5
            "claude-3-sonnet",        # Fallback a 3
            "claude-3-haiku"          # Fallback a 3 Haiku
        ]
    
    def get_available_models(self) -> List[str]:
        """Obtiene la lista de modelos disponibles de la API."""
        try:
            logger.info("🔍 Consultando modelos disponibles en Anthropic...")
            response = self.client.models.list()
            models = [model.id for model in response.data]
            logger.info(f"✅ Modelos disponibles: {len(models)} encontrados")
            logger.info(f"🔍 Modelos: {models[:5]}...")  # Mostrar primeros 5
            return models
        except Exception as e:
            logger.error(f"❌ Error consultando modelos: {e}")
            return []
    
    def pick_best_model(self) -> Optional[str]:
        """Selecciona el mejor modelo disponible según preferencias."""
        if self._available_models is None:
            self._available_models = self.get_available_models()
        
        if not self._available_models:
            logger.error("❌ No hay modelos disponibles")
            return None
        
        # Buscar por orden de preferencia
        for preferred_family in self._model_preferences:
            for model_id in self._available_models:
                if preferred_family in model_id:
                    logger.info(f"✅ Modelo seleccionado: {model_id} (familia: {preferred_family})")
                    return model_id
        
        # Si no encuentra ninguno de los preferidos, usar el primero disponible
        fallback_model = self._available_models[0]
        logger.warning(f"⚠️ Usando modelo de fallback: {fallback_model}")
        return fallback_model
    
    def get_vision_model(self) -> Optional[str]:
        """Obtiene un modelo con capacidades de visión."""
        model = self.pick_best_model()
        if model:
            logger.info(f"🔍 Modelo de visión seleccionado: {model}")
        return model
    
    def refresh_models(self):
        """Refresca la lista de modelos disponibles."""
        logger.info("🔄 Refrescando lista de modelos...")
        self._available_models = None
        return self.get_available_models()


def create_model_finder(api_key: str) -> AnthropicModelFinder:
    """Factory function para crear un finder de modelos."""
    return AnthropicModelFinder(api_key)
