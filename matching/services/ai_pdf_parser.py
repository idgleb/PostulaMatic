"""
Parser de PDFs que usa IA para extraer texto de manera inteligente.
"""

import base64
import logging
from typing import Dict, Any
from .ai_service import AIEmailService
from .pdf_parser import PDFParser

logger = logging.getLogger(__name__)


class AIPDFParser:
    """
    Parser de PDFs que usa IA para extraer texto de manera inteligente.
    """

    def __init__(self, ai_service: AIEmailService = None):
        """
        Inicializa el parser de IA.

        Args:
            ai_service: Servicio de IA para procesar PDFs
        """
        self.ai_service = ai_service or AIEmailService()

    def parse_cv(self, file_path: str, progress_tracker=None) -> Dict[str, Any]:
        """
        Extrae texto de un CV usando IA con fallback explícito.

        Flujo:
        1. Intenta con OpenAI (soporta visión)
        2. Si OpenAI falla, intenta con Anthropic (no soporta visión)
        3. Si ambos fallan, lanza excepción con detalles específicos

        Args:
            file_path: Ruta al archivo PDF
            progress_tracker: Instancia de ProgressTracker para actualizar el progreso (opcional)

        Returns:
            Diccionario con el texto extraído y metadatos

        Raises:
            Exception: Si la IA no está disponible o falla
        """
        try:
            logger.info(
                f"🤖 AIPDFParser: Iniciando extracción con IA para: {file_path}"
            )
            logger.info(
                "🤖 Flujo: OpenAI (visión) → Anthropic (visión) → Error si ambos fallan"
            )
            logger.info("📋 PASO 1: Iniciando conversión de PDF a imágenes...")

            # 1. Convertir PDF a imagen base64
            if progress_tracker:
                progress_tracker.update_step(
                    "pdf_to_images", "in_progress", "Convirtiendo PDF a imágenes..."
                )

            try:
                pdf_images = self._pdf_to_images(file_path)
            except Exception as img_error:
                # Si es error de validación de páginas, propagarlo directamente sin modificar
                if "solo se permiten CVs de máximo" in str(img_error):
                    logger.warning(f"⚠️ Validación de páginas: {img_error}")
                    raise  # Re-lanzar la excepción original
                else:
                    # Otro tipo de error en conversión
                    logger.error(f"❌ Error en conversión de PDF: {img_error}")
                    raise

            if progress_tracker:
                progress_tracker.update_step(
                    "pdf_to_images",
                    "completed",
                    f"{len(pdf_images)} imágenes extraídas",
                )
            logger.info(
                f"📋 PASO 1 COMPLETADO: Se extrajeron {len(pdf_images)} imágenes del PDF"
            )

            # 2. Procesar cada imagen con IA
            extracted_texts = []
            fallback_used = False
            logger.info(f"📋 PASO 2: Procesando {len(pdf_images)} páginas con IA...")

            for i, image_base64 in enumerate(pdf_images):
                logger.info(f"🔍 PASO 2.{i+1}: Procesando página {i+1} con IA...")
                logger.info(
                    f"🔍 PASO 2.{i+1}: Tamaño de imagen base64: {len(image_base64)} caracteres"
                )

                # Actualizar progreso según el proveedor configurado (solo en la primera página)
                if progress_tracker and i == 0:
                    # Verificar qué proveedor está configurado
                    if self.ai_service.is_provider_configured("openai"):
                        progress_tracker.update_step(
                            "openai_vision",
                            "in_progress",
                            "Extrayendo texto con OpenAI",
                        )
                    elif self.ai_service.is_provider_configured("anthropic"):
                        progress_tracker.update_step(
                            "anthropic_vision",
                            "in_progress",
                            "Extrayendo texto con Anthropic",
                        )
                    else:
                        progress_tracker.update_step(
                            "openai_vision",
                            "error",
                            "No hay proveedores de IA configurados",
                        )

                try:
                    page_text, used_fallback = self._extract_text_from_image_with_ai(
                        image_base64, progress_tracker if i == 0 else None
                    )
                    logger.info(
                        f"🔍 PASO 2.{i+1}: Texto extraído de página {i+1}: {len(page_text)} caracteres"
                    )

                    # Actualizar progreso según el resultado
                    # NOTA: NO sobrescribir si openai_vision ya está en "error" (el mensaje específico ya fue establecido)
                    if progress_tracker:
                        if i == 0:
                            if used_fallback:
                                # OpenAI falló pero Anthropic tuvo éxito
                                # El mensaje de error específico de OpenAI ya fue establecido en ai_service.py
                                # Solo actualizamos Anthropic
                                progress_tracker.update_step(
                                    "anthropic_vision",
                                    "in_progress",
                                    f"Procesando con Anthropic (página {i+1}/{len(pdf_images)})",
                                )
                            else:
                                # El proveedor configurado tuvo éxito (OpenAI o Anthropic)
                                if self.ai_service.is_provider_configured("openai"):
                                    progress_tracker.update_step(
                                        "openai_vision",
                                        "in_progress",
                                        f"Procesando con OpenAI (página {i+1}/{len(pdf_images)})",
                                    )
                                    progress_tracker.update_step(
                                        "anthropic_vision",
                                        "skipped",
                                        "No fue necesario",
                                    )
                                else:
                                    # Solo Anthropic está configurado y funcionó
                                    progress_tracker.update_step(
                                        "anthropic_vision",
                                        "in_progress",
                                        f"Procesando con Anthropic (página {i+1}/{len(pdf_images)})",
                                    )
                                    progress_tracker.update_step(
                                        "openai_vision", "skipped", "No configurado"
                                    )
                        else:
                            # Actualizar progreso de páginas subsiguientes
                            if fallback_used or used_fallback:
                                progress_tracker.update_step(
                                    "anthropic_vision",
                                    "in_progress",
                                    f"Procesando con Anthropic (página {i+1}/{len(pdf_images)})",
                                )
                            else:
                                progress_tracker.update_step(
                                    "openai_vision",
                                    "in_progress",
                                    f"Procesando con OpenAI (página {i+1}/{len(pdf_images)})",
                                )

                    if page_text:
                        extracted_texts.append(page_text)
                        logger.info(
                            f"🔍 PASO 2.{i+1}: Página {i+1} agregada a resultados"
                        )
                    else:
                        logger.warning(
                            f"🔍 PASO 2.{i+1}: Página {i+1} no produjo texto"
                        )
                    if used_fallback:
                        fallback_used = True
                        logger.info(
                            f"🔄 PASO 2.{i+1}: Fallback detectado en página {i+1}"
                        )
                except Exception as e:
                    # Si hay error en esta página, NO intentar con la siguiente
                    # Lanzar el error completo inmediatamente para que se propague
                    logger.error(
                        f"❌ PASO 2.{i+1}: Error procesando página {i+1}, abortando: {e}"
                    )
                    if progress_tracker:
                        step_id = (
                            "anthropic_vision" if fallback_used else "openai_vision"
                        )
                        progress_tracker.set_error(str(e), step_id)
                    raise e  # Re-lanzar el error completo sin modificarlo

            logger.info(
                f"📋 PASO 2 COMPLETADO: Se procesaron {len(extracted_texts)} páginas exitosamente"
            )

            # Marcar el paso de extracción como completado
            if progress_tracker:
                if fallback_used:
                    progress_tracker.update_step(
                        "anthropic_vision",
                        "completed",
                        f"Texto extraído con Anthropic ({len(pdf_images)} páginas)",
                    )
                else:
                    # Marcar como completado el proveedor que se usó
                    if self.ai_service.is_provider_configured("openai"):
                        progress_tracker.update_step(
                            "openai_vision",
                            "completed",
                            f"Texto extraído con OpenAI ({len(pdf_images)} páginas)",
                        )
                    else:
                        progress_tracker.update_step(
                            "anthropic_vision",
                            "completed",
                            f"Texto extraído con Anthropic ({len(pdf_images)} páginas)",
                        )

            if not extracted_texts:
                error_msg = "❌ IA no pudo extraer texto de las imágenes"
                logger.error(error_msg)
                raise Exception(error_msg)

            # 3. Combinar texto de todas las páginas
            logger.info("📋 PASO 3: Combinando texto de todas las páginas...")
            full_text = "\n\n".join(extracted_texts)
            logger.info(
                f"📋 PASO 3 COMPLETADO: Texto combinado: {len(full_text)} caracteres"
            )

            # 4. Post-procesar con IA para mejorar estructura (DESACTIVADO para evitar timeouts)
            logger.info(
                "📋 PASO 4: Saltado temporalmente (se devuelve texto crudo extraído)"
            )
            improved_text = full_text

            logger.info(
                f"✅ Extracción con IA completada: {len(improved_text)} caracteres"
            )

            # Crear mensaje de advertencia si se usó fallback
            warning_message = None
            if fallback_used:
                warning_message = "⚠️ OpenAI falló, se usó Anthropic como respaldo"
                logger.info("🔄 Se usó fallback de OpenAI a Anthropic")

            return {
                "text": improved_text,
                "warning_message": warning_message,
                "extraction_method": "ai_vision",
                "pages_processed": len(pdf_images),
                "fallback_used": fallback_used,
            }

        except Exception as e:
            error_msg = f"❌ Error crítico en extracción con IA: {e}"
            logger.error(error_msg)
            logger.error(f"🔍 Error original completo: {str(e)}")

            # Si el error contiene detalles específicos de OpenAI o Anthropic, usarlos directamente
            if (
                "OpenAI" in str(e)
                or "Anthropic" in str(e)
                or "visión" in str(e).lower()
            ):
                logger.error(f"🔴 ERROR DE IA ESPECÍFICO: {str(e)}")
                raise Exception(str(e))
            else:
                # Si no es un error específico de IA, crear uno más detallado
                raise Exception(error_msg)

    def get_supported_formats(self) -> list:
        """Retorna los formatos soportados por el parser de IA."""
        return [".pdf"]  # Solo PDFs para el parser de IA

    def _pdf_to_images(self, file_path: str) -> list:
        """
        Convierte un PDF a imágenes base64.

        Args:
            file_path: Ruta al archivo PDF

        Returns:
            Lista de imágenes en base64

        Raises:
            Exception: Si el PDF tiene más de 5 páginas
        """
        try:
            import fitz  # PyMuPDF

            logger.info(f"🔍 ABRIENDO PDF: {file_path}")
            doc = fitz.open(file_path)
            num_pages = len(doc)
            logger.info(f"🔍 PDF ABIERTO: {num_pages} páginas encontradas")

            # Validar número de páginas ANTES de procesar
            MAX_PAGES = 5
            if num_pages > MAX_PAGES:
                doc.close()
                error_msg = f"❌ El CV tiene {num_pages} páginas. Por razones de economía de tokens de IA, solo se permiten CVs de máximo {MAX_PAGES} páginas. Por favor, sube un CV más corto."
                logger.warning(error_msg)
                raise Exception(error_msg)

            images = []

            for page_num in range(len(doc)):
                logger.info(f"🔍 PROCESANDO PÁGINA {page_num + 1}/{len(doc)}...")
                page = doc.load_page(page_num)
                logger.info(f"🔍 PÁGINA {page_num + 1} CARGADA")

                # Convertir página a imagen
                mat = fitz.Matrix(2.0, 2.0)  # Escala 2x para mejor calidad
                logger.info(f"🔍 MATRIZ DE ESCALA CREADA: 2.0x")
                pix = page.get_pixmap(matrix=mat)
                logger.info(
                    f"🔍 PIXMAP CREADO PARA PÁGINA {page_num + 1}: {pix.width}x{pix.height}"
                )

                img_data = pix.tobytes("png")
                logger.info(
                    f"🔍 IMAGEN PNG GENERADA PARA PÁGINA {page_num + 1}: {len(img_data)} bytes"
                )

                # Convertir a base64
                img_base64 = base64.b64encode(img_data).decode("utf-8")
                logger.info(
                    f"🔍 BASE64 GENERADO PARA PÁGINA {page_num + 1}: {len(img_base64)} caracteres"
                )

                images.append(img_base64)
                logger.info(f"🔍 PÁGINA {page_num + 1} AGREGADA A LISTA DE IMÁGENES")

            doc.close()
            logger.info(f"🔍 PDF CERRADO. TOTAL DE IMÁGENES: {len(images)}")
            return images

        except Exception as e:
            logger.error(f"❌ Error convirtiendo PDF a imágenes: {e}")
            # Re-lanzar la excepción en lugar de retornar lista vacía
            # para que el mensaje de error específico se propague
            raise

    def _extract_text_from_image_with_ai(
        self, image_base64: str, progress_tracker=None
    ) -> tuple:
        """
        Extrae texto de una imagen usando IA.

        Args:
            image_base64: Imagen en base64
            progress_tracker: Rastreador de progreso opcional

        Returns:
            Tupla con (texto_extraído, usó_fallback)
        """
        try:
            # Crear prompt para IA
            logger.info("🔍 CREANDO PROMPT PARA IA...")
            prompt = self._create_vision_prompt()
            logger.info(f"🔍 PROMPT CREADO: {len(prompt)} caracteres")
            logger.info(f"🔍 PROMPT PREVIEW: {prompt[:200]}...")

            # Usar el método que rastrea el fallback
            logger.info("🔄 Extrayendo texto con IA (OpenAI → Anthropic si falla)...")
            try:
                response, used_fallback = (
                    self.ai_service.generate_with_vision_and_track_fallback(
                        prompt, image_base64, progress_tracker
                    )
                )

                if used_fallback:
                    logger.info(
                        f"✅ ANTHROPIC EXITOSO (FALLBACK): Respuesta recibida de {len(response)} caracteres"
                    )
                    logger.info(f"✅ ANTHROPIC PREVIEW: {response[:200]}...")
                else:
                    logger.info(
                        f"✅ OPENAI EXITOSO: Respuesta recibida de {len(response)} caracteres"
                    )
                    logger.info(f"✅ OPENAI PREVIEW: {response[:200]}...")

                return response.strip(), used_fallback
            except Exception as e:
                # Ambos proveedores fallaron
                error_msg = str(e)
                logger.error(f"❌ ERROR EXTRAYENDO TEXTO CON IA: {error_msg}")
                raise e

        except Exception as e:
            logger.error(f"❌ ERROR EXTRAYENDO TEXTO CON IA: {e}")
            logger.error(f"❌ ERROR TYPE: {type(e)}")
            raise e

    def _create_vision_prompt(self) -> str:
        """
        Crea el prompt para la extracción de texto con IA.

        Returns:
            Prompt optimizado para extracción de CVs
        """
        return """
Eres un experto en extracción de texto de CVs. Tu tarea es extraer TODO el texto visible de esta imagen de CV de manera precisa y estructurada.

INSTRUCCIONES:
1. Extrae TODO el texto visible de la imagen
2. Mantén la estructura y formato del CV
3. Preserva saltos de línea importantes
4. Incluye TODOS los enlaces, emails y números de teléfono
5. Mantén las secciones del CV (EXPERIENCIA, EDUCACIÓN, etc.)
6. Preserva fechas y rangos de tiempo
7. NO inventes información que no esté visible
8. Si hay texto borroso o ilegible, indícalo como [texto ilegible]

FORMATO DE RESPUESTA:
- Extrae el texto tal como aparece en la imagen
- Mantén la estructura original
- Preserva enlaces y contactos
- Incluye todas las secciones del CV

IMPORTANTE: Solo devuelve el texto extraído, sin explicaciones adicionales.
"""

    def _improve_text_structure_with_ai(self, text: str) -> tuple:
        """
        Mejora la estructura del texto extraído usando IA.

        Args:
            text: Texto extraído del CV

        Returns:
            Tupla con (texto_mejorado, usó_fallback)
        """
        try:
            prompt = f"""
Eres un experto en procesamiento de CVs. Tu tarea es mejorar la estructura y legibilidad de este texto extraído de un CV.

TEXTO ORIGINAL:
{text}

INSTRUCCIONES:
1. Reorganiza el texto para que sea más legible
2. Agrupa información relacionada
3. Preserva TODOS los enlaces, emails y números de teléfono
4. Mantén las secciones del CV (EXPERIENCIA, EDUCACIÓN, etc.)
5. Mejora la estructura pero NO cambies el contenido
6. Preserva fechas y rangos de tiempo
7. Mantén la información de contacto al inicio

FORMATO DESEADO:
- Información de contacto al inicio
- Secciones claramente separadas
- Texto fluido y legible
- Preservar todos los enlaces y contactos

IMPORTANTE: Solo devuelve el texto mejorado, sin explicaciones adicionales.
"""

            logger.info(f"🔍 PROMPT DE MEJORA CREADO: {len(prompt)} caracteres")
            logger.info(f"🔍 TEXTO ORIGINAL: {len(text)} caracteres")
            logger.info("🔄 ENVIANDO PROMPT DE MEJORA A IA...")

            # Para post-procesamiento textual, preferimos Anthropic primero por costo/latencia,
            # y hacemos fallback a OpenAI. Si ambos fallan, devolvemos el texto crudo.
            try:
                response, fallback_used = (
                    self.ai_service.generate_text_and_track_fallback(prompt)
                )
            except Exception as e:
                logger.error(
                    f"❌ Post-procesamiento con IA falló, devolviendo texto crudo: {e}"
                )
                return text, False
            logger.info(f"✅ TEXTO MEJORADO RECIBIDO: {len(response)} caracteres")
            logger.info(f"✅ FALLBACK USADO: {fallback_used}")
            return response.strip(), fallback_used

        except Exception as e:
            logger.error(f"❌ Error mejorando estructura con IA: {e}")
            # Si es un error de IA no disponible, lanzar excepción
            if (
                "IA no disponible" in str(e)
                or "Cuota agotada" in str(e)
                or "API keys inválidas" in str(e)
            ):
                raise Exception(
                    f"❌ IA no disponible - Cuota agotada o API keys inválidas"
                )
            else:
                return text, False

    def get_supported_formats(self) -> list:
        """Retorna los formatos soportados por este parser."""
        return [".pdf"]
