"""
Utilidad para encriptar y desencriptar credenciales usando Fernet.
"""
import os
import base64
from cryptography.fernet import Fernet
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """Clase para manejar encriptación de credenciales."""
    
    def __init__(self):
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self):
        """Obtiene o crea la clave de encriptación."""
        # Intentar obtener de variables de entorno primero
        key = os.environ.get('ENCRYPTION_KEY')
        
        if key:
            try:
                # Verificar que la clave es válida
                Fernet(key.encode())
                return key.encode()
            except Exception as e:
                logger.warning(f"Clave de encriptación inválida en ENCRYPTION_KEY: {e}")
        
        # Si no hay clave válida, generar una nueva
        key = Fernet.generate_key()
        
        # Guardar en archivo .env para uso futuro
        env_file = settings.BASE_DIR / '.env'
        if not env_file.exists():
            with open(env_file, 'w') as f:
                f.write(f'ENCRYPTION_KEY={key.decode()}\n')
        else:
            # Verificar si ya existe ENCRYPTION_KEY en el archivo
            with open(env_file, 'r') as f:
                content = f.read()
            
            if 'ENCRYPTION_KEY=' not in content:
                with open(env_file, 'a') as f:
                    f.write(f'ENCRYPTION_KEY={key.decode()}\n')
        
        logger.info("Nueva clave de encriptación generada y guardada en .env")
        return key
    
    def encrypt(self, text: str) -> str:
        """
        Encripta un texto.
        
        Args:
            text: Texto a encriptar
            
        Returns:
            Texto encriptado en base64
        """
        if not text:
            return ""
        
        try:
            encrypted_bytes = self.cipher.encrypt(text.encode())
            return base64.b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Error encriptando texto: {e}")
            raise
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Desencripta un texto.
        
        Args:
            encrypted_text: Texto encriptado en base64
            
        Returns:
            Texto desencriptado
        """
        if not encrypted_text:
            return ""
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_text.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Error desencriptando texto: {e}")
            # Si falla la desencriptación, puede ser texto plano antiguo
            # Retornar el texto tal como está
            logger.warning("Asumiendo texto plano para credenciales existentes")
            return encrypted_text
    
    def is_encrypted(self, text: str) -> bool:
        """
        Verifica si un texto está encriptado.
        
        Args:
            text: Texto a verificar
            
        Returns:
            True si está encriptado, False si es texto plano
        """
        if not text:
            return False
        
        try:
            # Intentar decodificar base64 y desencriptar
            encrypted_bytes = base64.b64decode(text.encode())
            # Verificar que sea válido Fernet
            self.cipher.decrypt(encrypted_bytes)
            return True
        except Exception as e:
            # Si falla, no está encriptado
            return False


# Instancia global del encriptador
credential_encryption = CredentialEncryption()


def encrypt_credential(text: str) -> str:
    """
    Función de conveniencia para encriptar credenciales.
    
    Args:
        text: Texto a encriptar
        
    Returns:
        Texto encriptado
    """
    return credential_encryption.encrypt(text)


def decrypt_credential(encrypted_text: str) -> str:
    """
    Función de conveniencia para desencriptar credenciales.
    
    Args:
        encrypted_text: Texto encriptado
        
    Returns:
        Texto desencriptado
    """
    return credential_encryption.decrypt(encrypted_text)


def is_credential_encrypted(text: str) -> bool:
    """
    Función de conveniencia para verificar si una credencial está encriptada.
    
    Args:
        text: Texto a verificar
        
    Returns:
        True si está encriptado, False si es texto plano
    """
    return credential_encryption.is_encrypted(text)
