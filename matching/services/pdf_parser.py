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

                # Extraer texto de todas las páginas
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
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
        Limpia el texto extraído del PDF, removiendo metadatos y normalizando.

        Args:
            text: Texto crudo del PDF

        Returns:
            Texto limpio y legible
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

        # Limpiar líneas y normalizar
        lines = cleaned_text.split("\n")
        clean_lines = []

        for line in lines:
            line = line.strip()

            # Filtrar líneas que son solo metadatos
            if (
                len(line) > 3
                and not re.match(r"^[\d\s.,\-+]+$", line)  # No solo números
                and not re.match(r"^[0-9.\s]+$", line)  # No solo decimales
                and "cm" not in line  # No coordenadas
                and "RG" not in line  # No colores
                and "J" not in line  # No comandos PDF
                and "m" not in line
                or "l" not in line
            ):  # No comandos de línea
                clean_lines.append(line)

        # Unir líneas y limpiar espacios múltiples
        final_text = "\n".join(clean_lines)
        final_text = " ".join(final_text.split())  # Normalizar espacios

        return final_text

    def get_supported_formats(self) -> list:
        """Retorna los formatos soportados por este parser."""
        return self.supported_extensions
