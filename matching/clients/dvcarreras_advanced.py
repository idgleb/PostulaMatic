"""
Cliente avanzado para scraping de dvcarreras.davinci.edu.ar
Usa proxies, rotación de User-Agents y técnicas anti-detección.
"""

import logging
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class JobPostingData:
    """Estructura de datos para una oferta de trabajo."""

    external_id: str
    title: str
    company: str
    location: str
    description: str
    url: str
    posted_at: Optional[datetime] = None
    raw_html: str = ""


class DVCarrerasAdvancedClient:
    """Cliente avanzado para scraping con técnicas anti-detección"""

    BASE_URL = "https://dvcarreras.davinci.edu.ar"
    LOGIN_URL = "https://dvcarreras.davinci.edu.ar/login.html"
    JOB_BOARD_URL = "https://dvcarreras.davinci.edu.ar/job_board-0.html"

    # Lista de User-Agents realistas
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    ]

    # Lista de proxies gratuitos (pueden no funcionar, pero es un ejemplo)
    PROXIES = [
        # Agregar proxies reales aquí si los tienes
        # {'http': 'http://proxy1:port', 'https': 'https://proxy1:port'},
        # {'http': 'http://proxy2:port', 'https': 'https://proxy2:port'},
    ]

    def __init__(self, username: str, password: str, use_proxies: bool = False):
        """
        Inicializa el cliente avanzado.

        Args:
            username: Usuario para login
            password: Contraseña para login
            use_proxies: Si usar proxies (requiere configuración)
        """
        self.username = username
        self.password = password
        self.use_proxies = use_proxies
        self.session = requests.Session()
        self._is_authenticated = False
        self._current_proxy = None
        self._current_user_agent = None

        # Configurar sesión inicial
        self._setup_session()

    def _setup_session(self):
        """Configura la sesión con headers anti-detección."""
        # Rotar User-Agent
        self._current_user_agent = random.choice(self.USER_AGENTS)

        # Headers más realistas y variados
        self.session.headers.update(
            {
                "User-Agent": self._current_user_agent,
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

        # Configurar timeout y retries
        self.session.timeout = 30

        # Rotar proxy si está habilitado
        if self.use_proxies and self.PROXIES:
            self._rotate_proxy()

    def _rotate_proxy(self):
        """Rota el proxy actual."""
        if self.PROXIES:
            self._current_proxy = random.choice(self.PROXIES)
            self.session.proxies.update(self._current_proxy)
            logger.info(f"Usando proxy: {self._current_proxy}")

    def _rotate_user_agent(self):
        """Rota el User-Agent actual."""
        old_ua = self._current_user_agent
        self._current_user_agent = random.choice(self.USER_AGENTS)
        self.session.headers["User-Agent"] = self._current_user_agent
        logger.info(
            f"Rotando User-Agent: {old_ua[:50]}... -> {self._current_user_agent[:50]}..."
        )

    def _random_delay(self, min_seconds: float = 2.0, max_seconds: float = 5.0):
        """Aplica un delay aleatorio para simular comportamiento humano."""
        delay = random.uniform(min_seconds, max_seconds)
        logger.debug(f"Aplicando delay de {delay:.2f} segundos")
        time.sleep(delay)

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Realiza una petición HTTP con reintentos y rotación de headers.

        Args:
            method: Método HTTP (GET, POST, etc.)
            url: URL a solicitar
            **kwargs: Argumentos adicionales para requests

        Returns:
            Respuesta HTTP
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                # Rotar User-Agent cada pocos intentos
                if attempt > 0 and attempt % 2 == 0:
                    self._rotate_user_agent()

                # Rotar proxy si está habilitado
                if self.use_proxies and attempt > 0:
                    self._rotate_proxy()

                # Delay progresivo entre reintentos
                if attempt > 0:
                    delay = random.uniform(5, 15) * attempt
                    logger.info(
                        f"Esperando {delay:.1f} segundos antes del reintento {attempt + 1}"
                    )
                    time.sleep(delay)

                # Realizar petición
                response = self.session.request(method, url, **kwargs)

                # Verificar si fue bloqueado
                if response.status_code == 403:
                    logger.warning(
                        f"Error 403 en intento {attempt + 1}. Rotando configuración..."
                    )
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error("Todos los intentos fallaron con 403")
                        return response

                # Si llegamos aquí, la petición fue exitosa
                return response

            except requests.RequestException as e:
                logger.error(f"Error en petición (intento {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    continue
                else:
                    raise

        # Si llegamos aquí, todos los reintentos fallaron
        raise Exception("Todos los reintentos fallaron")

    def login(self) -> bool:
        """
        Realiza login con técnicas anti-detección.

        Returns:
            True si el login fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"Iniciando login avanzado para usuario: {self.username}")

            # Paso 1: Visitar página principal primero
            logger.info("Visitando página principal...")
            main_response = self._make_request("GET", self.BASE_URL)
            if main_response.status_code != 200:
                logger.error(
                    f"Error accediendo a página principal: {main_response.status_code}"
                )
                return False

            # Delay humano
            self._random_delay(3, 6)

            # Paso 2: Acceder a página de login
            logger.info("Accediendo a página de login...")
            login_page_response = self._make_request("GET", self.LOGIN_URL)

            if login_page_response.status_code != 200:
                logger.error(
                    f"Error accediendo a página de login: {login_page_response.status_code}"
                )
                return False

            # Parsear formulario de login
            soup = BeautifulSoup(login_page_response.text, "html.parser")
            login_form = soup.find("form")

            if not login_form:
                logger.error("No se encontró formulario de login")
                return False

            # Buscar campos de usuario y contraseña
            username_field = soup.find("input", {"name": "username"}) or soup.find(
                "input", {"name": "user"}
            )
            password_field = soup.find("input", {"name": "password"}) or soup.find(
                "input", {"type": "password"}
            )

            if not username_field or not password_field:
                logger.error("No se encontraron campos de usuario/contraseña")
                return False

            # Preparar datos del formulario
            form_data = {
                username_field["name"]: self.username,
                password_field["name"]: self.password,
            }

            # Buscar token CSRF
            csrf_token = self._get_csrf_token(login_page_response.text)
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

            # Delay antes del login
            self._random_delay(2, 4)

            # Enviar formulario de login
            logger.info("Enviando formulario de login...")
            login_response = self._make_request(
                "POST", login_url, data=form_data, allow_redirects=True
            )

            # Verificar si el login fue exitoso
            if self._is_login_successful(login_response):
                self._is_authenticated = True
                logger.info("Login exitoso con técnicas avanzadas")
                return True
            else:
                logger.error(
                    "Login fallido - credenciales incorrectas o error en el formulario"
                )
                return False

        except Exception as e:
            logger.error(f"Error durante login avanzado: {e}")
            return False

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

    def _is_login_successful(self, response: requests.Response) -> bool:
        """
        Verifica si el login fue exitoso basándose en la respuesta.
        """
        # Verificar código de estado
        if response.status_code not in [200, 302]:
            return False

        # Verificar URL de redirección
        if response.url and "login" not in response.url.lower():
            return True

        # Verificar contenido de la página
        page_content = response.text.lower()

        # Indicadores de éxito
        success_indicators = [
            "dashboard",
            "panel",
            "welcome",
            "bienvenido",
            "logout",
            "salir",
            "profile",
            "perfil",
        ]

        for indicator in success_indicators:
            if indicator in page_content:
                return True

        # Verificar que no hay mensajes de error
        error_indicators = [
            "invalid",
            "incorrect",
            "error",
            "failed",
            "invalid credentials",
            "credenciales incorrectas",
        ]

        for error in error_indicators:
            if error in page_content:
                return False

        return False

    def scrape_job_board(self, max_pages: int = 3) -> List[JobPostingData]:
        """
        Scrapea el tablero de ofertas de trabajo.

        Args:
            max_pages: Número máximo de páginas a scrapear

        Returns:
            Lista de ofertas de trabajo encontradas
        """
        if not self._is_authenticated:
            logger.error("No se puede scrapear sin estar autenticado")
            return []

        try:
            logger.info(
                f"Iniciando scraping avanzado del tablero (máx {max_pages} páginas)"
            )

            job_postings = []

            for page_num in range(max_pages):
                logger.info(f"Scrapeando página {page_num + 1}")

                # Navegar a la página del tablero
                if page_num == 0:
                    url = self.JOB_BOARD_URL
                else:
                    url = f"{self.JOB_BOARD_URL}?page={page_num + 1}"

                # Rotar User-Agent cada página
                if page_num > 0:
                    self._rotate_user_agent()

                response = self._make_request("GET", url)

                if response.status_code == 200:
                    # Extraer ofertas de la página
                    page_jobs = self._extract_jobs_from_page(response.text)
                    job_postings.extend(page_jobs)
                    logger.info(
                        f"Encontradas {len(page_jobs)} ofertas en página {page_num + 1}"
                    )
                else:
                    logger.error(
                        f"Error accediendo a página {page_num + 1}: {response.status_code}"
                    )

                # Pausa entre páginas
                if page_num < max_pages - 1:
                    self._random_delay(5, 10)

            logger.info(
                f"Scraping avanzado completado: {len(job_postings)} ofertas encontradas"
            )
            return job_postings

        except Exception as e:
            logger.error(f"Error durante scraping avanzado: {e}")
            return []

    def _extract_jobs_from_page(self, html_content: str) -> List[JobPostingData]:
        """Extrae ofertas de trabajo del HTML de la página."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            job_postings = []

            # Buscar elementos de ofertas (ajustar selectores según el sitio)
            job_elements = soup.find_all(
                ["div", "article", "section"],
                class_=re.compile(r"job|offer|posting", re.I),
            )

            for index, element in enumerate(job_elements):
                try:
                    # Extraer información de la oferta
                    title_elem = element.find(
                        ["h1", "h2", "h3", "h4"], class_=re.compile(r"title", re.I)
                    )
                    title = title_elem.get_text(strip=True) if title_elem else ""

                    company_elem = element.find(
                        ["span", "div"], class_=re.compile(r"company", re.I)
                    )
                    company = company_elem.get_text(strip=True) if company_elem else ""

                    location_elem = element.find(
                        ["span", "div"], class_=re.compile(r"location", re.I)
                    )
                    location = (
                        location_elem.get_text(strip=True) if location_elem else ""
                    )

                    description_elem = element.find(
                        ["div", "p"], class_=re.compile(r"description", re.I)
                    )
                    description = (
                        description_elem.get_text(strip=True)
                        if description_elem
                        else ""
                    )

                    link_elem = element.find("a")
                    url = (
                        link_elem["href"] if link_elem and link_elem.get("href") else ""
                    )

                    if title:  # Solo agregar si tiene título
                        job_posting = JobPostingData(
                            external_id=f"dvc_advanced_{int(time.time())}_{index}",
                            title=title,
                            company=company,
                            location=location,
                            description=description,
                            url=urljoin(self.BASE_URL, url) if url else "",
                            posted_at=datetime.now(),
                            raw_html=str(element),
                        )
                        job_postings.append(job_posting)

                except Exception as e:
                    logger.error(f"Error procesando oferta {index}: {e}")
                    continue

            return job_postings

        except Exception as e:
            logger.error(f"Error extrayendo ofertas de la página: {e}")
            return []

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if hasattr(self, "session"):
            self.session.close()
