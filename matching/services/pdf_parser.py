#!/usr/bin/env python
"""
Parser especializado para archivos PDF.
Maneja metadatos PDF complejos y extrae solo texto legible.
"""

import logging
import os
import re
from typing import Dict

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

logger = logging.getLogger(__name__)


class PDFParser:
    """Parser especializado para archivos PDF."""

    def __init__(self):
        self.supported_extensions = [".pdf"]

    def is_supported(self, file_path: str) -> bool:
        """Verifica si el archivo es soportado por este parser."""
        if not PyPDF2:
            return False

        extension = os.path.splitext(file_path)[1].lower()
        return extension in self.supported_extensions

    def parse_cv(self, file_path: str) -> Dict:
        """
        Parsea un archivo PDF y extrae solo el texto legible.

        Args:
            file_path: Ruta al archivo PDF

        Returns:
            Dict con 'text' y 'warning_message' si aplica
        """
        if not self.is_supported(file_path):
            return {"text": "", "warning_message": "Formato PDF no soportado"}

        try:
            with open(file_path, "rb") as file:
                pdf_reader = PyPDF2.PdfReader(file)

                if not pdf_reader.pages:
                    return {"text": "", "warning_message": "PDF sin páginas"}

                # Extraer texto de todas las páginas con método mejorado
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        # Método 1: Extracción básica
                        page_text = page.extract_text()
                        
                        # Método 2: Extracción mejorada para enlaces y contactos
                        enhanced_text = self._extract_enhanced_text(page)
                        
                        # Usar el mejor resultado
                        if enhanced_text and len(enhanced_text) > len(page_text):
                            page_text = enhanced_text
                        
                        if page_text:
                            full_text += page_text + "\n"
                            
                    except Exception as e:
                        logger.warning(f"Error extrayendo página {page_num}: {e}")
                        continue

                # Limpiar el texto extraído
                clean_text = self._clean_pdf_text(full_text)

                # Verificar si hay suficiente contenido
                if len(clean_text.strip()) < 50:
                    return {
                        "text": clean_text,
                        "warning_message": "Texto extraído muy corto. Posible PDF escaneado o con estructura compleja.",
                    }

                return {"text": clean_text, "warning_message": None}

        except Exception as e:
            logger.error(f"Error parseando PDF {file_path}: {e}")
            return {"text": "", "warning_message": f"Error parseando PDF: {str(e)}"}

    def _clean_pdf_text(self, text: str) -> str:
        """
        Limpieza mejorada que preserva estructura importante.
        """
        if not text:
            return ""

        # Patrones de metadatos PDF comunes
        pdf_metadata_patterns = [
            # Coordenadas y comandos PDF
            r"\b\d+\s+\d+\.\d+\s+m\s+\d+\s+\d+\.\d+\s+l\b",
            r"\b\d+\s+\d+\s+cm\b",
            r"\b\d+\s+\d+\s+\d+\s+RG\b",
            r"\b\d+\s+\d+\s+\d+\s+-\d+\s+re\b",
            r"\b\d+\s+J\b",
            r"\b[0-9.]+\s+[0-9.]+\s+[0-9.]+\s+RG\b",
            # Comandos de transformación
            r"\b1\s+0\s+0\s+1\s+0\s+0\s+cm\b",
            r"\b0\s+1\s+-1\s+0\s+\d+\s+0\s+cm\b",
            # Bloques de texto PDF
            r"BT.*?ET",
            # Estados de gráficos
            r"q\s+.*?\s+Q",
            # Fuentes PDF
            r"/\w+\s+\d+\s+Tf",
            # Posicionamiento de texto
            r"\d+\s+\d+\s+Td",
            r"\d+\s+\d+\s+Tm",
        ]

        # Aplicar filtros para remover metadatos PDF
        cleaned_text = text
        for pattern in pdf_metadata_patterns:
            cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.DOTALL)

        # Preservar saltos de línea importantes
        lines = cleaned_text.split('\n')
        clean_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Preservar líneas importantes
            is_important = (
                # Secciones del CV
                any(section in line.upper() for section in [
                    'EXPERIENCIA', 'EDUCACIÓN', 'HABILIDADES', 'PROYECTOS', 
                    'CONTACTO', 'PERFIL', 'RESUMEN', 'EXPERIENCE', 'EDUCATION',
                    'SKILLS', 'PROJECTS', 'CONTACT', 'PROFILE', 'SUMMARY'
                ]) or
                # Enlaces y contactos
                '@' in line or 'http' in line.lower() or
                'linkedin.com' in line.lower() or 'github.com' in line.lower() or
                # Fechas
                re.search(r'\d{4}', line) or
                # Contenido sustancial
                (len(line) > 10 and not re.match(r'^[\d\s.,\-+]+$', line))
            )
            
            if is_important:
                clean_lines.append(line)

        return '\n'.join(clean_lines)

    def _extract_enhanced_text(self, page) -> str:
        """
        Extrae texto mejorado de una página PDF, incluyendo enlaces y contactos.
        
        Args:
            page: Página del PDF
            
        Returns:
            Texto extraído mejorado
        """
        try:
            # 1. Extraer texto con estructura preservada
            structured_text = self._extract_text_with_structure(page)
            
            # 2. Extraer enlaces y contactos específicos
            links_contacts = self._extract_links_and_contacts_enhanced(page)
            
            # 3. Combinar manteniendo estructura
            return self._combine_structured_content(structured_text, links_contacts)
            
        except Exception as e:
            logger.warning(f"Error en extracción mejorada: {e}")
            return page.extract_text()

    def _extract_text_with_structure(self, page) -> str:
        """
        Extrae texto preservando estructura del CV (saltos de línea, secciones).
        """
        try:
            # Obtener contenido crudo de la página
            page_content = page.get_contents()
            if not page_content:
                return page.extract_text()
            
            # Convertir a string
            if isinstance(page_content, list):
                content_str = b''.join(page_content).decode('utf-8', errors='ignore')
            else:
                content_str = str(page_content)
            
            # Extraer texto con comandos PDF que preservan estructura
            text_blocks = self._extract_text_blocks_with_structure(content_str)
            
            # Reconstruir texto manteniendo saltos de línea importantes
            structured_text = self._reconstruct_text_with_structure(text_blocks)
            
            return structured_text
            
        except Exception as e:
            logger.warning(f"Error extrayendo estructura: {e}")
            return page.extract_text()

    def _extract_text_blocks_with_structure(self, content_str: str) -> list:
        """
        Extrae bloques de texto preservando estructura del PDF.
        """
        import re
        
        # Patrones para detectar bloques de texto con estructura
        text_patterns = [
            # Bloques de texto con coordenadas
            r'BT\s+(.*?)\s+ET',
            # Texto con posicionamiento
            r'(\d+\.?\d*)\s+(\d+\.?\d*)\s+Td\s+\((.*?)\)\s+Tj',
            # Texto con matriz de transformación
            r'(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+Tm\s+\((.*?)\)\s+Tj',
        ]
        
        text_blocks = []
        
        for pattern in text_patterns:
            matches = re.findall(pattern, content_str, re.DOTALL)
            for match in matches:
                if isinstance(match, tuple):
                    # Extraer texto del match
                    text_content = match[-1] if match else ""
                    if text_content and len(text_content.strip()) > 1:
                        text_blocks.append(text_content.strip())
                else:
                    if match and len(match.strip()) > 1:
                        text_blocks.append(match.strip())
        
        return text_blocks

    def _reconstruct_text_with_structure(self, text_blocks: list) -> str:
        """
        Reconstruye texto manteniendo estructura y saltos de línea importantes.
        """
        if not text_blocks:
            return ""
        
        # Detectar secciones importantes del CV
        cv_sections = [
            'EXPERIENCIA', 'EXPERIENCE', 'EXPERIENCIA LABORAL',
            'EDUCACIÓN', 'EDUCATION', 'FORMACIÓN',
            'HABILIDADES', 'SKILLS', 'COMPETENCIAS',
            'PROYECTOS', 'PROJECTS', 'PORTFOLIO', 'PROJECTOS DESTACADOS',
            'CONTACTO', 'CONTACT', 'INFORMACIÓN PERSONAL',
            'PERFIL', 'PROFILE', 'RESUMEN', 'SUMMARY', 'PERFIL PROFESIONAL'
        ]
        
        structured_lines = []
        current_section = None
        
        for block in text_blocks:
            lines = block.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detectar si es una sección
                is_section = any(section in line.upper() for section in cv_sections)
                
                if is_section:
                    current_section = line.upper()
                    structured_lines.append(f"\n{line}\n")  # Sección con saltos de línea
                else:
                    # Determinar si necesita salto de línea
                    needs_break = self._needs_line_break(line, current_section)
                    
                    if needs_break:
                        structured_lines.append(f"{line}\n")
                    else:
                        structured_lines.append(line)
        
        return '\n'.join(structured_lines)

    def _needs_line_break(self, line: str, current_section: str) -> bool:
        """
        Determina si una línea necesita salto de línea basado en su contenido.
        """
        # Patrones que indican nueva línea
        break_patterns = [
            # Fechas
            r'\d{4}[-/]\d{2}[-/]\d{2}',
            r'\d{4}\s*[-–]\s*\d{4}',
            r'\d{4}\s*[-–]\s*Presente',
            r'\d{4}\s*[-–]\s*Actualidad',
            # Empresas/Instituciones (empiezan con mayúscula)
            r'^[A-Z][a-zA-Z\s&]+$',
            # Cargos (contienen palabras clave)
            r'(Desarrollador|Developer|Analista|Manager|Director|Coordinador)',
            # Enlaces
            r'https?://',
            r'linkedin\.com',
            r'github\.com',
            # Emails
            r'@.*\.',
            # Nombres de empresas comunes
            r'(Digital Vibe|Sberbank|Google|Microsoft|Apple|Amazon)',
            # Patrones de experiencia
            r'\d{4}\s*[-–]\s*\d{4}',
            r'\d{4}\s*[-–]\s*Actualidad',
        ]
        
        import re
        for pattern in break_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        
        return False

    def _preserve_date_ranges(self, text: str) -> str:
        """
        Preserva mejor los rangos de fechas en el texto extraído.
        """
        import re
        
        # Patrones para rangos de fechas
        date_patterns = [
            (r'(\d{4})\s*[-–]\s*(\d{4})', r'\1 – \2'),
            (r'(\d{4})\s*[-–]\s*Presente', r'\1 – Presente'),
            (r'(\d{4})\s*[-–]\s*Actualidad', r'\1 – Actualidad'),
        ]
        
        for pattern, replacement in date_patterns:
            text = re.sub(pattern, replacement, text)
        
        return text

    def _extract_links_and_contacts_enhanced(self, page) -> list:
        """
        Extrae enlaces y contactos con patrones mejorados.
        """
        try:
            # Obtener contenido crudo
            page_content = page.get_contents()
            if isinstance(page_content, list):
                content_str = b''.join(page_content).decode('utf-8', errors='ignore')
            else:
                content_str = str(page_content)
            
            # Patrones mejorados para enlaces y contactos
            patterns = {
                'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                'phone': r'\b\+?[\d\s\-\(\)]{10,}\b',
                'linkedin': r'linkedin\.com/in/[A-Za-z0-9\-_]+',
                'github': r'github\.com/[A-Za-z0-9\-_]+',
                'url': r'https?://[^\s]+',
                'playstore': r'play\.google\.com/store/apps/details\?id=[^\s]+',
                'portfolio': r'[A-Za-z0-9\-_]+\.com(?:/[^\s]*)?',
                'behance': r'behance\.net/[A-Za-z0-9\-_]+',
                'dribbble': r'dribbble\.com/[A-Za-z0-9\-_]+',
            }
            
            extracted_items = []
            
            for pattern_name, pattern in patterns.items():
                matches = re.findall(pattern, content_str, re.IGNORECASE)
                for match in matches:
                    if match not in extracted_items:
                        extracted_items.append(match)
            
            return extracted_items
            
        except Exception as e:
            logger.warning(f"Error extrayendo enlaces mejorados: {e}")
            return []

    def _combine_structured_content(self, structured_text: str, links_contacts: list) -> str:
        """
        Combina texto estructurado con enlaces y contactos.
        """
        result = structured_text
        
        if links_contacts:
            # Agregar enlaces y contactos al final, preservando estructura
            result += "\n\n" + "\n".join(links_contacts)
        
        # Aplicar limpieza final que preserve estructura
        cleaned_result = self._final_structure_cleanup(result)
        
        # Aplicar reconstrucción agresiva de frases
        return self._aggressive_sentence_reconstruction(cleaned_result)

    def _final_structure_cleanup(self, text: str) -> str:
        """
        Limpieza final que preserva la estructura del CV.
        """
        if not text:
            return ""
        
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Preservar líneas importantes con mejor detección
            is_important = (
                # Secciones del CV
                any(section in line.upper() for section in [
                    'EXPERIENCIA', 'EDUCACIÓN', 'HABILIDADES', 'PROYECTOS', 
                    'CONTACTO', 'PERFIL', 'RESUMEN', 'EXPERIENCE', 'EDUCATION',
                    'SKILLS', 'PROJECTS', 'CONTACT', 'PROFILE', 'SUMMARY',
                    'PERFIL PROFESIONAL', 'EXPERIENCIA LABORAL', 'PROJECTOS DESTACADOS'
                ]) or
                # Enlaces y contactos
                '@' in line or 'http' in line.lower() or
                'linkedin.com' in line.lower() or 'github.com' in line.lower() or
                # Fechas y rangos de tiempo
                re.search(r'\d{4}', line) or
                re.search(r'\d{4}\s*[-–]\s*\d{4}', line) or
                re.search(r'\d{4}\s*[-–]\s*Actualidad', line) or
                # Nombres de empresas
                any(company in line for company in ['Digital Vibe', 'Sberbank', 'Google', 'Microsoft']) or
                # Contenido sustancial
                (len(line) > 15 and not re.match(r'^[\d\s.,\-+]+$', line))
            )
            
            if is_important:
                cleaned_lines.append(line)
        
        # Aplicar mejoras de estructura
        structured_text = self._improve_text_structure('\n'.join(cleaned_lines))
        
        # Preservar rangos de fechas
        return self._preserve_date_ranges(structured_text)

    def _improve_text_structure(self, text: str) -> str:
        """
        Mejora la estructura del texto extraído para preservar mejor el formato del CV.
        """
        if not text:
            return ""
        
        import re
        
        # Dividir en líneas y procesar
        lines = text.split('\n')
        improved_lines = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Agregar salto de línea antes de secciones importantes
            if any(section in line.upper() for section in [
                'EXPERIENCIA LABORAL', 'PERFIL PROFESIONAL', 'PROYECTOS DESTACADOS',
                'EDUCACIÓN', 'HABILIDADES', 'CONTACTO'
            ]):
                if improved_lines:  # Solo si no es la primera línea
                    improved_lines.append('')  # Línea en blanco antes de sección
                improved_lines.append(line)
                continue
            
            # Agregar salto de línea antes de fechas
            if re.search(r'\d{4}\s*[-–]\s*', line):
                if improved_lines and not improved_lines[-1].strip() == '':
                    improved_lines.append('')  # Línea en blanco antes de fecha
                improved_lines.append(line)
                continue
            
            # Agregar salto de línea antes de nombres de empresas
            if any(company in line for company in ['Digital Vibe', 'Sberbank', 'Google', 'Microsoft']):
                if improved_lines and not improved_lines[-1].strip() == '':
                    improved_lines.append('')  # Línea en blanco antes de empresa
                improved_lines.append(line)
                continue
            
            # Agregar salto de línea antes de enlaces
            if any(pattern in line.lower() for pattern in ['http', 'linkedin.com', 'github.com']):
                if improved_lines and not improved_lines[-1].strip() == '':
                    improved_lines.append('')  # Línea en blanco antes de enlace
                improved_lines.append(line)
                continue
            
            # Línea normal
            improved_lines.append(line)
        
        # Aplicar reconstrucción de frases
        return self._reconstruct_sentences('\n'.join(improved_lines))

    def _reconstruct_sentences(self, text: str) -> str:
        """
        Reconstruye frases fragmentadas para mejorar la legibilidad.
        """
        if not text:
            return ""
        
        import re
        
        lines = text.split('\n')
        reconstructed_lines = []
        current_sentence = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_sentence:
                    # Reconstruir frase acumulada
                    reconstructed_lines.append(' '.join(current_sentence))
                    current_sentence = []
                reconstructed_lines.append('')
                continue
            
            # Detectar si es una línea que debe mantenerse separada
            should_keep_separate = (
                # Secciones del CV
                any(section in line.upper() for section in [
                    'EXPERIENCIA', 'EDUCACIÓN', 'HABILIDADES', 'PROYECTOS', 
                    'CONTACTO', 'PERFIL', 'RESUMEN'
                ]) or
                # Enlaces y contactos
                '@' in line or 'http' in line.lower() or
                'linkedin.com' in line.lower() or 'github.com' in line.lower() or
                # Fechas
                re.search(r'\d{4}', line) or
                # Nombres de empresas
                any(company in line for company in ['Digital Vibe', 'Sberbank', 'Google', 'Microsoft']) or
                # Líneas muy cortas que probablemente son títulos
                len(line) <= 3
            )
            
            if should_keep_separate:
                # Guardar frase acumulada si existe
                if current_sentence:
                    reconstructed_lines.append(' '.join(current_sentence))
                    current_sentence = []
                reconstructed_lines.append(line)
            else:
                # Acumular para reconstruir frase
                current_sentence.append(line)
        
        # Guardar última frase acumulada
        if current_sentence:
            reconstructed_lines.append(' '.join(current_sentence))
        
        # Aplicar reconstrucción más agresiva
        return self._aggressive_sentence_reconstruction('\n'.join(reconstructed_lines))

    def _aggressive_sentence_reconstruction(self, text: str) -> str:
        """
        Reconstrucción más agresiva de frases para combinar palabras fragmentadas.
        """
        if not text:
            return ""
        
        import re
        
        lines = text.split('\n')
        reconstructed_lines = []
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    # Reconstruir párrafo acumulada
                    reconstructed_lines.append(' '.join(current_paragraph))
                    current_paragraph = []
                reconstructed_lines.append('')
                continue
            
            # Detectar si es una línea que debe mantenerse separada
            should_keep_separate = (
                # Secciones del CV
                any(section in line.upper() for section in [
                    'EXPERIENCIA', 'EDUCACIÓN', 'HABILIDADES', 'PROYECTOS', 
                    'CONTACTO', 'PERFIL', 'RESUMEN'
                ]) or
                # Enlaces y contactos
                '@' in line or 'http' in line.lower() or
                'linkedin.com' in line.lower() or 'github.com' in line.lower() or
                # Fechas
                re.search(r'\d{4}', line) or
                # Nombres de empresas
                any(company in line for company in ['Digital Vibe', 'Sberbank', 'Google', 'Microsoft']) or
                # Líneas que terminan en punto (frases completas)
                line.endswith('.') or
                # Líneas muy largas (probablemente ya son frases completas)
                len(line) > 50
            )
            
            if should_keep_separate:
                # Guardar párrafo acumulada si existe
                if current_paragraph:
                    reconstructed_lines.append(' '.join(current_paragraph))
                    current_paragraph = []
                reconstructed_lines.append(line)
            else:
                # Acumular para reconstruir párrafo
                current_paragraph.append(line)
        
        # Guardar último párrafo acumulada
        if current_paragraph:
            reconstructed_lines.append(' '.join(current_paragraph))
        
        # Aplicar reconstrucción ultra-agresiva
        return self._ultra_aggressive_reconstruction('\n'.join(reconstructed_lines))

    def _ultra_aggressive_reconstruction(self, text: str) -> str:
        """
        Reconstrucción ultra-agresiva que combina todas las palabras fragmentadas.
        """
        if not text:
            return ""
        
        import re
        
        # Dividir en líneas
        lines = text.split('\n')
        result_lines = []
        current_section = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_section:
                    # Combinar toda la sección en una sola línea
                    combined = ' '.join(current_section)
                    result_lines.append(combined)
                    current_section = []
                result_lines.append('')
                continue
            
            # Detectar secciones importantes que deben mantenerse separadas
            is_section_header = any(section in line.upper() for section in [
                'EXPERIENCIA', 'EDUCACIÓN', 'HABILIDADES', 'PROYECTOS', 
                'CONTACTO', 'PERFIL', 'RESUMEN', 'EXPERIENCIA LABORAL',
                'PERFIL PROFESIONAL', 'PROYECTOS DESTACADOS'
            ])
            
            # Detectar enlaces y contactos
            is_contact = '@' in line or 'http' in line.lower() or 'linkedin.com' in line.lower() or 'github.com' in line.lower()
            
            # Detectar fechas
            is_date = re.search(r'\d{4}', line)
            
            # Detectar nombres de empresas
            is_company = any(company in line for company in ['Digital Vibe', 'Sberbank', 'Google', 'Microsoft'])
            
            if is_section_header or is_contact or is_date or is_company:
                # Guardar sección acumulada
                if current_section:
                    combined = ' '.join(current_section)
                    result_lines.append(combined)
                    current_section = []
                result_lines.append(line)
            else:
                # Acumular en sección
                current_section.append(line)
        
        # Guardar última sección
        if current_section:
            combined = ' '.join(current_section)
            result_lines.append(combined)
        
        return '\n'.join(result_lines)

    def get_supported_formats(self) -> list:
        """Retorna los formatos soportados por este parser."""
        return self.supported_extensions
