"""
Servicio para parsear CVs en formato PDF y DOCX.
Extrae el texto limpio y lo normaliza para procesamiento posterior.
"""
import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path

# PDF parsing
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# DOCX parsing
try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

logger = logging.getLogger(__name__)


class CVParserError(Exception):
    """Excepción personalizada para errores del parser de CV."""
    pass


class CVParser:
    """Parser principal para CVs en diferentes formatos."""
    
    def __init__(self):
        self.supported_formats = []
        if PDF_AVAILABLE:
            self.supported_formats.append('.pdf')
        if DOCX_AVAILABLE:
            self.supported_formats.append('.docx')
    
    def parse_cv(self, file_path: str) -> Dict[str, Any]:
        """
        Parsea un archivo de CV y extrae el texto.
        
        Args:
            file_path: Ruta al archivo de CV
            
        Returns:
            Dict con 'text', 'format', 'word_count', 'pages' (si aplica)
            
        Raises:
            CVParserError: Si el archivo no se puede procesar
        """
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
            if file_extension == '.pdf':
                return self._parse_pdf(file_path)
            elif file_extension == '.docx':
                return self._parse_docx(file_path)
        except Exception as e:
            logger.error(f"Error parseando CV {file_path}: {e}")
            raise CVParserError(f"Error procesando el archivo: {str(e)}")
    
    def _parse_pdf(self, file_path: Path) -> Dict[str, Any]:
        """Parsea un archivo PDF."""
        if not PDF_AVAILABLE:
            raise CVParserError("PyPDF2 no está disponible para procesar PDFs")
        
        text_content = []
        pages = 0
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            pages = len(pdf_reader.pages)
            
            for page_num in range(pages):
                try:
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    if text.strip():
                        text_content.append(text)
                except Exception as e:
                    logger.warning(f"Error extrayendo página {page_num + 1}: {e}")
                    continue
        
        full_text = '\n\n'.join(text_content)
        
        # Normalizar el texto extraído
        normalized_text = self._normalize_text(full_text)
        
        return {
            'text': normalized_text,
            'format': 'pdf',
            'word_count': len(normalized_text.split()),
            'pages': pages
        }
    
    def _parse_docx(self, file_path: Path) -> Dict[str, Any]:
        """Parsea un archivo DOCX."""
        if not DOCX_AVAILABLE:
            raise CVParserError("python-docx no está disponible para procesar DOCX")
        
        try:
            doc = Document(file_path)
            text_content = []
            
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            full_text = '\n'.join(text_content)
            
            # Normalizar el texto extraído
            normalized_text = self._normalize_text(full_text)
            
            return {
                'text': normalized_text,
                'format': 'docx',
                'word_count': len(normalized_text.split()),
                'pages': 1  # DOCX no tiene páginas definidas
            }
            
        except Exception as e:
            raise CVParserError(f"Error procesando archivo DOCX: {str(e)}")
    
    def _normalize_text(self, text: str) -> str:
        """
        Normaliza el texto extraído para mejor procesamiento.
        Reconstruye texto fragmentado línea por línea de manera inteligente.
        Basado en el CV real del usuario.
        
        Args:
            text: Texto crudo extraído del CV
            
        Returns:
            Texto normalizado
        """
        if not text:
            return ""
        
        import re
        
        # Remover caracteres no imprimibles
        text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', text)
        
        # Normalizar espacios múltiples
        text = re.sub(r'[ \t]+', ' ', text)
        
        # Dividir en líneas
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return ""
        
        reconstructed_lines = []
        current_section = ""
        current_paragraph = ""
        
        for i, line in enumerate(lines):
            # Detectar secciones principales
            is_section_header = line in [
                'PERFIL PROFESIONAL', 'EXPERIENCIA LABORAL', 'EDUCACIÓN', 
                'PROYECTOS DESTACADOS', 'HABILIDADES', 'IDIOMAS', 'CERTIFICACIONES'
            ]
            
            # Detectar títulos de trabajo/empresa
            is_job_title = re.match(r'^\d{4}', line) or 'Desarrollador' in line or 'Developer' in line
            
            # Detectar URLs y emails
            is_url_or_email = '@' in line or 'http' in line or '.com' in line or 'github.com' in line or 'linkedin.com' in line
            
            # Detectar si es el final de una oración
            ends_with_period = line.endswith('.') or line.endswith('!') or line.endswith('?')
            
            # Si es una sección principal, mantenerla separada
            if is_section_header:
                if current_paragraph:
                    reconstructed_lines.append(current_paragraph.strip())
                    current_paragraph = ""
                reconstructed_lines.append(line)
                current_section = line
            
            # Si es un título de trabajo, mantenerlo separado
            elif is_job_title:
                if current_paragraph:
                    reconstructed_lines.append(current_paragraph.strip())
                    current_paragraph = ""
                reconstructed_lines.append(line)
            
            # Si es URL o email, mantenerlo separado
            elif is_url_or_email:
                if current_paragraph:
                    reconstructed_lines.append(current_paragraph.strip())
                    current_paragraph = ""
                reconstructed_lines.append(line)
            
            # Si termina con punto, completar párrafo
            elif ends_with_period:
                current_paragraph += " " + line if current_paragraph else line
                reconstructed_lines.append(current_paragraph.strip())
                current_paragraph = ""
            
            # Si es una línea corta (probablemente fragmentada), continuar construyendo
            elif len(line.split()) <= 3 and not line.isupper():
                current_paragraph += " " + line if current_paragraph else line
            
            # Si es una línea normal, continuar construyendo
            else:
                current_paragraph += " " + line if current_paragraph else line
        
        # Agregar el último párrafo si queda algo
        if current_paragraph:
            reconstructed_lines.append(current_paragraph.strip())
        
        # Unir líneas y limpiar
        text = '\n'.join(reconstructed_lines)
        
        # Limpiar saltos de línea múltiples
        text = re.sub(r'\n\s*\n+', '\n\n', text)
        
        # Remover líneas vacías al inicio y final
        text = text.strip()
        
        return text
    
    def get_supported_formats(self) -> list:
        """Retorna la lista de formatos soportados."""
        return self.supported_formats.copy()
    
    def is_supported(self, file_path: str) -> bool:
        """Verifica si el archivo es de un formato soportado."""
        return Path(file_path).suffix.lower() in self.supported_formats


# Instancia global del parser
cv_parser = CVParser()
