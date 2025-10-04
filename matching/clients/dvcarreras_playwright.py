"""
Cliente para scraping con Playwright (navegador real) para dvcarreras.davinci.edu.ar
Usa un navegador real para evitar detección anti-bot.
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from playwright.async_api import (async_playwright)

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


class DVCarrerasPlaywrightClient:
    """Cliente para scraping con Playwright (navegador real)"""

    BASE_URL = "https://dvcarreras.davinci.edu.ar"
    LOGIN_URL = "https://dvcarreras.davinci.edu.ar/login.html"
    JOB_BOARD_URL = "https://dvcarreras.davinci.edu.ar/job_board-0.html"

    def __init__(self, username: str, password: str, headless: bool = True):
        """
        Inicializa el cliente con credenciales.

        Args:
            username: Usuario para login
            password: Contraseña para login
            headless: Si ejecutar el navegador en modo headless
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.browser = None
        self.context = None
        self.page = None
        self._is_authenticated = False

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def start(self):
        """Inicia el navegador y crea el contexto."""
        try:
            self.playwright = await async_playwright().start()

            # Usar Chromium con configuraciones para evitar detección
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ],
            )

            # Crear contexto con configuraciones anti-detección
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-AR",
                timezone_id="America/Argentina/Buenos_Aires",
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
            )

            # Crear página
            self.page = await self.context.new_page()

            # Inyectar scripts para evitar detección
            await self.page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['es-AR', 'es', 'en'],
                });
            """
            )

            logger.info("Navegador Playwright iniciado correctamente")

        except Exception as e:
            logger.error(f"Error iniciando Playwright: {e}")
            raise

    async def close(self):
        """Cierra el navegador y libera recursos."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, "playwright"):
                await self.playwright.stop()
            logger.info("Navegador Playwright cerrado")
        except Exception as e:
            logger.error(f"Error cerrando Playwright: {e}")

    async def login(self) -> bool:
        """
        Realiza login en dvcarreras usando navegador real.

        Returns:
            True si el login fue exitoso, False en caso contrario
        """
        try:
            logger.info(f"Iniciando login con Playwright para usuario: {self.username}")

            # Navegar a la página de login
            await self.page.goto(self.LOGIN_URL, wait_until="networkidle")
            await self._random_delay(2, 4)

            # Buscar campos de login
            username_field = await self.page.query_selector(
                'input[name="username"], input[name="user"], input[type="text"]'
            )
            password_field = await self.page.query_selector(
                'input[name="password"], input[type="password"]'
            )

            if not username_field or not password_field:
                logger.error("No se encontraron campos de usuario/contraseña")
                return False

            # Llenar campos con comportamiento humano
            await username_field.click()
            await self._random_delay(0.5, 1.0)
            await username_field.fill(self.username)
            await self._random_delay(0.5, 1.0)

            await password_field.click()
            await self._random_delay(0.5, 1.0)
            await password_field.fill(self.password)
            await self._random_delay(1, 2)

            # Buscar y hacer clic en el botón de login
            login_button = await self.page.query_selector(
                'button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Entrar")'
            )

            if login_button:
                await login_button.click()
            else:
                # Si no hay botón, presionar Enter
                await self.page.keyboard.press("Enter")

            # Esperar navegación
            await self.page.wait_for_load_state("networkidle")
            await self._random_delay(2, 4)

            # Verificar si el login fue exitoso
            current_url = self.page.url
            page_content = await self.page.content()

            # Verificar indicadores de login exitoso
            if self._is_login_successful(current_url, page_content):
                self._is_authenticated = True
                logger.info("Login exitoso con Playwright")
                return True
            else:
                logger.error(
                    "Login fallido - credenciales incorrectas o error en el formulario"
                )
                return False

        except Exception as e:
            logger.error(f"Error durante login con Playwright: {e}")
            return False

    def _is_login_successful(self, current_url: str, page_content: str) -> bool:
        """
        Verifica si el login fue exitoso basándose en la URL y contenido.
        """
        # Verificar URL - si no estamos en login, probablemente fue exitoso
        if "login" not in current_url.lower():
            return True

        # Verificar contenido de la página
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
            if indicator.lower() in page_content.lower():
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
            if error.lower() in page_content.lower():
                return False

        return False

    async def scrape_job_board(self, max_pages: int = 3) -> List[JobPostingData]:
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
                f"Iniciando scraping del tablero de ofertas (máx {max_pages} páginas)"
            )

            job_postings = []

            for page_num in range(max_pages):
                logger.info(f"Scrapeando página {page_num + 1}")

                # Navegar a la página del tablero
                if page_num == 0:
                    url = self.JOB_BOARD_URL
                else:
                    url = f"{self.JOB_BOARD_URL}?page={page_num + 1}"

                await self.page.goto(url, wait_until="networkidle")
                await self._random_delay(2, 4)

                # Extraer ofertas de la página actual
                page_jobs = await self._extract_jobs_from_page()
                job_postings.extend(page_jobs)

                logger.info(
                    f"Encontradas {len(page_jobs)} ofertas en página {page_num + 1}"
                )

                # Pausa entre páginas
                if page_num < max_pages - 1:
                    await self._random_delay(3, 6)

            logger.info(f"Scraping completado: {len(job_postings)} ofertas encontradas")
            return job_postings

        except Exception as e:
            logger.error(f"Error durante scraping: {e}")
            return []

    async def _extract_jobs_from_page(self) -> List[JobPostingData]:
        """Extrae ofertas de trabajo de la página actual."""
        try:
            # Esperar a que se carguen las ofertas
            await self.page.wait_for_selector(
                '.job-posting, .job-card, .offer, [class*="job"]', timeout=10000
            )

            # Extraer ofertas usando JavaScript
            jobs_data = await self.page.evaluate(
                """
                () => {
                    const jobs = [];
                    
                    // Buscar elementos de ofertas (ajustar selectores según el sitio)
                    const jobElements = document.querySelectorAll('.job-posting, .job-card, .offer, [class*="job"]');
                    
                    jobElements.forEach((element, index) => {
                        try {
                            const title = element.querySelector('h3, h4, .title, [class*="title"]')?.textContent?.trim() || '';
                            const company = element.querySelector('.company, [class*="company"]')?.textContent?.trim() || '';
                            const location = element.querySelector('.location, [class*="location"]')?.textContent?.trim() || '';
                            const description = element.querySelector('.description, [class*="description"]')?.textContent?.trim() || '';
                            const link = element.querySelector('a')?.href || '';
                            
                            if (title) {
                                jobs.push({
                                    external_id: `dvc_${Date.now()}_${index}`,
                                    title: title,
                                    company: company,
                                    location: location,
                                    description: description,
                                    url: link,
                                    raw_html: element.outerHTML
                                });
                            }
                        } catch (e) {
                            console.error('Error procesando oferta:', e);
                        }
                    });
                    
                    return jobs;
                }
            """
            )

            # Convertir a objetos JobPostingData
            job_postings = []
            for job_data in jobs_data:
                job_posting = JobPostingData(
                    external_id=job_data["external_id"],
                    title=job_data["title"],
                    company=job_data["company"],
                    location=job_data["location"],
                    description=job_data["description"],
                    url=job_data["url"],
                    posted_at=datetime.now(),
                    raw_html=job_data["raw_html"],
                )
                job_postings.append(job_posting)

            return job_postings

        except Exception as e:
            logger.error(f"Error extrayendo ofertas de la página: {e}")
            return []

    async def _random_delay(self, min_seconds: float, max_seconds: float):
        """Aplica un delay aleatorio para simular comportamiento humano."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)
