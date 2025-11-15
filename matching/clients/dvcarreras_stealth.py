"""
Cliente stealth para DV Carreras usando undetected-chromedriver.
Este cliente está diseñado para bypasear Cloudflare Turnstile usando técnicas anti-detección.
"""

import asyncio
import json
import logging
import os
import random
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import undetected_chromedriver as uc
from asgiref.sync import sync_to_async
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from matching.models import ScrapingLog, UserProfile

logger = logging.getLogger(__name__)


class DVCarrerasStealth:
    """
    Cliente stealth para DV Carreras usando undetected-chromedriver.

    Características:
    - Bypasea Cloudflare Turnstile
    - Simula comportamiento humano
    - Gestión de sesiones
    - Anti-detección avanzada
    """

    BASE_URL = "https://dvcarreras.davinci.edu.ar"
    LOGIN_URL = f"{BASE_URL}/login.html"
    JOB_BOARD_URL = f"{BASE_URL}/job_board-0.html"

    def __init__(
        self, user_id: int, headless: bool = True, task_id: Optional[str] = None
    ):
        """
        Inicializa el cliente stealth.

        Args:
            user_id: ID del usuario
            headless: Si ejecutar en modo headless
            task_id: ID de la tarea de Celery (opcional)
        """
        self.user_id = user_id
        self.task_id = task_id or "stealth_scraper"  # Fallback al ID genérico
        self.headless = headless
        self.driver: Optional[uc.Chrome] = None
        self._is_authenticated = False
        self.profile = None
        self.session_file = f"media/sessions/user_{user_id}_stealth_session.json"

        # Configuración anti-detección
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        # El perfil se cargará cuando sea necesario

    async def _load_profile(self):
        """Carga el perfil del usuario."""
        try:
            self.profile = await sync_to_async(UserProfile.objects.get)(
                user_id=self.user_id
            )
            logger.info(
                f"[DVCarrerasStealth] Perfil cargado para usuario {self.user_id}"
            )
        except UserProfile.DoesNotExist:
            logger.error(
                f"[DVCarrerasStealth] No se encontró perfil para usuario {self.user_id}"
            )
            raise ValueError(f"Usuario {self.user_id} no tiene perfil configurado")

    async def _log(self, message: str, level: str = "info"):
        """Registra un mensaje en logs y base de datos."""
        timestamp = datetime.now()
        log_message = f"[DVCarrerasStealth] {message}"

        if level == "error":
            logger.error(log_message)
        elif level == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Guardar en base de datos con reintentos
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Forzar cierre de conexiones antiguas antes del primer intento
                if attempt == 0:
                    from django.db import connection

                    await sync_to_async(connection.close_if_unusable_or_obsolete)()

                await sync_to_async(ScrapingLog.objects.create)(
                    user_id=self.user_id,
                    message=message,
                    log_type=level,
                    task_id=self.task_id,
                )
                break  # Éxito, salir del loop
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Intento {attempt + 1}/{max_retries} fallido guardando log en BD: {e}"
                    )
                    await asyncio.sleep(0.1)  # Pequeño delay antes de reintentar
                else:
                    logger.error(
                        f"Error guardando log en BD después de {max_retries} intentos: {e}"
                    )

    async def _clear_previous_screenshots(self):
        """Limpiar screenshots anteriores del usuario"""
        try:
            await self._log("🧹 Limpiando screenshots anteriores...", "info")

            screenshots_dir = Path("media/screenshots")
            if not screenshots_dir.exists():
                await self._log(
                    "📁 No hay directorio de screenshots para limpiar", "info"
                )
                return

            # Buscar screenshots del usuario actual
            pattern = f"user_{self.user_id}_*.png"
            screenshots = list(screenshots_dir.glob(pattern))

            if screenshots:
                deleted_count = 0
                for screenshot in screenshots:
                    try:
                        screenshot.unlink()
                        deleted_count += 1
                    except Exception as e:
                        await self._log(
                            f"⚠️ No se pudo eliminar {screenshot.name}: {e}", "warning"
                        )

                await self._log(
                    f"✅ Eliminados {deleted_count} screenshots anteriores", "success"
                )
            else:
                await self._log("ℹ️ No hay screenshots anteriores para limpiar", "info")

        except Exception as e:
            await self._log(f"❌ Error limpiando screenshots: {e}", "error")

    async def _capture_screenshot(self, step_name: str = None):
        """Capturar screenshot del navegador actual"""
        try:
            await self._log(
                f"🔍 Intentando capturar screenshot: {step_name or 'proceso'}", "info"
            )

            if not self.driver:
                await self._log("❌ No hay driver disponible para screenshot", "error")
                return None

            # Crear directorio de screenshots si no existe
            screenshots_dir = Path("media/screenshots")
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            await self._log(f"📁 Directorio de screenshots: {screenshots_dir}", "info")

            # Generar nombre del archivo
            timestamp = int(time.time())
            step_suffix = f"_{step_name}" if step_name else ""
            filename = (
                f"user_{self.user_id}_{self.task_id}{step_suffix}_{timestamp}.png"
            )
            screenshot_path = screenshots_dir / filename

            await self._log(f"📸 Capturando screenshot: {filename}", "info")

            # Capturar screenshot
            self.driver.save_screenshot(str(screenshot_path))

            # Verificar que se creó el archivo
            if screenshot_path.exists():
                # Comprimir screenshot para reducir tamaño (objetivo: 60-80% de reducción)
                try:
                    from PIL import Image

                    # Obtener tamaño original
                    original_size = screenshot_path.stat().st_size

                    # Abrir imagen
                    img = Image.open(screenshot_path)

                    # Convertir RGBA a RGB si tiene transparencia (JPEG no soporta alpha)
                    if img.mode in ("RGBA", "LA", "P"):
                        # Crear fondo blanco para transparencias
                        background = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        background.paste(
                            img, mask=img.split()[-1] if img.mode == "RGBA" else None
                        )
                        img = background
                        await self._log(
                            "🔄 Convertido RGBA→RGB para mejor compresión", "info"
                        )

                    # Redimensionar si es muy grande
                    # Límites: max 1600px de ancho o 2000px de alto (más agresivo)
                    max_width = 1600
                    max_height = 2000
                    needs_resize = False
                    new_width, new_height = img.width, img.height

                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_width = max_width
                        new_height = int(img.height * ratio)
                        needs_resize = True

                    if new_height > max_height:
                        ratio = max_height / new_height
                        new_height = max_height
                        new_width = int(new_width * ratio)
                        needs_resize = True

                    if needs_resize:
                        img = img.resize(
                            (new_width, new_height), Image.Resampling.LANCZOS
                        )
                        await self._log(
                            f"📐 Screenshot redimensionado: {img.width}x{img.height}",
                            "info",
                        )

                    # Estrategia de compresión según tamaño original
                    # Para screenshots, JPEG siempre comprime mejor que PNG
                    # Usamos diferentes calidades según el tamaño para maximizar reducción
                    
                    if original_size < 100 * 1024:  # < 100KB: JPEG calidad 75 (más agresivo)
                        quality = 75
                        strategy = "JPEG calidad 75 (imagen pequeña)"
                    elif original_size < 500 * 1024:  # 100-500KB: JPEG calidad 80
                        quality = 80
                        strategy = "JPEG calidad 80 (imagen mediana)"
                    else:  # > 500KB: JPEG calidad 85
                        quality = 85
                        strategy = "JPEG calidad 85 (imagen grande)"
                    
                    # Convertir a JPEG (siempre mejor que PNG para screenshots)
                    jpeg_path = screenshot_path.with_suffix(".jpg")
                    img.save(
                        jpeg_path,
                        "JPEG",
                        quality=quality,
                        optimize=True,
                        progressive=True,
                    )
                    
                    # Obtener tamaño comprimido
                    compressed_size = jpeg_path.stat().st_size
                    
                    # Si el JPEG es más grande que el original, intentar con calidad más baja
                    if compressed_size >= original_size and original_size < 500 * 1024:
                        await self._log(
                            f"⚠️ JPEG inicial más grande, probando calidad más baja...",
                            "info",
                        )
                        # Intentar con calidad 70
                        img.save(
                            jpeg_path,
                            "JPEG",
                            quality=70,
                            optimize=True,
                            progressive=True,
                        )
                        compressed_size = jpeg_path.stat().st_size
                        strategy = "JPEG calidad 70 (optimizado)"
                    
                    # Si aún es más grande, mantener el original PNG
                    if compressed_size >= original_size:
                        await self._log(
                            f"⚠️ JPEG no mejora el tamaño, manteniendo PNG original",
                            "warning",
                        )
                        jpeg_path.unlink()  # Eliminar JPEG
                        compressed_size = original_size
                        reduction_percent = 0
                    else:
                        # Reemplazar PNG con JPEG
                        screenshot_path.unlink()
                        screenshot_path = jpeg_path
                        reduction_percent = (
                            (1 - compressed_size / original_size) * 100
                            if original_size > 0
                            else 0
                        )
                        await self._log(
                            f"🖼️ {strategy}", "info"
                        )

                    await self._log(
                        f"🗜️ Screenshot comprimido: {original_size / 1024:.1f}KB → {compressed_size / 1024:.1f}KB ({reduction_percent:.1f}% reducción)",
                        "success",
                    )
                except ImportError:
                    await self._log(
                        "⚠️ Pillow no disponible, screenshot guardado sin compresión",
                        "warning",
                    )
                except Exception as e:
                    await self._log(f"⚠️ Error comprimiendo screenshot: {e}", "warning")
                    # Continuar aunque falle la compresión

                await self._log(
                    f"✅ Screenshot guardado exitosamente: {screenshot_path}", "success"
                )
                return str(screenshot_path)
            else:
                await self._log(
                    f"❌ Screenshot no se guardó: {screenshot_path}", "error"
                )
                return None

        except Exception as e:
            await self._log(f"❌ Error capturando screenshot: {e}", "error")
            import traceback

            await self._log(f"❌ Traceback: {traceback.format_exc()}", "error")
            return None

    def _get_stealth_options(self) -> uc.ChromeOptions:
        """
        Configura opciones stealth para undetected-chromedriver.

        Returns:
            ChromeOptions configurado para anti-detección
        """
        options = uc.ChromeOptions()

        # Configuración básica stealth
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")

        # Anti-detección avanzada
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-images")  # Para velocidad

        # User-Agent aleatorio
        user_agent = random.choice(self.user_agents)
        options.add_argument(f"--user-agent={user_agent}")

        # Configuración de ventana
        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")

        # Configuración de red
        options.add_argument("--disable-background-networking")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-backgrounding-occluded-windows")

        # Configuración de privacidad
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")

        return options

    def _get_chrome_version(self) -> Optional[int]:
        """
        Detecta la versión de Chrome instalada en el sistema.

        Returns:
            Versión mayor de Chrome (ej: 141) o None si no se puede detectar
        """
        try:
            result = subprocess.run(
                ["google-chrome", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Output esperado: "Google Chrome 141.0.7390.107"
            match = re.search(r"Chrome (\d+)", result.stdout)
            if match:
                version = int(match.group(1))
                logger.info(f"🔍 Chrome version detectada: {version}")
                return version
        except subprocess.TimeoutExpired:
            logger.warning("⚠️ Timeout detectando versión de Chrome")
        except FileNotFoundError:
            logger.warning("⚠️ google-chrome no encontrado en PATH")
        except Exception as e:
            logger.warning(f"⚠️ Error detectando versión de Chrome: {e}")

        return None  # Fallback a auto-detección de undetected-chromedriver

    async def start(self) -> bool:
        """
        Inicia el navegador stealth.

        Returns:
            True si se inició correctamente
        """
        try:
            await self._log("Iniciando navegador stealth...", "info")

            # Limpiar screenshots anteriores al inicio
            await self._clear_previous_screenshots()

            # Configurar opciones
            options = self._get_stealth_options()

            # Detectar versión de Chrome instalada
            chrome_version = self._get_chrome_version()

            if chrome_version:
                await self._log(f"🎯 Usando Chrome version {chrome_version}", "info")
            else:
                await self._log("⚠️ Auto-detectando versión de Chrome...", "warning")

            # Inicializar undetected-chromedriver con versión detectada
            self.driver = uc.Chrome(
                options=options,
                version_main=chrome_version,  # Usa versión detectada (o None para auto-detectar)
                driver_executable_path=None,  # Auto-detecta
            )

            # Configuraciones adicionales anti-detección
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})"
            )
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})"
            )

            await self._log("Navegador stealth iniciado correctamente", "success")
            # Removido screenshot de navegador_iniciado
            await self._capture_screenshot("pantalla_inicial")
            return True

        except Exception as e:
            await self._log(f"Error iniciando navegador stealth: {e}", "error")
            return False

    async def close(self):
        """Cierra el navegador."""
        if self.driver:
            try:
                self.driver.quit()
                await self._log("Navegador stealth cerrado", "info")
            except Exception as e:
                await self._log(f"Error cerrando navegador: {e}", "warning")
            finally:
                self.driver = None
                self._is_authenticated = False

    async def _get_credentials(self) -> tuple[str, str]:
        """
        Obtiene las credenciales del usuario.

        Returns:
            Tupla (username, password)
        """
        try:
            # Cargar perfil si no está cargado
            if not self.profile:
                await self._load_profile()

            # Intentar desencriptar
            if hasattr(self.profile, "dv_username") and hasattr(
                self.profile, "dv_password"
            ):
                username = self.profile.dv_username
                password = self.profile.dv_password

                # Si están encriptados, desencriptar
                try:
                    from cryptography.fernet import Fernet
                    from django.conf import settings

                    if hasattr(settings, "ENCRYPTION_KEY") and settings.ENCRYPTION_KEY:
                        fernet = Fernet(settings.ENCRYPTION_KEY.encode())
                        username = fernet.decrypt(username.encode()).decode()
                        password = fernet.decrypt(password.encode()).decode()
                except Exception:
                    # Si falla la desencriptación, usar como texto plano
                    pass

                return username, password
            else:
                raise ValueError("Credenciales no configuradas")

        except Exception as e:
            await self._log(f"Error obteniendo credenciales: {e}", "error")
            raise

    async def _handle_survey_popup(self):
        """
        Detecta y maneja la página de encuesta que puede aparecer después del login.
        Si detecta la encuesta, hace clic en el botón "OMITIR".
        """
        try:
            # Verificar si estamos en la página de encuesta
            page_source = self.driver.page_source

            if (
                "Encuesta" in self.driver.title
                or "Queremos conocer tu opinión" in page_source
            ):
                await self._log("🔔 Página de encuesta detectada", "info")
                await self._capture_screenshot("encuesta_detectada")

                # Buscar el botón "OMITIR"
                try:
                    # El botón tiene el texto "OMITIR" y href que contiene "set_survey_check.html?a=later"
                    omit_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                "//a[contains(@href, 'set_survey_check.html?a=later')]",
                            )
                        )
                    )

                    await self._log(
                        "✅ Botón 'OMITIR' encontrado, haciendo clic...", "info"
                    )
                    await self._human_delay(1, 2)
                    await self._human_click(omit_button)
                    await self._human_delay(2, 4)
                    await self._capture_screenshot("encuesta_omitida")
                    await self._log("✅ Encuesta omitida exitosamente", "success")

                except TimeoutException:
                    await self._log(
                        "⚠️ No se encontró el botón OMITIR en la encuesta", "warning"
                    )
                except Exception as e:
                    await self._log(f"⚠️ Error al omitir encuesta: {e}", "warning")
            else:
                await self._log("✓ No se detectó página de encuesta", "info")

        except Exception as e:
            await self._log(f"⚠️ Error verificando encuesta: {e}", "warning")

    async def login(self) -> bool:
        """
        Realiza login usando técnicas stealth.

        Returns:
            True si el login fue exitoso
        """
        if not self.driver:
            await self._log("Navegador no iniciado", "error")
            return False

        try:
            # Intentar cargar sesión existente primero
            if await self.load_session():
                if await self.test_session_validity():
                    await self._log(
                        "Sesión válida encontrada, navegando al tablero", "success"
                    )
                    # Navegar al tablero (sin capturas aquí; se capturará en scrape_job_board)
                    await self._log(f"Navegando a: {self.JOB_BOARD_URL}", "info")
                    self.driver.get(self.JOB_BOARD_URL)
                    await self._human_delay(3, 5)

                    # Verificar si aparece página de encuesta y omitirla
                    await self._handle_survey_popup()

                    self._is_authenticated = True
                    return True
                else:
                    await self._log(
                        "Sesión inválida, procediendo con login completo", "warning"
                    )

            await self._log("Iniciando login stealth...", "info")

            # Obtener credenciales
            username, password = await self._get_credentials()

            # Navegar a página de login
            await self._log("Navegando a página de login...", "info")
            self.driver.get(self.LOGIN_URL)
            # Removido screenshot de navegando_login

            # Esperar y simular comportamiento humano
            await self._human_delay(2, 4)
            await self._capture_screenshot("pagina_login_cargada")

            # Buscar campos de login
            await self._log("Buscando campos de login...", "info")

            try:
                username_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "user"))
                )
                password_field = self.driver.find_element(By.ID, "pass")
                submit_button = self.driver.find_element(
                    By.CSS_SELECTOR, "button[type='submit']"
                )

                await self._log("Campos encontrados, llenando formulario...", "info")
                # Removido screenshot de campos_encontrados

                # Llenar campos con comportamiento humano
                await self._human_type(username_field, username)
                await self._capture_screenshot("usuario_escrito")
                await self._human_delay(0.5, 1.5)
                await self._human_type(password_field, password)
                await self._capture_screenshot("credenciales_completas")
                await self._human_delay(1, 2)

                # Hacer clic con comportamiento humano
                # Removido screenshot de antes_del_click
                await self._human_click(submit_button)
                # Removido screenshot de despues_del_click

                await self._log("Formulario enviado, esperando respuesta...", "info")

                # Esperar redirección o respuesta
                await self._human_delay(3, 6)

                # Verificar si el login fue exitoso
                current_url = self.driver.current_url
                page_title = self.driver.title

                await self._log(f"URL después del login: {current_url}", "info")
                await self._log(f"Título de la página: {page_title}", "info")

                # Verificar éxito
                if "login" not in current_url.lower() or "job_board" in current_url:
                    await self._log("Login exitoso detectado", "success")
                    await self._capture_screenshot("login_exitoso")
                    self._is_authenticated = True

                    # Verificar si aparece página de encuesta y omitirla
                    await self._handle_survey_popup()

                    # Guardar sesión
                    await self.save_session()
                    return True
                else:
                    await self._log("Login fallido - aún en página de login", "error")
                    return False

            except TimeoutException:
                await self._log("Timeout esperando campos de login", "error")
                return False
            except NoSuchElementException as e:
                await self._log(f"Elemento no encontrado: {e}", "error")
                return False

        except Exception as e:
            await self._log(f"Error durante login: {e}", "error")
            return False

    async def _human_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """
        Simula delay humano aleatorio.

        Args:
            min_seconds: Mínimo de segundos
            max_seconds: Máximo de segundos
        """
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    async def _human_type(self, element, text: str):
        """
        Simula escritura humana.

        Args:
            element: Elemento web
            text: Texto a escribir
        """
        # Limpiar campo primero
        element.clear()
        await self._human_delay(0.1, 0.3)

        # Escribir carácter por carácter con delays aleatorios
        for char in text:
            element.send_keys(char)
            await self._human_delay(0.05, 0.2)

    async def _human_click(self, element):
        """
        Simula clic humano con movimiento del mouse.

        Args:
            element: Elemento a hacer clic
        """
        # Mover mouse al elemento primero
        actions = ActionChains(self.driver)
        actions.move_to_element(element).perform()
        await self._human_delay(0.2, 0.5)

        # Hacer clic
        element.click()

    @staticmethod
    def _remove_duplicate_cookies(cookies: list) -> tuple[list, int]:
        """
        Elimina cookies duplicadas basándose en nombre+dominio.

        Args:
            cookies: Lista de cookies a limpiar

        Returns:
            Tupla con (lista de cookies únicas, número de duplicadas eliminadas)
        """
        unique_cookies = []
        seen_cookies = set()
        duplicates_count = 0

        for cookie in cookies:
            # Crear clave única para detectar duplicadas
            cookie_key = f"{cookie.get('name', '')}_{cookie.get('domain', '')}"

            if cookie_key not in seen_cookies:
                seen_cookies.add(cookie_key)
                unique_cookies.append(cookie)
            else:
                duplicates_count += 1

        return unique_cookies, duplicates_count

    async def save_session(self) -> bool:
        """
        Guarda la sesión actual (cookies).

        Returns:
            True si se guardó correctamente
        """
        if not self.driver:
            return False

        try:
            cookies = self.driver.get_cookies()
            await self._log(f"Obtenidas {len(cookies)} cookies del navegador", "info")

            # Normalizar dominios de cookies para compatibilidad
            normalized_cookies = []

            for cookie in cookies:
                normalized_cookie = cookie.copy()

                # Normalizar dominio para dvcarreras
                if "dvcarreras.davinci.edu.ar" in cookie.get("domain", ""):
                    normalized_cookie["domain"] = "dvcarreras.davinci.edu.ar"
                elif ".davinci.edu.ar" in cookie.get("domain", ""):
                    normalized_cookie["domain"] = ".davinci.edu.ar"

                # Asegurar que el path sea válido
                if not normalized_cookie.get("path"):
                    normalized_cookie["path"] = "/"

                normalized_cookies.append(normalized_cookie)

            # Protección: Eliminar duplicadas después de normalizar
            unique_cookies, duplicates_count = self._remove_duplicate_cookies(
                normalized_cookies
            )

            if duplicates_count > 0:
                await self._log(
                    f"⚠️ Se eliminaron {duplicates_count} cookies duplicadas al guardar",
                    "warning",
                )
                # Log de debugging: mostrar qué cookies quedaron
                cookie_names = [f"{c['name']} ({c['domain']})" for c in unique_cookies]
                await self._log(
                    f"Cookies únicas guardadas: {', '.join(cookie_names)}", "info"
                )

            session_data = {
                "cookies": unique_cookies,
                "timestamp": datetime.now().isoformat(),
                "user_agent": self.driver.execute_script("return navigator.userAgent;"),
            }

            os.makedirs(os.path.dirname(self.session_file), exist_ok=True)
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2)

            await self._log(
                f"Sesión guardada con {len(unique_cookies)} cookies únicas", "success"
            )
            return True

        except Exception as e:
            await self._log(f"Error guardando sesión: {e}", "error")
            return False

    async def load_session(self) -> bool:
        """
        Carga una sesión guardada.

        Returns:
            True si se cargó correctamente
        """
        if not self.driver or not os.path.exists(self.session_file):
            return False

        try:
            with open(self.session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # Verificar antigüedad de la sesión (máximo 24 horas)
            session_time = datetime.fromisoformat(session_data["timestamp"])
            age_seconds = (datetime.now() - session_time).total_seconds()
            age_hours = age_seconds / 3600
            age_minutes = (age_seconds % 3600) / 60

            if age_hours >= 1:
                await self._log(
                    f"Sesión guardada hace {age_hours:.1f} horas ({int(age_hours)}h {int(age_minutes)}m)",
                    "info",
                )
            else:
                await self._log(
                    f"Sesión guardada hace {int(age_minutes)} minutos", "info"
                )

            if (datetime.now() - session_time).total_seconds() > 86400:
                await self._log(
                    "Sesión expirada (más de 24h), eliminando archivo", "warning"
                )
                os.remove(self.session_file)
                return False

            # Navegar primero al dominio correcto para cargar cookies
            await self._log(
                "Navegando al dominio correcto para cargar cookies...", "info"
            )
            self.driver.get("https://dvcarreras.davinci.edu.ar/")
            await self._human_delay(2, 3)

            # CRÍTICO: Limpiar TODAS las cookies antes de cargar las guardadas
            await self._log("Limpiando cookies existentes del navegador...", "info")
            self.driver.delete_all_cookies()
            await self._human_delay(1, 2)

            # Cargar cookies
            cookies = session_data["cookies"]
            await self._log(
                f"Intentando cargar {len(cookies)} cookies guardadas", "info"
            )

            # Protección: Eliminar duplicadas antes de cargar (por si acaso)
            unique_cookies, duplicates_count = self._remove_duplicate_cookies(cookies)

            if duplicates_count > 0:
                await self._log(
                    f"⚠️ Se detectaron y eliminaron {duplicates_count} cookies duplicadas al cargar",
                    "warning",
                )
                await self._log(
                    f"Cookies únicas después de filtrar: {len(unique_cookies)}/{len(cookies)}",
                    "info",
                )

            loaded_count = 0
            skipped_count = 0

            for cookie in unique_cookies:
                cookie_name = cookie.get("name", "desconocida")
                cookie_domain = cookie.get("domain", "sin dominio")
                await self._log(
                    f"Intentando cargar cookie: {cookie_name} (dominio: {cookie_domain})",
                    "info",
                )

                # Intentar cargar la cookie tal como está
                try:
                    self.driver.add_cookie(cookie)
                    loaded_count += 1
                    await self._log(
                        f"✅ Cookie '{cookie_name}' cargada exitosamente", "success"
                    )
                    continue
                except Exception as e:
                    # Si falla, intentar con dominio normalizado
                    if "invalid cookie domain" in str(e):
                        await self._log(
                            f"⚠️ Cookie '{cookie_name}' falló, intentando normalizar dominio...",
                            "warning",
                        )

                        # Crear cookie normalizada
                        normalized_cookie = cookie.copy()

                        # Intentar diferentes dominios (orden específico para dvcarreras)
                        domains_to_try = [
                            "dvcarreras.davinci.edu.ar",  # Dominio específico
                            ".dvcarreras.davinci.edu.ar",  # Subdominio con punto
                            ".davinci.edu.ar",  # Dominio padre
                            "davinci.edu.ar",  # Sin punto
                        ]

                        cookie_loaded = False
                        for domain in domains_to_try:
                            try:
                                normalized_cookie["domain"] = domain
                                await self._log(
                                    f"🔄 Probando dominio: {domain}", "info"
                                )
                                self.driver.add_cookie(normalized_cookie)
                                loaded_count += 1
                                await self._log(
                                    f"✅ Cookie '{cookie_name}' cargada con dominio: {domain}",
                                    "success",
                                )
                                cookie_loaded = True
                                break
                            except Exception as domain_error:
                                await self._log(
                                    f"❌ Falló con dominio {domain}: {str(domain_error)[:50]}",
                                    "warning",
                                )
                                continue

                        if not cookie_loaded:
                            skipped_count += 1
                            await self._log(
                                f"❌ Cookie '{cookie_name}' no se pudo cargar con ningún dominio",
                                "error",
                            )
                    else:
                        # Para otros errores, mostrar mensaje simple
                        await self._log(
                            f"❌ Cookie '{cookie_name}' no se pudo cargar: {str(e)[:100]}",
                            "error",
                        )
                        skipped_count += 1

            # Mensaje final más informativo
            if loaded_count > 0:
                await self._log(
                    f"Sesión cargada: {loaded_count} cookies activas", "success"
                )
                if skipped_count > 0:
                    await self._log(
                        f"({skipped_count} cookies obsoletas omitidas)", "info"
                    )
            else:
                await self._log(
                    "Sesión guardada expirada, se requiere nuevo login", "warning"
                )
            return True

        except Exception as e:
            await self._log(f"Error cargando sesión: {e}", "error")
            return False

    async def test_session_validity(self) -> bool:
        """
        Prueba si la sesión cargada es válida.

        Returns:
            True si la sesión es válida
        """
        if not self.driver:
            return False

        try:
            await self._log("Probando validez de sesión...", "info")

            # Debug: Verificar cookies antes de validar
            current_cookies = self.driver.get_cookies()
            cookie_names = [f"{c['name']}" for c in current_cookies]
            await self._log(
                f"Cookies en navegador antes de validar: {', '.join(cookie_names)}",
                "info",
            )

            # Usar el dashboard principal para validar (más confiable)
            validation_url = "https://dvcarreras.davinci.edu.ar/news_list-0-15-0.html"
            self.driver.get(validation_url)
            await self._human_delay(3, 5)

            current_url = self.driver.current_url
            page_title = self.driver.title

            await self._log(f"URL de validación: {current_url}", "info")
            await self._log(f"Título: {page_title}", "info")

            # Verificar si estamos en la página correcta o redirigidos a login
            if (
                "login" in current_url.lower()
                or "login" in page_title.lower()
                or "credenciales" in page_title.lower()
            ):
                await self._log(
                    "Sesión inválida - redirigido a login (cookies expiradas en el servidor)",
                    "warning",
                )
                return False
            elif (
                "news_list" in current_url.lower()
                or "davinci" in page_title.lower()
                or page_title.strip() == ""
            ):
                # Si estamos en el dashboard o página principal, sesión válida
                await self._log(
                    "Sesión válida - acceso exitoso al dashboard", "success"
                )
                await self._capture_screenshot("dashboard_accedido")
                self._is_authenticated = True
                return True
            else:
                # Si no estamos en login, asumir sesión válida
                await self._log("Sesión válida - no redirigido a login", "success")
                self._is_authenticated = True
                return True

        except Exception as e:
            await self._log(f"Error validando sesión: {e}", "error")
            return False

    async def scrape_job_board(self, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Scrapea el tablero de ofertas.

        Args:
            max_pages: Número máximo de páginas a scrapear

        Returns:
            Lista de ofertas encontradas
        """
        if not self.driver or not self._is_authenticated:
            await self._log("No se puede scrapear sin estar autenticado", "error")
            return []

        try:
            await self._log("Iniciando scraping del tablero de ofertas...", "info")

            # Navegar al tablero
            await self._log(f"Navegando a: {self.JOB_BOARD_URL}", "info")
            self.driver.get(self.JOB_BOARD_URL)
            await self._human_delay(3, 5)

            # Verificar si aparece página de encuesta antes de scrapear
            await self._handle_survey_popup()

            # ÚNICA captura de ofertas al entrar al tablero
            await self._capture_screenshot("tablero_cargado")

            # Verificar URL actual
            current_url = self.driver.current_url
            await self._log(f"URL actual después de navegar: {current_url}", "info")
            # Removido screenshot redundante de URL verificada

            # Verificar que no hayamos sido redirigidos
            current_url = self.driver.current_url
            if "login" in current_url.lower():
                await self._log("Redirigido a login durante scraping", "error")
                return []

            # Verificar si hay Cloudflare Turnstile
            page_content = self.driver.page_source
            if (
                "turnstile" in page_content.lower()
                or "verificar que usted es un ser humano" in page_content.lower()
            ):
                await self._log(
                    "Cloudflare Turnstile detectado, esperando resolución automática...",
                    "warning",
                )

                # Esperar más tiempo para resolución automática
                await self._human_delay(10, 15)

                # Verificar si se resolvió
                page_content = self.driver.page_source
                if "turnstile" in page_content.lower():
                    await self._log("Turnstile no se resolvió automáticamente", "error")
                    return []
                else:
                    await self._log("Turnstile resuelto automáticamente", "success")

            # Extraer ofertas
            jobs = []
            job_rows = self.driver.find_elements(By.CSS_SELECTOR, "tbody tr")

            await self._log(f"Encontradas {len(job_rows)} filas en el tablero", "info")
            # Removido screenshot redundante de filas

            for i, row in enumerate(job_rows):
                try:
                    # Removido: Solo capturar screenshot para las primeras 3 ofertas para evitar spam
                    # Buscar información de la oferta
                    first_td = row.find_element(By.CSS_SELECTOR, "td:first-child")
                    row_text = first_td.text.strip()

                    # Buscar título
                    title_element = first_td.find_element(By.CSS_SELECTOR, "strong")
                    title = title_element.text.strip() if title_element else ""

                    # Buscar descripción
                    details_element = first_td.find_element(By.CSS_SELECTOR, "small")
                    description = (
                        details_element.text.strip() if details_element else ""
                    )

                    # Buscar email protegido
                    email_html = ""
                    try:
                        email_link = details_element.find_element(
                            By.CSS_SELECTOR, "a[href*='email-protection']"
                        )
                        email_html = email_link.get_attribute("outerHTML")
                    except NoSuchElementException:
                        pass

                    # Buscar email en texto
                    import re

                    email_regex = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
                    emails_in_text = re.findall(email_regex, description)
                    found_email = emails_in_text[0] if emails_in_text else ""

                    if title and len(title) > 3:
                        jobs.append(
                            {
                                "title": title,
                                "description": description,
                                "email_html": email_html,
                                "email_text": found_email,
                                "raw_html": first_td.get_attribute("outerHTML")[:2000],
                            }
                        )

                except Exception as e:
                    await self._log(f"Error procesando fila: {e}", "warning")
                    continue

            await self._log(
                f"Scraping completado: {len(jobs)} ofertas encontradas", "success"
            )
            return jobs

        except Exception as e:
            await self._log(f"Error durante scraping: {e}", "error")
            return []

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
