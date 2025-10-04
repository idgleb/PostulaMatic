"""
Cliente para scraping autenticado de dvcarreras.davinci.edu.ar
Maneja login, rate limiting y extracción de ofertas de trabajo.
"""

import hashlib
import logging
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class JobPostingData:
    """Estructura de datos para una oferta de trabajo."""

    external_id: str
    title: str
    description: str
    email: str
    url: str
    posted_at: Optional[datetime] = None
    raw_html: str = ""


class DVCarrerasScraperError(Exception):
    """Excepción personalizada para errores del scraper."""

    pass


def is_duplicate_job(job_data: JobPostingData) -> str:
    """
    Verifica si una oferta de trabajo ya existe en la base de datos.

    Args:
        job_data: Datos de la oferta a verificar

    Returns:
        'new': Nueva oferta
        'duplicate': Oferta duplicada
    """
    from matching.models import JobPosting

    # Buscar por email + título + descripción (combinación única)
    existing = JobPosting.objects.filter(
        email=job_data.email, title=job_data.title, description=job_data.description
    ).first()

    if existing:
        logger.info(f"Oferta duplicada encontrada: {job_data.title} - {job_data.email}")
        return "duplicate"

    return "new"


def generate_external_id(title: str, email: str, description: str) -> str:
    """
    Genera un ID único basado en el contenido de la oferta.

    Args:
        title: Título de la oferta
        email: Email de contacto
        description: Descripción de la oferta

    Returns:
        ID único generado
    """
    content = f"{title}|{email}|{description}"
    return hashlib.md5(content.encode()).hexdigest()


class DVCarrerasClient:
    """Cliente para scraping de dvcarreras.davinci.edu.ar"""

    BASE_URL = "https://dvcarreras.davinci.edu.ar"
    LOGIN_URL = "https://dvcarreras.davinci.edu.ar/login.html"
    JOB_BOARD_URL = "https://dvcarreras.davinci.edu.ar/job_board-0.html"

    def __init__(
        self,
        username: str,
        password: str,
        rate_limit_delay: Tuple[float, float] = (1.0, 3.0),
    ):
        """
        Inicializa el cliente con credenciales.

        Args:
            username: Usuario para login
            password: Contraseña para login
            rate_limit_delay: Tupla (min_delay, max_delay) en segundos para rate limiting
        """
        self.username = username
        self.password = password
        self.rate_limit_delay = rate_limit_delay

        self.session = requests.Session()
        # Headers más convincentes para evitar detección
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "DNT": "1",
                "Sec-GPC": "1",
            }
        )

        self._is_authenticated = False

    def _random_delay(self):
        """Aplica un delay aleatorio para simular comportamiento humano."""
        delay = random.uniform(*self.rate_limit_delay)
        logger.debug(f"Aplicando delay de {delay:.2f} segundos")
        time.sleep(delay)

    def _get_csrf_token(self, response_text: str) -> Optional[str]:
        """Extrae el token CSRF del HTML de respuesta."""
        soup = BeautifulSoup(response_text, "html.parser")

        # Buscar token CSRF en diferentes ubicaciones comunes
        csrf_inputs = [
            soup.find("input", {"name": "csrf_token"}),
            soup.find("input", {"name": "_token"}),
            soup.find("input", {"name": "authenticity_token"}),
            soup.find("meta", {"name": "csrf-token"}),
        ]

        for csrf_input in csrf_inputs:
            if csrf_input:
                return csrf_input.get("value") or csrf_input.get("content")

        return None

    def login(self) -> bool:
        """
        Realiza login en dvcarreras con múltiples intentos y estrategias.

        Returns:
            True si el login fue exitoso, False en caso contrario
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                logger.info(
                    f"Iniciando login para usuario: {self.username} (intento {attempt + 1}/{max_retries})"
                )

                # Delay más largo en el primer intento
                if attempt == 0:
                    time.sleep(random.uniform(3, 7))
                else:
                    self._random_delay()

                # Obtener página de login
                logger.debug(f"Solicitando página de login: {self.LOGIN_URL}")
                response = self.session.get(self.LOGIN_URL, timeout=30)
                logger.debug(
                    f"Respuesta del login: {response.status_code} - {response.reason}"
                )

                if response.status_code == 403:
                    logger.error(
                        f"Acceso denegado (403) a {self.LOGIN_URL}. Intento {attempt + 1}/{max_retries}"
                    )
                    if attempt < max_retries - 1:
                        # Esperar más tiempo antes del siguiente intento
                        wait_time = random.uniform(10, 20)
                        logger.info(
                            f"Esperando {wait_time:.1f} segundos antes del siguiente intento..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            "Todos los intentos de login fallaron con error 403"
                        )
                        logger.error(
                            "- Posibles causas: Rate limiting, User-Agent bloqueado, o protección anti-bot"
                        )
                        return False

                response.raise_for_status()

                # Parsear formulario de login
                soup = BeautifulSoup(response.text, "html.parser")
                login_form = soup.find("form")

                if not login_form:
                    logger.error("No se encontró formulario de login")
                    if attempt < max_retries - 1:
                        continue
                    return False

                # Preparar datos del formulario
                form_data = {}

                # Buscar campos de usuario y contraseña
                username_field = soup.find("input", {"name": "username"}) or soup.find(
                    "input", {"name": "user"}
                )
                password_field = soup.find("input", {"name": "password"}) or soup.find(
                    "input", {"name": "pass"}
                )

                if not username_field or not password_field:
                    logger.error(
                        "No se encontraron campos de usuario/contraseña en el formulario"
                    )
                    if attempt < max_retries - 1:
                        continue
                    return False

                form_data[username_field["name"]] = self.username
                form_data[password_field["name"]] = self.password

                # Buscar token CSRF
                csrf_token = self._get_csrf_token(response.text)
                if csrf_token:
                    form_data["csrf_token"] = csrf_token
                    logger.debug("Token CSRF encontrado y agregado")

                # Obtener URL de acción del formulario
                form_action = login_form.get("action", "")
                if form_action.startswith("/"):
                    login_url = urljoin(self.BASE_URL, form_action)
                elif form_action.startswith("http"):
                    login_url = form_action
                else:
                    login_url = self.LOGIN_URL

                # Enviar formulario de login
                self._random_delay()
                login_response = self.session.post(
                    login_url, data=form_data, timeout=30, allow_redirects=True
                )

                # Verificar si el login fue exitoso
                if self._is_login_successful(login_response):
                    self._is_authenticated = True
                    logger.info("Login exitoso")
                    return True
                else:
                    logger.error(
                        f"Login fallido - credenciales incorrectas o error en el formulario (intento {attempt + 1})"
                    )
                    if attempt < max_retries - 1:
                        wait_time = random.uniform(5, 10)
                        logger.info(
                            f"Esperando {wait_time:.1f} segundos antes del siguiente intento..."
                        )
                        time.sleep(wait_time)
                        continue
                    return False

            except requests.RequestException as e:
                logger.error(
                    f"Error de conexión durante login (intento {attempt + 1}): {e}"
                )
                if attempt < max_retries - 1:
                    wait_time = random.uniform(10, 15)
                    logger.info(
                        f"Esperando {wait_time:.1f} segundos antes del siguiente intento..."
                    )
                    time.sleep(wait_time)
                    continue
                return False
            except Exception as e:
                logger.error(
                    f"Error inesperado durante login (intento {attempt + 1}): {e}"
                )
                if attempt < max_retries - 1:
                    continue
                return False

        return False

    def _is_login_successful(self, response: requests.Response) -> bool:
        """
        Verifica si el login fue exitoso basándose en la respuesta.

        Args:
            response: Respuesta HTTP del login

        Returns:
            True si el login fue exitoso
        """
        # Verificar redirección a página principal
        if response.url != self.LOGIN_URL and "login" not in response.url.lower():
            return True

        # Verificar contenido que indique login exitoso
        response_text = response.text.lower()
        success_indicators = ["dashboard", "welcome", "profile", "logout"]
        error_indicators = ["invalid", "incorrect", "error", "failed"]

        for indicator in success_indicators:
            if indicator in response_text:
                return True

        for indicator in error_indicators:
            if indicator in response_text:
                return False

        # Si no hay indicadores claros, asumir éxito si no hay redirección al login
        return response.status_code == 200 and "login" not in response.url.lower()

    def scrape_job_board(self, max_pages: int = 5) -> List[JobPostingData]:
        """
        Scrapea ofertas del job board.

        Args:
            max_pages: Número máximo de páginas a scrapear

        Returns:
            Lista de ofertas de trabajo encontradas
        """
        if not self._is_authenticated:
            logger.error("No está autenticado. Debe hacer login primero.")
            raise DVCarrerasScraperError("Usuario no autenticado")

        job_postings = []
        new_count = 0
        duplicate_count = 0

        try:
            for page in range(max_pages):
                logger.info(f"Scrapeando página {page + 1} del job board")

                # Construir URL de la página
                if page == 0:
                    url = self.JOB_BOARD_URL
                else:
                    url = f"{self.BASE_URL}/job_board-{page}.html"

                # Obtener página
                self._random_delay()
                response = self.session.get(url, timeout=30)
                response.raise_for_status()

                # Parsear ofertas de la página
                page_jobs = self._parse_job_board_page(response.text, url)

                # Verificar duplicados para cada oferta
                for job in page_jobs:
                    if is_duplicate_job(job) == "new":
                        job_postings.append(job)
                        new_count += 1
                        logger.info(f"Nueva oferta: {job.title}")
                    else:
                        duplicate_count += 1
                        logger.info(f"Oferta duplicada omitida: {job.title}")

                logger.info(
                    f"Página {page + 1}: {len(page_jobs)} ofertas encontradas, {new_count} nuevas, {duplicate_count} duplicadas"
                )

                # Si no hay más ofertas, parar
                if not page_jobs:
                    logger.info("No hay más ofertas. Deteniendo scraping.")
                    break

            logger.info(
                f"Scraping completado. Total: {len(job_postings)} nuevas, {duplicate_count} duplicadas omitidas"
            )
            return job_postings

        except requests.RequestException as e:
            logger.error(f"Error de conexión durante scraping: {e}")
            raise DVCarrerasScraperError(f"Error de conexión: {e}")
        except Exception as e:
            logger.error(f"Error inesperado durante scraping: {e}")
            raise DVCarrerasScraperError(f"Error inesperado: {e}")

    def _parse_job_board_page(
        self, html_content: str, page_url: str
    ) -> List[JobPostingData]:
        """
        Parsea una página del job board y extrae las ofertas.

        Args:
            html_content: Contenido HTML de la página
            page_url: URL de la página actual

        Returns:
            Lista de ofertas parseadas
        """
        soup = BeautifulSoup(html_content, "html.parser")
        job_postings = []

        # Buscar filas de tabla que contengan ofertas
        job_containers = soup.find_all("tr")

        logger.debug(f"Encontrados {len(job_containers)} filas de tabla")

        for container in job_containers:
            try:
                # Verificar que la fila contenga una oferta (tiene <strong> con título)
                if container.find("strong"):
                    job_data = self._extract_job_data(container, page_url)
                    if job_data:
                        job_postings.append(job_data)
            except Exception as e:
                logger.warning(f"Error parseando oferta: {e}")
                continue

        return job_postings

    def _extract_job_data(self, container, base_url: str) -> Optional[JobPostingData]:
        """
        Extrae datos de una oferta de trabajo individual.

        Args:
            container: Elemento HTML contenedor de la oferta
            base_url: URL base para resolver enlaces relativos

        Returns:
            Datos de la oferta o None si no se puede extraer
        """
        try:
            # Buscar título en <strong>
            title_elem = container.find("strong")

            if not title_elem:
                return None

            title = title_elem.get_text(strip=True)
            if not title or len(title) < 3:
                return None

            # Buscar descripción en <small>
            desc_elem = container.find("small")
            description = desc_elem.get_text(strip=True) if desc_elem else ""

            # Extraer email de Cloudflare protection
            email = self._extract_email_from_cloudflare(container)
            if not email:
                return None

            # Buscar enlace
            link_elem = container.find("a", href=True)
            if link_elem:
                url = urljoin(base_url, link_elem["href"])
            else:
                url = base_url

            # Generar ID único basado en contenido
            external_id = generate_external_id(title, email, description)

            # Extraer fecha si está disponible
            posted_at = self._extract_posted_date(container)

            return JobPostingData(
                external_id=external_id,
                title=title,
                description=description,
                email=email,
                url=url,
                posted_at=posted_at,
                raw_html=str(container),
            )

        except Exception as e:
            logger.warning(f"Error extrayendo datos de oferta: {e}")
            return None

    def _extract_posted_date(self, container) -> Optional[datetime]:
        """Extrae fecha de publicación si está disponible."""
        try:
            date_elem = container.find(
                "span", class_=re.compile(r"date|time", re.I)
            ) or container.find("div", class_=re.compile(r"date|time", re.I))

            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # Intentar parsear diferentes formatos de fecha
                date_formats = [
                    "%d/%m/%Y",
                    "%Y-%m-%d",
                    "%d-%m-%Y",
                    "%B %d, %Y",
                    "%d de %B de %Y",
                ]

                for fmt in date_formats:
                    try:
                        return datetime.strptime(date_text, fmt)
                    except ValueError:
                        continue

            return None
        except Exception:
            return None

    def _extract_email_from_cloudflare(self, container) -> Optional[str]:
        """
        Extrae email de Cloudflare protection.

        Args:
            container: Elemento HTML contenedor

        Returns:
            Email decodificado o None si no se encuentra
        """
        try:
            # Buscar enlaces con protección de Cloudflare
            cf_links = container.find_all("a", href="/cdn-cgi/l/email-protection")

            for link in cf_links:
                # Obtener el hash de data-cfemail
                cf_hash = link.get("data-cfemail")
                if cf_hash:
                    # Decodificar el hash de Cloudflare
                    email = self._decode_cloudflare_email(cf_hash)
                    if email:
                        return email

            return None
        except Exception as e:
            logger.warning(f"Error extrayendo email de Cloudflare: {e}")
            return None

    def _decode_cloudflare_email(self, cf_hash: str) -> Optional[str]:
        """
        Decodifica email protegido por Cloudflare.

        Args:
            cf_hash: Hash de data-cfemail

        Returns:
            Email decodificado o None si falla
        """
        try:
            # Convertir hash hex a bytes
            hash_bytes = bytes.fromhex(cf_hash)

            # Decodificar usando el algoritmo de Cloudflare
            email = ""
            for i, byte in enumerate(hash_bytes):
                # Algoritmo de decodificación de Cloudflare
                decoded_char = chr(byte ^ 0x42)  # XOR con 0x42
                email += decoded_char

            # Verificar que sea un email válido
            if "@" in email and "." in email:
                return email

            return None
        except Exception as e:
            logger.warning(f"Error decodificando email de Cloudflare: {e}")
            return None

    def is_authenticated(self) -> bool:
        """Verifica si el cliente está autenticado."""
        return self._is_authenticated

    def logout(self):
        """Cierra la sesión."""
        try:
            if self._is_authenticated:
                self.session.get(f"{self.BASE_URL}/logout", timeout=10)
                self._is_authenticated = False
                logger.info("Sesión cerrada")
        except Exception as e:
            logger.warning(f"Error al cerrar sesión: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.logout()
