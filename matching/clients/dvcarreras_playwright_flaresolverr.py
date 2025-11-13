"""
Cliente Playwright que usa FlareSolverr para bypasear Cloudflare.
Combina la potencia de Playwright con la capacidad de FlareSolverr para resolver Cloudflare.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import async_playwright

from ..services.flaresolverr_client import (get_flaresolverr_client)

logger = logging.getLogger(__name__)


class DVCarrerasPlaywrightFlareSolverr:
    """Cliente Playwright que usa FlareSolverr para bypasear Cloudflare."""

    BASE_URL = "https://dvcarreras.davinci.edu.ar"
    LOGIN_URL = "https://dvcarreras.davinci.edu.ar/login.html"
    JOB_BOARD_URL = "https://dvcarreras.davinci.edu.ar/job_board-0.html"

    def __init__(
        self,
        username: str,
        password: str,
        headless: bool = True,
        log_callback=None,
        session_dir: str = None,
    ):
        """
        Inicializa el cliente.

        Args:
            username: Usuario para login
            password: Contraseña para login
            headless: Si ejecutar el navegador en modo headless
            log_callback: Callback para logs
            session_dir: Directorio para guardar sesiones
        """
        self.username = username
        self.password = password
        self.headless = headless
        self.log_callback = log_callback
        self.browser = None
        self.context = None
        self.page = None
        self._is_authenticated = False
        self.flaresolverr = get_flaresolverr_client()

        # Configuración de sesiones
        self.session_dir = session_dir or "media/sessions"
        self.session_file = Path(self.session_dir) / f"dv_session_{username}.json"
        self.cookies_file = Path(self.session_dir) / f"dv_cookies_{username}.json"

        # Crear directorio de sesiones si no existe
        Path(self.session_dir).mkdir(parents=True, exist_ok=True)

    async def _log(self, message: str, log_type: str = "info"):
        """Envía un log a través del callback si está disponible."""
        if self.log_callback:
            try:
                await self.log_callback(message, log_type)
            except Exception as e:
                logger.error(f"Error enviando log: {e}")
        logger.info(f"[DVCarrerasFlareSolverr] {message}")

    async def save_session(self):
        """Guarda la sesión actual (cookies y estado) para reutilización futura."""
        try:
            if not self.context or not self.page:
                await self._log("No hay sesión activa para guardar", "warning")
                return False

            # Obtener cookies del contexto
            cookies = await self.context.cookies()

            # Crear objeto de sesión
            session_data = {
                "username": self.username,
                "saved_at": datetime.now().isoformat(),
                "is_authenticated": self._is_authenticated,
                "cookies": cookies,
                "user_agent": await self.page.evaluate("navigator.userAgent"),
            }

            # Guardar sesión
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)

            # Guardar cookies por separado para FlareSolverr
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)

            await self._log(f"Sesión guardada en {self.session_file}", "success")
            return True

        except Exception as e:
            await self._log(f"Error guardando sesión: {e}", "error")
            return False

    async def load_session(self) -> bool:
        """Carga una sesión guardada previamente."""
        try:
            if not self.session_file.exists():
                await self._log("No hay sesión guardada para cargar", "info")
                return False

            # Verificar si la sesión no es muy antigua (máximo 7 días)
            session_age = datetime.now() - datetime.fromtimestamp(
                self.session_file.stat().st_mtime
            )
            if session_age.days > 7:
                await self._log(
                    "Sesión guardada es muy antigua, se requiere nuevo login", "warning"
                )
                return False

            # Cargar datos de sesión
            with open(self.session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # Verificar que sea para el mismo usuario
            if session_data.get("username") != self.username:
                await self._log("Sesión guardada es para otro usuario", "warning")
                return False

            # Cargar cookies en el contexto
            cookies = session_data.get("cookies", [])
            if cookies and self.context:
                await self.context.add_cookies(cookies)
                await self._log(
                    f"Cargadas {len(cookies)} cookies de sesión guardada", "success"
                )

                # Marcar como autenticado si la sesión lo indica
                if session_data.get("is_authenticated", False):
                    self._is_authenticated = True
                    await self._log("Sesión restaurada exitosamente", "success")
                    return True

            return False

        except Exception as e:
            await self._log(f"Error cargando sesión: {e}", "error")
            return False

    async def test_session_validity(self) -> bool:
        """Verifica si la sesión cargada sigue siendo válida."""
        try:
            if not self.page:
                return False

            # Intentar acceder a una página que requiere autenticación
            await self.page.goto(
                self.JOB_BOARD_URL, wait_until="domcontentloaded", timeout=15000
            )
            await asyncio.sleep(2)  # Dar tiempo para que cargue completamente

            # Verificar si estamos en la página de login (sesión expirada)
            current_url = self.page.url
            page_content = await self.page.content()

            await self._log(f"URL de validación: {current_url}", "info")

            # Si estamos en login, la sesión expiró
            if "login" in current_url.lower():
                await self._log("Sesión expirada - redirigido a login", "warning")
                self._is_authenticated = False
                return False

            # Verificar si hay indicadores de Cloudflare (sesión puede seguir siendo válida)
            if (
                "Just a moment" in page_content
                or "cloudflare" in page_content.lower()
                or "Un momento" in page_content
            ):
                await self._log(
                    "Cloudflare detectado en validación - usando FlareSolverr", "info"
                )

                # Usar FlareSolverr para resolver la página
                solved_result = self.flaresolverr.solve_page(self.JOB_BOARD_URL)
                if solved_result and solved_result.get("status") == "ok":
                    html_content = solved_result.get("solution", {}).get("response", "")
                    await self.page.set_content(html_content)
                    await asyncio.sleep(1)
                    page_content = await self.page.content()

            # Verificar indicadores de autenticación exitosa
            success_indicators = [
                "logout",
                "salir",
                "perfil",
                "profile",
                "ofertas",
                "jobs",
                "tablero",
            ]
            if any(
                indicator in page_content.lower() for indicator in success_indicators
            ):
                await self._log("Sesión válida confirmada", "success")
                self._is_authenticated = True
                return True

            # Si no hay indicadores claros pero tampoco estamos en login, asumir válida
            if (
                "dvcarreras.davinci.edu.ar" in current_url
                and "login" not in current_url.lower()
            ):
                await self._log(
                    "Sesión probablemente válida - no en página de login", "success"
                )
                self._is_authenticated = True
                return True

            await self._log("No se pudo confirmar validez de sesión", "warning")
            return False

        except Exception as e:
            await self._log(f"Error verificando validez de sesión: {e}", "error")
            return False

    async def start(self):
        """Inicia el navegador Playwright."""
        try:
            await self._log("Iniciando navegador Playwright con FlareSolverr", "info")

            self.playwright = await async_playwright().start()

            # Usar Chromium con configuraciones anti-detección
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                ],
            )

            # Crear contexto
            self.context = await self.browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-AR",
                timezone_id="America/Argentina/Buenos_Aires",
            )

            # Crear página
            self.page = await self.context.new_page()

            # Inyectar scripts anti-detección
            await self.page.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """
            )

            await self._log("Navegador Playwright iniciado correctamente", "success")

        except Exception as e:
            await self._log(f"Error iniciando Playwright: {e}", "error")
            raise

    async def close(self):
        """Cierra el navegador."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, "playwright"):
                await self.playwright.stop()
            await self._log("Navegador Playwright cerrado", "info")
        except Exception as e:
            await self._log(f"Error cerrando Playwright: {e}", "error")

    async def test_login(self) -> bool:
        """
        Prueba el login usando FlareSolverr para bypasear Cloudflare.
        Primero intenta cargar una sesión existente, si no funciona hace login completo.

        Returns:
            True si el login es exitoso, False en caso contrario
        """
        try:
            await self._log(
                f"Probando login con FlareSolverr para usuario: {self.username}", "info"
            )

            # Paso 0: Intentar cargar sesión existente
            await self._log("Intentando cargar sesión existente...", "info")
            if await self.load_session():
                await self._log("Probando validez de sesión cargada...", "info")
                if await self.test_session_validity():
                    await self._log(
                        "Sesión válida encontrada, login exitoso", "success"
                    )

                    # Hacer scraping inmediatamente mientras tenemos la sesión activa
                    await self._log(
                        "Realizando scraping inmediato con sesión activa...", "info"
                    )
                    jobs = await self.scrape_job_board_immediate()
                    await self._log(
                        f"Scraping inmediato completado: {len(jobs)} ofertas encontradas",
                        "success",
                    )

                    return True
                else:
                    await self._log(
                        "Sesión cargada no es válida, procediendo con login completo",
                        "warning",
                    )
            else:
                await self._log(
                    "No hay sesión válida, procediendo con login completo", "info"
                )

            # Primero verificar que FlareSolverr esté funcionando
            if not self.flaresolverr.is_healthy():
                await self._log(
                    "FlareSolverr no está funcionando correctamente", "error"
                )
                return False

            await self._log(
                "FlareSolverr está funcionando, procediendo con login", "info"
            )

            # Paso 1: Obtener cookies iniciales con FlareSolverr
            await self._log("Obteniendo cookies iniciales con FlareSolverr...", "info")
            cookies_result = self.flaresolverr.get_cookies(self.LOGIN_URL)

            if not cookies_result or cookies_result.get("status") != "ok":
                await self._log("Error obteniendo cookies con FlareSolverr", "error")
                return False

            # Paso 2: Configurar cookies en Playwright
            cookies = cookies_result.get("solution", {}).get("cookies", [])
            if cookies:
                await self.context.add_cookies(cookies)
                await self._log(
                    f"Configuradas {len(cookies)} cookies en Playwright", "info"
                )

            # Paso 3: Navegar a la página de login con Playwright
            await self._log("Navegando a la página de login con Playwright...", "info")
            await self.page.goto(
                self.LOGIN_URL, wait_until="domcontentloaded", timeout=30000
            )
            await asyncio.sleep(3)

            # Verificar si hay Cloudflare
            page_content = await self.page.content()
            if (
                "Just a moment" in page_content
                or "cloudflare" in page_content.lower()
                or "Un momento" in page_content
            ):
                await self._log(
                    "Cloudflare detectado, usando FlareSolverr para resolver...",
                    "warning",
                )

                # Usar FlareSolverr para resolver la página completa
                solved_result = self.flaresolverr.solve_page(self.LOGIN_URL)

                if solved_result and solved_result.get("status") == "ok":
                    await self._log(
                        "Cloudflare resuelto exitosamente con FlareSolverr", "success"
                    )

                    # Obtener el HTML resuelto
                    solved_html = solved_result.get("solution", {}).get("response", "")
                    if solved_html:
                        # Navegar a una página en blanco y cargar el HTML resuelto
                        await self.page.goto("about:blank")
                        await self.page.set_content(solved_html)
                        await asyncio.sleep(2)
                else:
                    await self._log(
                        "Error resolviendo Cloudflare con FlareSolverr", "error"
                    )
                    return False

            # Paso 4: Buscar campos de login
            await self._log("Buscando campos de login...", "info")
            username_field = await self.page.query_selector(
                'input[name="user"], input[name="username"], input[type="text"]'
            )
            password_field = await self.page.query_selector('input[type="password"]')

            if not username_field or not password_field:
                await self._log(
                    "No se encontraron campos de usuario/contraseña", "error"
                )
                return False

            # Paso 5: Llenar campos y hacer login
            await self._log("Llenando campos de login...", "info")
            await username_field.fill(self.username)
            await asyncio.sleep(1)
            await password_field.fill(self.password)
            await asyncio.sleep(1)

            # Buscar botón de login
            login_button = await self.page.query_selector(
                'button:has-text("Acceder"), button[type="submit"], input[type="submit"]'
            )

            if login_button:
                await self._log("Haciendo clic en botón de login...", "info")
                await login_button.click()
            else:
                await self._log("Presionando Enter para enviar formulario...", "info")
                await self.page.keyboard.press("Enter")

            # Esperar navegación con manejo mejorado
            try:
                # Esperar un poco para que se procese el login
                await asyncio.sleep(2)

                # Intentar esperar por navegación, pero con timeout más corto
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)

                # Verificar si hay Cloudflare después del login
                page_content = await self.page.content()
                if (
                    "Just a moment" in page_content
                    or "cloudflare" in page_content.lower()
                    or "Un momento" in page_content
                ):
                    await self._log(
                        "Cloudflare detectado después del login, usando FlareSolverr para resolver...",
                        "warning",
                    )

                    # Usar FlareSolverr para resolver la página actual
                    current_url = self.page.url
                    solved_result = self.flaresolverr.solve_page(current_url)

                    if solved_result and solved_result.get("status") == "ok":
                        await self._log(
                            "Cloudflare post-login resuelto exitosamente", "success"
                        )

                        # Obtener el HTML resuelto y cargarlo
                        solved_html = solved_result.get("solution", {}).get(
                            "response", ""
                        )
                        if solved_html:
                            await self.page.goto("about:blank")
                            await self.page.set_content(solved_html)
                            await asyncio.sleep(2)
                    else:
                        await self._log(
                            "Error resolviendo Cloudflare post-login", "error"
                        )

                await asyncio.sleep(2)

            except Exception as nav_error:
                await self._log(
                    f"Timeout en navegación, continuando: {nav_error}", "warning"
                )
                await asyncio.sleep(2)

            # Verificar si el login fue exitoso
            current_url = self.page.url
            page_content = await self.page.content()

            await self._log(f"URL actual después del login: {current_url}", "info")

            if self._is_login_successful(current_url, page_content):
                self._is_authenticated = True
                await self._log("✅ Login exitoso con FlareSolverr", "success")

                # Guardar la sesión para futuras operaciones
                await self._log("Guardando sesión para futuras operaciones...", "info")
                await self.save_session()

                # Hacer scraping inmediatamente mientras tenemos la sesión activa
                await self._log(
                    "Realizando scraping inmediato con sesión activa...", "info"
                )
                jobs = await self.scrape_job_board_immediate()
                await self._log(
                    f"Scraping inmediato completado: {len(jobs)} ofertas encontradas",
                    "success",
                )

                return True
            else:
                await self._log("❌ Login fallido - credenciales incorrectas", "error")
                return False

        except Exception as e:
            await self._log(f"❌ Error durante login: {str(e)}", "error")
            return False

    def _is_login_successful(self, current_url: str, page_content: str) -> bool:
        """Verifica si el login fue exitoso."""
        page_content_lower = page_content.lower()

        # Verificar mensajes de error específicos
        error_indicators = [
            "usuario o contraseña incorrectos",
            "credenciales incorrectas",
            "login fallido",
            "error de autenticación",
            "invalid credentials",
            "wrong password",
            "incorrect username",
            "authentication failed",
        ]

        for error in error_indicators:
            if error in page_content_lower:
                logger.warning(f"Indicador de error encontrado: {error}")
                return False

        # Verificar si estamos en la página de login (indica fallo)
        if "login" in current_url.lower():
            logger.warning("Aún en página de login - credenciales incorrectas")
            return False

        # Verificar indicadores de éxito
        success_indicators = [
            "dashboard",
            "panel",
            "welcome",
            "bienvenido",
            "logout",
            "salir",
            "perfil",
            "profile",
            "menu",
            "navegación",
            "job_board",
            "oferta",
            "trabajo",
        ]

        for indicator in success_indicators:
            if indicator.lower() in page_content_lower:
                logger.info(f"Indicador de éxito encontrado: {indicator}")
                return True

        # Si no hay indicadores claros, verificar si la URL cambió
        if (
            "dvcarreras.davinci.edu.ar" in current_url
            and "login" not in current_url.lower()
        ):
            logger.info("URL cambió y no contiene 'login' - posible éxito")
            return True

        # Si no hay indicadores claros, asumir fallo
        logger.warning("No se encontraron indicadores claros de éxito o fallo")
        return False

    async def scrape_job_board_immediate(
        self, max_pages: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Scrapea el tablero de ofertas usando Playwright directamente (sin FlareSolverr).
        Se usa inmediatamente después del login exitoso.

        Args:
            max_pages: Número máximo de páginas a scrapear

        Returns:
            Lista de ofertas encontradas
        """
        if not self._is_authenticated or not self.page:
            logger.error(
                "No se puede scrapear sin estar autenticado o sin página activa"
            )
            return []

        try:
            await self._log("Navegando directamente al tablero de ofertas...", "info")

            # Navegar directamente al tablero de ofertas
            await self.page.goto(
                self.JOB_BOARD_URL, wait_until="domcontentloaded", timeout=30000
            )
            await asyncio.sleep(5)  # Esperar más tiempo para que cargue completamente

            # Verificar la URL actual
            current_url = self.page.url
            await self._log(f"URL actual después de navegar: {current_url}", "info")

            # Verificar si estamos en la página correcta
            if "login" in current_url.lower():
                await self._log(
                    "❌ Redirigido a página de login - sesión perdida", "error"
                )
                return []

            # Obtener el título de la página
            page_title = await self.page.title()
            await self._log(f"Título de la página: {page_title}", "info")

            # Obtener contenido de la página para debugging
            page_content = await self.page.content()
            await self._log(
                f"Contenido de la página: {len(page_content)} caracteres", "info"
            )

            # Verificar si hay un challenge de Cloudflare
            if (
                "turnstile" in page_content.lower()
                or "verificar que usted es un ser humano" in page_content.lower()
            ):
                await self._log(
                    "❌ Cloudflare Turnstile detectado - esperando resolución...",
                    "warning",
                )

                # Esperar más tiempo para que se resuelva automáticamente
                await self._log(
                    "Esperando 10 segundos para resolución automática...", "info"
                )
                await asyncio.sleep(10)

                # Verificar si la página cambió
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                page_content = await self.page.content()
                current_url = self.page.url
                page_title = await self.page.title()

                await self._log(
                    f"Después de esperar - URL: {current_url}, Título: {page_title}",
                    "info",
                )

                # Verificar si aún hay Turnstile
                if (
                    "turnstile" in page_content.lower()
                    or "verificar que usted es un ser humano" in page_content.lower()
                ):
                    await self._log(
                        "❌ Turnstile aún presente - no se pudo resolver automáticamente",
                        "error",
                    )
                    # Guardar el contenido para debugging
                    debug_filename = f"media/debug/scraper_html/turnstile_challenge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    os.makedirs(os.path.dirname(debug_filename), exist_ok=True)
                    with open(debug_filename, "w", encoding="utf-8") as f:
                        f.write(page_content)
                    await self._log(
                        f"Contenido del challenge guardado en: {debug_filename}", "info"
                    )
                    return []
                else:
                    await self._log("✅ Turnstile resuelto automáticamente", "success")

            # Verificar si hay contenido de ofertas
            if (
                "oferta" not in page_content.lower()
                and "trabajo" not in page_content.lower()
            ):
                await self._log(
                    "❌ No se encontró contenido de ofertas en la página", "warning"
                )
                # Guardar el contenido para debugging
                debug_filename = f"media/debug/scraper_html/immediate_scraping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                os.makedirs(os.path.dirname(debug_filename), exist_ok=True)
                with open(debug_filename, "w", encoding="utf-8") as f:
                    f.write(page_content)
                await self._log(f"Contenido guardado en: {debug_filename}", "info")

            # Extraer ofertas usando JavaScript
            jobs_data = await self.page.evaluate(
                """
                () => {
                    const jobs = [];
                    
                    // Debug: Verificar estructura de la página
                    console.log('URL actual:', window.location.href);
                    console.log('Título de la página:', document.title);
                    console.log('¿Existe tbody?', !!document.querySelector('tbody'));
                    console.log('¿Existe tabla?', !!document.querySelector('table'));
                    
                    // Buscar específicamente filas tr que contengan ofertas
                    const jobRows = document.querySelectorAll('tbody tr');
                    console.log('Total filas tr encontradas:', jobRows.length);
                    
                    // Debug adicional: verificar contenido de las filas
                    jobRows.forEach((row, index) => {
                        console.log(`Fila ${index}:`, row.textContent?.substring(0, 100));
                    });
                    
                    jobRows.forEach((row, index) => {
                        try {
                            // Buscar el primer td que contiene la información de la oferta
                            const firstTd = row.querySelector('td:first-child');
                            if (!firstTd) return;
                            
                            const rowText = firstTd.textContent?.trim() || '';
                            
                            // Buscar el título en strong
                            const titleElement = firstTd.querySelector('strong');
                            let title = titleElement?.textContent?.trim() || '';
                            
                            // Si no hay strong, usar las primeras palabras del texto
                            if (!title || title.length < 3) {
                                const words = rowText.split(' ').slice(0, 5);
                                title = words.join(' ');
                            }
                            
                            // Buscar los detalles en small (descripción completa)
                            const detailsElement = firstTd.querySelector('small');
                            const description = detailsElement?.textContent?.trim() || '';
                            
                            // Buscar enlaces de email protegido por Cloudflare
                            let emailHtml = '';
                            if (detailsElement) {
                                const emailLink = detailsElement.querySelector('a[href*="email-protection"]');
                                if (emailLink) {
                                    emailHtml = emailLink.outerHTML;
                                }
                            }
                            
                            // Buscar emails en el texto usando regex
                            const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                            const emailsInText = description.match(emailRegex);
                            let foundEmail = '';
                            if (emailsInText && emailsInText.length > 0) {
                                foundEmail = emailsInText[0];
                            }
                            
                            // Solo procesar si tiene título
                            if (title && title.length > 3) {
                                jobs.push({
                                    title: title,
                                    description: description,
                                    email_html: emailHtml,
                                    email_text: foundEmail,
                                    raw_html: firstTd.outerHTML.substring(0, 2000)
                                });
                            }
                        } catch (e) {
                            console.error('Error procesando fila:', e);
                        }
                    });
                    
                    console.log('Total ofertas encontradas:', jobs.length);
                    return jobs;
                }
            """
            )

            await self._log(
                f"Encontradas {len(jobs_data)} ofertas en el tablero", "success"
            )
            return jobs_data

        except Exception as e:
            await self._log(f"Error durante scraping inmediato: {e}", "error")
            return []

    async def scrape_job_board(self, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Scrapea el tablero de ofertas usando FlareSolverr si es necesario.

        Args:
            max_pages: Número máximo de páginas a scrapear

        Returns:
            Lista de ofertas encontradas
        """
        if not self._is_authenticated:
            logger.error("No se puede scrapear sin estar autenticado")
            return []

        try:
            await self._log("Iniciando scraping del tablero de ofertas", "info")

            # Obtener cookies actuales de Playwright para FlareSolverr
            current_cookies = await self.context.cookies() if self.context else []
            await self._log(
                f"Cookies disponibles para FlareSolverr: {len(current_cookies)}", "info"
            )

            # Debug: mostrar las cookies que se van a enviar
            for cookie in current_cookies:
                await self._log(
                    f"Cookie: {cookie.get('name')} = {cookie.get('value')[:20]}...",
                    "info",
                )

            # Usar FlareSolverr para resolver la página del tablero con cookies
            await self._log(
                f"Enviando petición a FlareSolverr para: {self.JOB_BOARD_URL}", "info"
            )
            solved_result = self.flaresolverr.solve_page(
                self.JOB_BOARD_URL, cookies=current_cookies
            )

            await self._log(f"Respuesta de FlareSolverr: {solved_result}", "info")

            if not solved_result or solved_result.get("status") != "ok":
                await self._log(
                    "Error resolviendo página del tablero con FlareSolverr", "error"
                )
                await self._log(f"Resultado completo: {solved_result}", "error")
                return []

            # Obtener el HTML resuelto
            solved_html = solved_result.get("solution", {}).get("response", "")
            if not solved_html:
                await self._log("No se obtuvo HTML resuelto del tablero", "error")
                return []

            # Debug: Verificar el HTML que llega de FlareSolverr
            await self._log(
                f"HTML recibido de FlareSolverr: {len(solved_html)} caracteres", "info"
            )
            if "EDITOR semi sr" in solved_html:
                await self._log("✅ HTML contiene ofertas esperadas", "success")
            else:
                await self._log("❌ HTML no contiene ofertas esperadas", "warning")
                await self._log(f"Primeros 500 caracteres: {solved_html[:500]}", "info")

                # Guardar HTML completo para debugging
                import os
                from datetime import datetime

                debug_dir = "media/debug/scraper_html"
                os.makedirs(debug_dir, exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html_file = f"{debug_dir}/flaresolverr_response_{timestamp}.html"

                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(solved_html)
                await self._log(f"HTML completo guardado en: {html_file}", "info")

            # Cargar el HTML resuelto en Playwright
            await self.page.goto("about:blank")
            await self.page.set_content(solved_html)
            await asyncio.sleep(2)

            # Extraer ofertas usando JavaScript
            jobs_data = await self.page.evaluate(
                """
                () => {
                    const jobs = [];
                    
                    // Debug: Verificar estructura de la página
                    console.log('URL actual:', window.location.href);
                    console.log('Título de la página:', document.title);
                    console.log('¿Existe tbody?', !!document.querySelector('tbody'));
                    console.log('¿Existe tabla?', !!document.querySelector('table'));
                    
                    // Buscar específicamente filas tr que contengan ofertas
                    const jobRows = document.querySelectorAll('tbody tr');
                    console.log('Total filas tr encontradas:', jobRows.length);
                    
                    // Debug adicional: verificar contenido de las filas
                    jobRows.forEach((row, index) => {
                        console.log(`Fila ${index}:`, row.textContent?.substring(0, 100));
                    });
                    
                    jobRows.forEach((row, index) => {
                        try {
                            // Buscar el primer td que contiene la información de la oferta
                            const firstTd = row.querySelector('td:first-child');
                            if (!firstTd) return;
                            
                            const rowText = firstTd.textContent?.trim() || '';
                            
                            // Buscar el título en strong
                            const titleElement = firstTd.querySelector('strong');
                            let title = titleElement?.textContent?.trim() || '';
                            
                            // Si no hay strong, usar las primeras palabras del texto
                            if (!title || title.length < 3) {
                                const words = rowText.split(' ').slice(0, 5);
                                title = words.join(' ');
                            }
                            
                            // Buscar los detalles en small (descripción completa)
                            const detailsElement = firstTd.querySelector('small');
                            const description = detailsElement?.textContent?.trim() || '';
                            
                            // Buscar enlaces de email protegido por Cloudflare
                            let emailHtml = '';
                            if (detailsElement) {
                                const emailLink = detailsElement.querySelector('a[href*="email-protection"]');
                                if (emailLink) {
                                    emailHtml = emailLink.outerHTML;
                                }
                            }
                            
                            // Buscar emails en el texto usando regex
                            const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}/g;
                            const emailsInText = description.match(emailRegex);
                            let foundEmail = '';
                            if (emailsInText && emailsInText.length > 0) {
                                foundEmail = emailsInText[0];
                            }
                            
                            // Solo procesar si tiene título
                            if (title && title.length > 3) {
                                jobs.push({
                                    title: title,
                                    description: description,
                                    email_html: emailHtml,
                                    email_text: foundEmail,
                                    raw_html: firstTd.outerHTML.substring(0, 2000)
                                });
                            }
                        } catch (e) {
                            console.error('Error procesando fila:', e);
                        }
                    });
                    
                    console.log('Total ofertas encontradas:', jobs.length);
                    return jobs;
                }
            """
            )

            await self._log(
                f"Encontradas {len(jobs_data)} ofertas en el tablero", "success"
            )
            return jobs_data

        except Exception as e:
            await self._log(f"Error durante scraping: {e}", "error")
            return []

    def test_login_sync(self) -> bool:
        """
        Versión síncrona del test de login para usar en Celery.

        Returns:
            True si el login es exitoso, False en caso contrario
        """
        try:
            logger.info(
                f"Probando login síncrono con FlareSolverr para usuario: {self.username}"
            )

            # Ejecutar el login de forma asíncrona
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                result = loop.run_until_complete(self._test_login_async())
                return result
            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error durante prueba de login síncrono: {e}")
            return False

    async def _test_login_async(self) -> bool:
        """Versión asíncrona de la prueba de login."""
        try:
            # Iniciar navegador
            await self.start()

            # Realizar login
            login_success = await self.test_login()

            if login_success:
                await self._log(
                    "✅ Conexión a INTRANET DAVINCI verificada correctamente", "success"
                )
                return True
            else:
                await self._log(
                    "❌ Error de autenticación en INTRANET DAVINCI. Verifica usuario y contraseña.",
                    "error",
                )
                return False

        except Exception as e:
            await self._log(f"❌ Error de conexión: {str(e)}", "error")
            return False
        finally:
            # Cerrar navegador
            await self.close()
