import os
import time
import logging
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


LOGIN_URL = "https://dvcarreras.davinci.edu.ar/login.html"


def _build_requests_proxies() -> Optional[Dict[str, str]]:
    proxy_url = os.getenv("PROXY_URL")
    if not proxy_url:
        return None
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def _default_headers() -> Dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    }


def bootstrap_dv_session(max_attempts: int = 5, sleep_seconds: float = 1.5) -> List[Dict]:
    """Intenta obtener cookies iniciales del portal usando requests.

    Devuelve una lista de cookies compatibles con Playwright storage_state.
    """
    session = requests.Session()
    session.headers.update(_default_headers())

    proxies = _build_requests_proxies()
    if proxies:
        logger.info("Bootstrap: usando proxy para requests")

    cookies_result: List[Dict] = []

    for attempt in range(1, max_attempts + 1):
        try:
            resp = session.get(LOGIN_URL, timeout=20, proxies=proxies, allow_redirects=True)
            logger.info(
                f"Bootstrap intento {attempt}: status={resp.status_code} url={resp.url} set_cookies={len(resp.cookies)}"
            )

            # Convertir cookies a formato Playwright storage_state
            for c in session.cookies:
                cookie_dict = {
                    "name": c.name,
                    "value": c.value,
                    "domain": c.domain or ".dvcarreras.davinci.edu.ar",
                    "path": c.path or "/",
                    # Playwright espera epoch seconds; si no hay, usar 0 (session cookie)
                    "expires": int(c.expires) if c.expires else 0,
                    "httpOnly": bool(getattr(c, "_rest", {}).get("HttpOnly", False)),
                    "secure": c.secure,
                    "sameSite": "Lax",
                }
                cookies_result.append(cookie_dict)

            # Si ya tenemos alguna cookie, cortar el loop
            if cookies_result:
                break

        except Exception as e:
            logger.warning(f"Bootstrap error intento {attempt}: {e}")
        time.sleep(sleep_seconds)

    logger.info(f"Bootstrap completado. Cookies obtenidas: {len(cookies_result)}")
    return cookies_result


def build_playwright_proxy() -> Optional[Dict[str, str]]:
    """Devuelve diccionario de proxy para Playwright.launch si hay configuración."""
    proxy_url = os.getenv("PROXY_URL")
    if not proxy_url:
        return None
    result = {"server": proxy_url}
    if os.getenv("PROXY_USERNAME") and os.getenv("PROXY_PASSWORD"):
        result["username"] = os.getenv("PROXY_USERNAME")
        result["password"] = os.getenv("PROXY_PASSWORD")
    return result



