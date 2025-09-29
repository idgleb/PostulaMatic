"""
Utilidades para decodificar emails protegidos por Cloudflare.
"""
import re
import base64
import logging

logger = logging.getLogger(__name__)


def decode_cloudflare_email(encrypted_email: str) -> str:
    """
    Decodifica un email protegido por Cloudflare.
    
    Cloudflare usa un sistema de protección que ofusca emails con:
    - Un hash hexadecimal en data-cfemail
    - Caracteres HTML entities para el texto visible
    
    Args:
        encrypted_email: Email encriptado en formato Cloudflare
        
    Returns:
        Email decodificado o string vacío si no se puede decodificar
    """
    try:
        # Buscar el patrón de Cloudflare: data-cfemail="hash"
        cf_email_pattern = r'data-cfemail="([a-f0-9]+)"'
        match = re.search(cf_email_pattern, encrypted_email)
        
        if not match:
            logger.warning(f"No se encontró patrón de Cloudflare en: {encrypted_email}")
            return ""
        
        encrypted_hash = match.group(1)
        
        # Decodificar el hash (algoritmo de Cloudflare)
        # El hash es una versión ofuscada del email
        decoded_email = ""
        
        # Cloudflare usa un XOR simple con el primer byte del hash
        key = int(encrypted_hash[:2], 16)  # Primer byte como clave
        
        # Procesar cada par de caracteres hex
        for i in range(2, len(encrypted_hash), 2):
            if i + 1 < len(encrypted_hash):
                encrypted_byte = int(encrypted_hash[i:i+2], 16)
                decoded_byte = encrypted_byte ^ key
                decoded_email += chr(decoded_byte)
        
        # Validar que sea un email válido
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, decoded_email):
            logger.info(f"Email decodificado exitosamente: {decoded_email}")
            return decoded_email
        else:
            logger.warning(f"Email decodificado no válido: {decoded_email}")
            return ""
            
    except Exception as e:
        logger.error(f"Error decodificando email de Cloudflare: {e}")
        return ""


def extract_email_from_html(html_content: str) -> str:
    """
    Extrae y decodifica el email de un fragmento HTML que contiene protección de Cloudflare.
    
    Args:
        html_content: HTML que contiene el email protegido
        
    Returns:
        Email decodificado o string vacío
    """
    try:
        # Buscar el enlace con protección de Cloudflare
        cf_email_pattern = r'<a[^>]*href="/cdn-cgi/l/email-protection"[^>]*class="__cf_email__"[^>]*data-cfemail="([a-f0-9]+)"[^>]*>.*?</a>'
        match = re.search(cf_email_pattern, html_content, re.DOTALL)
        
        if match:
            encrypted_html = match.group(0)
            return decode_cloudflare_email(encrypted_html)
        
        # Si no encuentra el patrón completo, buscar solo el data-cfemail
        cf_data_pattern = r'data-cfemail="([a-f0-9]+)"'
        data_match = re.search(cf_data_pattern, html_content)
        
        if data_match:
            encrypted_hash = data_match.group(1)
            return decode_cloudflare_email(f'data-cfemail="{encrypted_hash}"')
        
        logger.warning(f"No se encontró email protegido en HTML: {html_content[:200]}...")
        return ""
        
    except Exception as e:
        logger.error(f"Error extrayendo email del HTML: {e}")
        return ""


# Función de conveniencia para uso en el scraper
def get_email_from_job_html(html_content: str) -> str:
    """
    Función principal para extraer email de HTML de oferta de trabajo.
    
    Args:
        html_content: HTML completo de la oferta
        
    Returns:
        Email decodificado o string vacío
    """
    return extract_email_from_html(html_content)


