import os
import time
import logging
from typing import Optional, Dict

import requests

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """Interfaz simple para resolver CAPTCHAs (Turnstile/hCaptcha) vía proveedor externo.

    Actualmente implementa 2Captcha si se configura CAPTCHA_PROVIDER=2captcha y
    CAPTCHA_API_KEY en variables de entorno. Devuelve el token (string) o None si falla.
    """

    def __init__(self):
        self.provider = (os.getenv("CAPTCHA_PROVIDER") or "").lower().strip()
        self.api_key = os.getenv("CAPTCHA_API_KEY")

    def is_configured(self) -> bool:
        return bool(self.provider == "2captcha" and self.api_key)

    # --- API públicas -----------------------------------------------------
    def solve_turnstile(self, page_url: str, site_key: str, **kwargs) -> Optional[str]:
        if not self.is_configured():
            logger.info("CaptchaSolver no configurado; omitiendo resolución de Turnstile")
            return None
        return self._solve_2captcha(method="turnstile", page_url=page_url, site_key=site_key)

    def solve_hcaptcha(self, page_url: str, site_key: str, **kwargs) -> Optional[str]:
        if not self.is_configured():
            logger.info("CaptchaSolver no configurado; omitiendo resolución de hCaptcha")
            return None
        return self._solve_2captcha(method="hcaptcha", page_url=page_url, site_key=site_key)

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


