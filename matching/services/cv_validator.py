"""
Validador de CVs para detectar archivos corruptos o que no son CVs reales.
"""
import re
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class CVValidator:
    """Validador para verificar si un texto extraído es realmente un CV."""
    
    def __init__(self):
        # Palabras clave que indican que es un CV
        self.cv_keywords = [
            'experiencia', 'educación', 'habilidades', 'skills', 'trabajo',
            'empleo', 'desarrollador', 'developer', 'programador', 'analista',
            'diseñador', 'designer', 'marketing', 'ventas', 'contador',
            'ingeniero', 'engineer', 'proyecto', 'project', 'certificación',
            'certification', 'idioma', 'language', 'universidad', 'universidad',
            'instituto', 'institute', 'título', 'degree', 'diploma',
            'resumen', 'summary', 'objetivo', 'objective', 'perfil', 'profile'
        ]
        
        # Patrones que indican documentos financieros/nómina
        self.financial_patterns = [
            r'\d{10,}',  # Números largos (códigos de cuenta)
            r'\d{4}\.\d{2}\.\d{2}',  # Fechas en formato específico
            r'payroll',  # Palabra "payroll"
            r'nómina',  # Palabra "nómina"
            r'banco',  # Referencias bancarias
            r'cuenta',  # Referencias a cuentas
            r'\$\d+\.?\d*',  # Montos en dinero
            r'saldo',  # Saldos bancarios
        ]
        
        # Patrones que indican documentos técnicos/legales
        self.technical_patterns = [
            r'cláusula',  # Contratos legales
            r'contrato',  # Contratos
            r'factura',  # Facturas
            r'recibo',  # Recibos
            r'comprobante',  # Comprobantes
        ]
    
    def validate_cv_content(self, text: str, filename: str = "") -> Dict[str, Any]:
        """
        Valida si el contenido extraído parece ser un CV real.
        
        Args:
            text: Texto extraído del archivo
            filename: Nombre del archivo (opcional)
            
        Returns:
            Dict con 'is_valid', 'confidence', 'reason', 'suggestions'
        """
        if not text or len(text.strip()) < 50:
            return {
                'is_valid': False,
                'confidence': 0.0,
                'reason': 'El archivo contiene muy poco texto o está vacío',
                'suggestions': ['Verifica que el archivo sea un CV válido', 'Asegúrate de que el archivo no esté corrupto']
            }
        
        text_lower = text.lower()
        filename_lower = filename.lower()
        
        # Verificar patrones financieros (documentos de nómina, etc.)
        financial_score = self._calculate_financial_score(text_lower, filename_lower)
        if financial_score > 0.5:  # Reducido el umbral para detectar mejor documentos financieros
            return {
                'is_valid': False,
                'confidence': 1.0 - financial_score,
                'reason': 'El archivo parece ser un documento financiero/nómina, no un CV',
                'suggestions': ['Sube tu CV profesional en lugar de documentos de nómina', 'El archivo debe contener información sobre tu experiencia y habilidades']
            }
        
        # Verificar patrones técnicos/legales
        technical_score = self._calculate_technical_score(text_lower, filename_lower)
        if technical_score > 0.6:
            return {
                'is_valid': False,
                'confidence': 1.0 - technical_score,
                'reason': 'El archivo parece ser un documento legal/técnico, no un CV',
                'suggestions': ['Sube tu CV profesional', 'El archivo debe contener información sobre tu perfil profesional']
            }
        
        # Verificar palabras clave de CV
        cv_score = self._calculate_cv_score(text_lower)
        if cv_score < 0.3:
            return {
                'is_valid': False,
                'confidence': cv_score,
                'reason': 'El archivo no parece contener información típica de un CV',
                'suggestions': ['Asegúrate de que el archivo sea tu CV profesional', 'El CV debe incluir secciones como experiencia, educación y habilidades']
            }
        
        # Calcular confianza general
        confidence = min(cv_score + (1 - financial_score) * 0.3 + (1 - technical_score) * 0.2, 1.0)
        
        return {
            'is_valid': True,
            'confidence': confidence,
            'reason': 'El archivo parece ser un CV válido',
            'suggestions': []
        }
    
    def _calculate_financial_score(self, text: str, filename: str) -> float:
        """Calcula qué tan probable es que sea un documento financiero."""
        score = 0.0
        total_patterns = len(self.financial_patterns)
        
        for pattern in self.financial_patterns:
            if re.search(pattern, text):
                score += 1.0 / total_patterns
        
        # Bonus si el nombre del archivo contiene palabras financieras
        if any(word in filename for word in ['payroll', 'nómina', 'banco', 'cuenta', 'salario']):
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_technical_score(self, text: str, filename: str) -> float:
        """Calcula qué tan probable es que sea un documento técnico/legal."""
        score = 0.0
        total_patterns = len(self.technical_patterns)
        
        for pattern in self.technical_patterns:
            if re.search(pattern, text):
                score += 1.0 / total_patterns
        
        return min(score, 1.0)
    
    def _calculate_cv_score(self, text: str) -> float:
        """Calcula qué tan probable es que sea un CV."""
        score = 0.0
        total_keywords = len(self.cv_keywords)
        
        for keyword in self.cv_keywords:
            if keyword in text:
                score += 1.0 / total_keywords
        
        # Bonus por longitud razonable del texto
        if 200 <= len(text) <= 5000:
            score += 0.1
        
        # Bonus por tener múltiples líneas (estructura de CV)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if len(lines) >= 10:
            score += 0.1
        
        return min(score, 1.0)
    
    def get_validation_message(self, validation_result: Dict[str, Any]) -> str:
        """Genera un mensaje de validación amigable para el usuario."""
        if validation_result['is_valid']:
            confidence = validation_result['confidence']
            if confidence > 0.8:
                return "✅ CV válido detectado"
            elif confidence > 0.6:
                return "⚠️ CV detectado con baja confianza"
            else:
                return "❓ CV detectado pero con muy baja confianza"
        else:
            return f"❌ {validation_result['reason']}"


# Instancia global del validador
cv_validator = CVValidator()
