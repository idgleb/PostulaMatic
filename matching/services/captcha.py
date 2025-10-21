import os
import time
import logging
from typing import Optional, Dict

try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Interfaz mejorada para resolver CAPTCHAs usando la librería oficial de 2Captcha.

    Implementa Cloudflare Turnstile usando la librería oficial 2captcha-python.
    Devuelve el token (string) o None si falla.
    """

    def __init__(self):
        self.provider = (os.getenv("CAPTCHA_PROVIDER") or "").lower().strip()
        self.api_key = os.getenv("CAPTCHA_API_KEY")
        self.solver = None
        
        if self.is_configured() and TWOCAPTCHA_AVAILABLE:
            try:
                # Configuración optimizada según la documentación oficial
                config = {
                    'apiKey': self.api_key,
                    'defaultTimeout': 120,
                    'recaptchaTimeout': 600,
                    'pollingInterval': 10,
                }
                self.solver = TwoCaptcha(**config)
                logger.info("2Captcha solver inicializado con librería oficial")
            except Exception as e:
                logger.error(f"Error inicializando 2Captcha solver: {e}")
                self.solver = None

    def is_configured(self) -> bool:
        return bool(self.provider == "2captcha" and self.api_key and TWOCAPTCHA_AVAILABLE)

    # --- API públicas -----------------------------------------------------
    def solve_turnstile(self, page_url: str, site_key: str, **kwargs) -> Optional[str]:
        """Resuelve Cloudflare Turnstile usando la librería oficial de 2Captcha."""
        if not self.is_configured() or not self.solver:
            logger.info("CaptchaSolver no configurado; omitiendo resolución de Turnstile")
            return None
        
        try:
            logger.info(f"2Captcha: iniciando resolución Turnstile sitekey={site_key} url={page_url}")
            
            # Usar el método oficial de la librería
            result = self.solver.turnstile(
                sitekey=site_key,
                url=page_url
            )
            
            if result and result.get('code'):
                logger.info(f"2Captcha: Turnstile resuelto exitosamente")
                return result['code']
            else:
                logger.warning(f"2Captcha: respuesta inesperada: {result}")
                return None
                
        except Exception as e:
            logger.error(f"2Captcha: error resolviendo Turnstile: {e}")
            return None

    def solve_hcaptcha(self, page_url: str, site_key: str, **kwargs) -> Optional[str]:
        """Resuelve hCaptcha usando la librería oficial de 2Captcha."""
        if not self.is_configured() or not self.solver:
            logger.info("CaptchaSolver no configurado; omitiendo resolución de hCaptcha")
            return None
        
        try:
            logger.info(f"2Captcha: iniciando resolución hCaptcha sitekey={site_key} url={page_url}")
            
            # Usar el método oficial de la librería
            result = self.solver.hcaptcha(
                sitekey=site_key,
                url=page_url
            )
            
            if result and result.get('code'):
                logger.info(f"2Captcha: hCaptcha resuelto exitosamente")
                return result['code']
            else:
                logger.warning(f"2Captcha: respuesta inesperada: {result}")
                return None
                
        except Exception as e:
            logger.error(f"2Captcha: error resolviendo hCaptcha: {e}")
            return None

    # --- Implementación 2Captcha -----------------------------------------
    def _solve_2captcha(self, method: str, page_url: str, site_key: str) -> Optional[str]:
        """Resuelve usando 2Captcha. Retorna token o None.
        Aumenta timeout de polling a ~90s y registra pasos clave en logs.
        """
        try:
            logger.info(f"2Captcha: iniciando resolución ({method}) sitekey={site_key} url={page_url}")
            in_payload: Dict[str, str] = {
                "key": self.api_key,
                "method": method,  # "turnstile" | "hcaptcha"
                "sitekey": site_key,
                "pageurl": page_url,
                "json": "1",
            }
            # Enviar solicitud de captcha
            res = requests.post("https://2captcha.com/in.php", data=in_payload, timeout=30)
            res.raise_for_status()
            data = res.json()
            if int(data.get("status", 0)) != 1:
                logger.warning(f"2Captcha in.php error: {data}")
                return None
            request_id = data.get("request")

            # Polling por el resultado (hasta 90s)
            for _ in range(45):
                time.sleep(2)
                poll = requests.get(
                    "https://2captcha.com/res.php",
                    params={
                        "key": self.api_key,
                        "action": "get",
                        "id": request_id,
                        "json": "1",
                    },
                    timeout=30,
                )
                poll.raise_for_status()
                pdata = poll.json()
                if pdata.get("status") == 1:
                    logger.info("2Captcha: token recibido correctamente")
                    return pdata.get("request")
                if pdata.get("request") == "ERROR_CAPTCHA_UNSOLVABLE":
                    logger.warning("2Captcha: CAPTCHA no resoluble")
                    return None
            logger.warning("2Captcha: timeout esperando resultado (90s)")
            return None
        except Exception as e:
            logger.error(f"Error resolviendo CAPTCHA con 2Captcha: {e}")
            return None


captcha_solver = CaptchaSolver()


