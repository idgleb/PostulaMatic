"""
Cliente para comunicarse con FlareSolverr.
FlareSolverr es un proxy server que bypasea la protección de Cloudflare.
"""
import json
import logging
import os
import requests
from typing import Dict, Optional, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class FlareSolverrClient:
    """Cliente para comunicarse con FlareSolverr API."""

    def __init__(self, base_url: str = None):
        """
        Inicializa el cliente FlareSolverr.

        Args:
            base_url: URL base de FlareSolverr. Por defecto usa variable de entorno
        """
        self.base_url = base_url or os.getenv("FLARESOLVERR_URL", "http://flaresolverr:8191")
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "PostulaMatic/1.0"
        })

    def _make_request(self, endpoint: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Realiza una petición a FlareSolverr.

        Args:
            endpoint: Endpoint de la API
            data: Datos a enviar

        Returns:
            Respuesta de FlareSolverr o None si hay error
        """
        url = urljoin(self.base_url, endpoint)
        
        try:
            logger.info(f"Enviando petición a FlareSolverr: {url}")
            response = self.session.post(url, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"FlareSolverr respondió con status: {result.get('status')}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error comunicándose con FlareSolverr: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando respuesta de FlareSolverr: {e}")
            return None

    def solve_page(self, url: str, user_agent: str = None, max_timeout: int = 60000, cookies: list = None) -> Optional[Dict[str, Any]]:
        """
        Resuelve una página protegida por Cloudflare.

        Args:
            url: URL a resolver
            user_agent: User-Agent personalizado
            max_timeout: Timeout máximo en milisegundos
            cookies: Lista de cookies a usar

        Returns:
            Diccionario con la respuesta resuelta o None si falla
        """
        data = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": max_timeout,
            "returnOnlyCookies": False
        }
        
        if user_agent:
            data["userAgent"] = user_agent
            
        if cookies:
            # Convertir cookies de Playwright a formato de FlareSolverr
            flaresolverr_cookies = []
            for cookie in cookies:
                flaresolverr_cookies.append({
                    "name": cookie.get("name"),
                    "value": cookie.get("value"),
                    "domain": cookie.get("domain"),
                    "path": cookie.get("path", "/"),
                    "secure": cookie.get("secure", False),
                    "httpOnly": cookie.get("httpOnly", False),
                    "sameSite": cookie.get("sameSite", "Lax")
                })
            data["cookies"] = flaresolverr_cookies

        return self._make_request("v1", data)

    def solve_post(self, url: str, post_data: str, user_agent: str = None, max_timeout: int = 60000) -> Optional[Dict[str, Any]]:
        """
        Resuelve un POST a una página protegida por Cloudflare.

        Args:
            url: URL a resolver
            post_data: Datos del POST en formato application/x-www-form-urlencoded
            user_agent: User-Agent personalizado
            max_timeout: Timeout máximo en milisegundos

        Returns:
            Diccionario con la respuesta resuelta o None si falla
        """
        data = {
            "cmd": "request.post",
            "url": url,
            "postData": post_data,
            "maxTimeout": max_timeout,
            "returnOnlyCookies": False
        }
        
        if user_agent:
            data["userAgent"] = user_agent

        return self._make_request("v1", data)

    def get_cookies(self, url: str, user_agent: str = None, max_timeout: int = 60000) -> Optional[Dict[str, Any]]:
        """
        Obtiene solo las cookies de una página protegida por Cloudflare.

        Args:
            url: URL a resolver
            user_agent: User-Agent personalizado
            max_timeout: Timeout máximo en milisegundos

        Returns:
            Diccionario con las cookies o None si falla
        """
        data = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": max_timeout,
            "returnOnlyCookies": True
        }
        
        if user_agent:
            data["userAgent"] = user_agent

        return self._make_request("v1", data)

    def is_healthy(self) -> bool:
        """
        Verifica si FlareSolverr está funcionando correctamente.

        Returns:
            True si está funcionando, False en caso contrario
        """
        try:
            url = urljoin(self.base_url, "v1")
            data = {"cmd": "request.get", "url": "https://www.google.com", "maxTimeout": 10000}
            
            response = self.session.post(url, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result.get("status") == "ok"
            
        except Exception as e:
            logger.error(f"FlareSolverr no está funcionando: {e}")
            return False


# Instancia global del cliente
_flaresolverr_client = None


def get_flaresolverr_client() -> FlareSolverrClient:
    """Obtiene la instancia global del cliente FlareSolverr."""
    global _flaresolverr_client
    if _flaresolverr_client is None:
        _flaresolverr_client = FlareSolverrClient()
    return _flaresolverr_client


def test_flaresolverr_connection() -> Dict[str, Any]:
    """
    Prueba la conexión con FlareSolverr.

    Returns:
        Diccionario con el resultado de la prueba
    """
    client = get_flaresolverr_client()
    
    try:
        # Probar con una página simple
        result = client.solve_page("https://httpbin.org/headers", max_timeout=30000)
        
        if result and result.get("status") == "ok":
            return {
                "success": True,
                "message": "FlareSolverr funcionando correctamente",
                "response": result.get("solution", {}).get("response", "")[:500] + "..." if len(result.get("solution", {}).get("response", "")) > 500 else result.get("solution", {}).get("response", "")
            }
        else:
            return {
                "success": False,
                "message": f"FlareSolverr falló: {result.get('message', 'Error desconocido') if result else 'Sin respuesta'}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Error probando FlareSolverr: {str(e)}"
        }
