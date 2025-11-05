"""
Servicio principal para parsear CVs en diferentes formatos.
Delega a parsers especializados según el tipo de archivo.
"""

import logging
from pathlib import Path
from typing import Dict

from .docx_parser import DOCXParser
# Importar parsers especializados
from .ai_pdf_parser import AIPDFParser

logger = logging.getLogger(__name__)


class CVParserError(Exception):
    """Excepción personalizada para errores del parser de CV."""

    pass


class CVParser:
    """Parser principal para CVs que delega a parsers especializados."""

    def __init__(self):
        self.pdf_parser = AIPDFParser()  # Usar parser de IA para PDFs
        self.docx_parser = DOCXParser()
        self.supported_formats = (
            self.pdf_parser.get_supported_formats()
            + self.docx_parser.get_supported_formats()
        )

    def parse_cv(self, file_path: str, progress_tracker=None) -> Dict:
        """
        Parsea un archivo de CV usando el parser especializado correspondiente.

        Args:
            file_path: Ruta al archivo de CV
            progress_tracker: Instancia de ProgressTracker para actualizar el progreso (opcional)

        Returns:
            Dict con 'text', 'format', 'word_count', 'pages' (si aplica)

        Raises:
            CVParserError: Si el archivo no se puede procesar
        """
        logger.info(f"🔍 CVParser: Iniciando parse_cv para {file_path}")
        print(f"🔍 CVParser: Iniciando parse_cv para {file_path}")  # Print para debugging
        file_path = Path(file_path)

        if not file_path.exists():
            raise CVParserError(f"El archivo {file_path} no existe")

        file_extension = file_path.suffix.lower()

        if file_extension not in self.supported_formats:
            raise CVParserError(
                f"Formato {file_extension} no soportado. "
                f"Formatos soportados: {', '.join(self.supported_formats)}"
            )

        try:
            # Delegar al parser especializado
            if file_extension == ".pdf":
                logger.info(f"🔍 CVParser: Usando AIPDFParser para {file_path}")
                result = self.pdf_parser.parse_cv(str(file_path), progress_tracker=progress_tracker)
                logger.info(f"🔍 CVParser: Resultado del AIPDFParser: {type(result)}")
            elif file_extension == ".docx":
                logger.info(f"🔍 CVParser: Usando DOCXParser para {file_path}")
                result = self.docx_parser.parse_cv(str(file_path))
            else:
                raise CVParserError(f"Parser no implementado para {file_extension}")

            # Normalizar el resultado
            return self._normalize_result(result, file_extension)

        except Exception as e:
            logger.error(f"Error parseando CV {file_path}: {e}")
            logger.error(f"🔍 Error en CVParser - Tipo: {type(e)}")
            logger.error(f"🔍 Error en CVParser - Contenido completo: {str(e)}")

            # Si es un error de validación de páginas, propagar directamente
            if "solo se permiten CVs de máximo" in str(e):
                logger.warning(f"⚠️ VALIDACIÓN: {str(e)}")
                raise CVParserError(str(e))
            
            # Si es un error de IA, propagar el mensaje original COMPLETO
            if ("IA no disponible" in str(e) or "Cuota agotada" in str(e) or "API keys inválidas" in str(e) or
                "Error crítico en extracción con IA" in str(e) or "Error con OpenAI" in str(e) or
                "Anthropic no soporta" in str(e) or "Error de IA" in str(e) or "IA_DETALLADO" in str(e)):
                logger.error(f"🔴 DETECTADO ERROR DE IA EN CVPARSER: {str(e)}")

                # Si el error viene con el prefijo especial IA_DETALLADO, extraer solo el contenido
                if str(e).startswith("IA_DETALLADO:"):
                    detailed_error = str(e).replace("IA_DETALLADO: ", "")
                    logger.error(f"🔴 PROPAGANDO ERROR DETALLADO: {detailed_error}")
                    # El error ya está completo, no agregar prefijo
                    raise CVParserError(detailed_error)
                # Si el error ya viene con formato detallado de IA (contiene OpenAI o Anthropic),
                # propagarlo tal cual sin agregar prefijo
                elif ("Error con OpenAI" in str(e) or "Anthropic no soporta" in str(e)):
                    logger.error(f"🔴 PROPAGANDO ERROR DETALLADO SIN MODIFICAR: {str(e)}")
                    raise CVParserError(str(e))
                else:
                    # Si no tiene detalles específicos, agregar el prefijo
                    logger.error(f"🔴 AGREGANDO PREFIJO Error de IA: {str(e)}")
                    raise CVParserError(f"Error de IA: {str(e)}")
            else:
                logger.error(f"🔴 ERROR NO ES DE IA: {str(e)}")
                raise CVParserError(f"Error procesando el archivo: {str(e)}")

    def _normalize_result(self, result: Dict, file_extension: str) -> Dict:
        """
        Normaliza el resultado del parser especializado.

        Args:
            result: Resultado del parser especializado
            file_extension: Extensión del archivo

        Returns:
            Resultado normalizado
        """
        text = result.get("text", "")
        warning_message = result.get("warning_message", "")

        # Calcular estadísticas
        word_count = len(text.split()) if text else 0
        char_count = len(text.strip()) if text else 0

        # Determinar páginas (solo para PDF)
        pages = 1
        if file_extension == ".pdf":
            # Contar saltos de página o estimar basado en longitud
            pages = max(1, char_count // 2000)  # Estimación aproximada

        # Crear advertencia si es necesario
        if not warning_message and char_count < 50:
            warning_message = f"⚠️ ADVERTENCIA: Texto extraído muy corto ({char_count} caracteres). Verifica que el archivo sea un CV válido."

        return {
            "text": text,
            "format": file_extension[1:],  # Remover el punto
            "word_count": word_count,
            "pages": pages,
            "warning_message": warning_message,  # ✅ Corregido: warning_message
            "extraction_method": f"specialized_{file_extension[1:]}_parser",
        }

    def get_supported_formats(self) -> list:
        """Retorna la lista de formatos soportados."""
        return self.supported_formats.copy()

    def is_supported(self, file_path: str) -> bool:
        """Verifica si el archivo es de un formato soportado."""
        return Path(file_path).suffix.lower() in self.supported_formats


# Instancia global del parser
cv_parser = CVParser()
