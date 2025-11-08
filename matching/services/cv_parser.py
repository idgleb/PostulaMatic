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
            # ============================================================
            # 🆕 NUEVO: Procesar DOCX con IA (convertir a PDF primero)
            # ============================================================
            if file_extension == ".docx":
                logger.info(f"🔍 CVParser: Convirtiendo DOCX a PDF para procesamiento con IA")
                print(f"🔍 CVParser: Convirtiendo DOCX a PDF para procesamiento con IA")
                
                if progress_tracker:
                    progress_tracker.update_step("docx_to_pdf", "in_progress", "Convirtiendo DOCX a PDF")
                
                # Convertir DOCX a PDF temporal
                pdf_path = self._convert_docx_to_pdf(str(file_path))
                
                if progress_tracker:
                    progress_tracker.update_step("docx_to_pdf", "completed", "DOCX convertido a PDF")
                
                # Procesar el PDF con IA
                logger.info(f"🔍 CVParser: Usando AIPDFParser para DOCX convertido")
                print(f"🔍 CVParser: Usando AIPDFParser para DOCX convertido")
                result = self.pdf_parser.parse_cv(pdf_path, progress_tracker=progress_tracker)
                
                # Limpiar archivo temporal
                import os
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
                    logger.info(f"🔍 CVParser: Archivo PDF temporal eliminado")
                
                logger.info(f"🔍 CVParser: DOCX procesado con IA exitosamente")
                print(f"🔍 CVParser: DOCX procesado con IA exitosamente")
                
            elif file_extension == ".pdf":
                logger.info(f"🔍 CVParser: Usando AIPDFParser para {file_path}")
                result = self.pdf_parser.parse_cv(str(file_path), progress_tracker=progress_tracker)
                logger.info(f"🔍 CVParser: Resultado del AIPDFParser: {type(result)}")
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

    def _convert_docx_to_pdf(self, docx_path: str) -> str:
        """
        Convierte un archivo DOCX a PDF temporal para procesamiento con IA.
        
        Args:
            docx_path: Ruta al archivo DOCX
            
        Returns:
            Ruta al archivo PDF temporal
            
        Raises:
            CVParserError: Si la conversión falla
        """
        try:
            import os
            import tempfile
            from docx2pdf import convert
            
            logger.info(f"🔄 Iniciando conversión de DOCX a PDF: {docx_path}")
            
            # Crear archivo PDF temporal
            temp_dir = tempfile.gettempdir()
            base_name = os.path.basename(docx_path).replace('.docx', '')
            pdf_filename = f"temp_cv_{base_name}_{os.getpid()}.pdf"
            pdf_path = os.path.join(temp_dir, pdf_filename)
            
            logger.info(f"🔄 Ruta PDF temporal: {pdf_path}")
            
            # Convertir DOCX a PDF
            # Nota: docx2pdf requiere Microsoft Word (Windows) o LibreOffice (Linux/Mac)
            convert(docx_path, pdf_path)
            
            # Verificar que el PDF se creó correctamente
            if not os.path.exists(pdf_path):
                raise CVParserError("El archivo PDF no se generó correctamente")
            
            file_size = os.path.getsize(pdf_path)
            logger.info(f"✅ DOCX convertido a PDF exitosamente: {pdf_path} ({file_size} bytes)")
            
            return pdf_path
            
        except ImportError as e:
            error_msg = (
                "❌ La biblioteca 'docx2pdf' no está instalada o no está disponible. "
                "Para procesar archivos DOCX con IA, necesitas instalar: pip install docx2pdf"
            )
            logger.error(error_msg)
            raise CVParserError(error_msg)
        except Exception as e:
            error_msg = f"❌ Error convirtiendo DOCX a PDF: {str(e)}"
            logger.error(error_msg)
            logger.error(f"🔍 Tipo de error: {type(e)}")
            
            # Si es un error de que no hay Word/LibreOffice instalado
            if "no such file" in str(e).lower() or "cannot find" in str(e).lower():
                raise CVParserError(
                    "❌ No se pudo convertir DOCX a PDF. "
                    "El servidor necesita Microsoft Word (Windows) o LibreOffice (Linux/Mac) instalado. "
                    "Por favor, contacta al administrador del sistema."
                )
            else:
                raise CVParserError(error_msg)

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
