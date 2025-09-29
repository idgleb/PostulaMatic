"""
Cliente simple con Playwright para dvcarreras.davinci.edu.ar
Usa un navegador real para evitar detección de Cloudflare.
"""
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class JobPostingData:
    """Estructura de datos para una oferta de trabajo."""
    external_id: str
    title: str
    description: str
    email: str
    raw_html: str

# Import para decodificar emails de Cloudflare
try:
    from ..utils.email_decoder import get_email_from_job_html
except ImportError:
    # Fallback si no se puede importar
    def get_email_from_job_html(html_content: str) -> str:
        return ""


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


def is_duplicate_job(job_data: JobPostingData) -> str:
    """
    Verifica si una oferta de trabajo ya existe en la base de datos.
    
    Args:
        job_data: Datos de la oferta a verificar
        
    Returns:
        'new': Nueva oferta
        'duplicate': Oferta duplicada
    """
    try:
        from matching.models import JobPosting
        
        logger.info(f"Buscando duplicado: {job_data.title} | {job_data.email} | {job_data.description[:50]}...")
        
        # Buscar por email + título + descripción (combinación única)
        existing = JobPosting.objects.filter(
            email=job_data.email,
            title=job_data.title,
            description=job_data.description
        ).first()
        
        if existing:
            logger.info(f"Oferta duplicada encontrada: {job_data.title} - {job_data.email}")
            return 'duplicate'
        
        logger.info(f"No se encontró duplicado para: {job_data.title}")
        return 'new'
        
    except Exception as e:
        logger.error(f"Error verificando duplicado: {e}")
        return 'new'  # En caso de error, asumir que es nueva


@dataclass
class JobPostingData:
    """Estructura de datos para una oferta de trabajo."""
    external_id: str
    title: str
    description: str
    email: str = ""
    raw_html: str = ""


class DVCarrerasPlaywrightSimple:
    """Cliente simple con Playwright para evitar Cloudflare"""
    
    BASE_URL = "https://dvcarreras.davinci.edu.ar"
    LOGIN_URL = "https://dvcarreras.davinci.edu.ar/login.html"
    JOB_BOARD_URL = "https://dvcarreras.davinci.edu.ar/job_board-0.html"
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
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
        """Inicia el navegador."""
        try:
            from playwright.async_api import async_playwright
            
            self.playwright = await async_playwright().start()
            
            # Usar Chromium con configuraciones anti-detección
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Cambiar a False para ver el navegador
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                ]
            )
            
            # Crear contexto
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='es-AR',
                timezone_id='America/Argentina/Buenos_Aires',
            )
            
            # Crear página
            self.page = await self.context.new_page()
            
            # Inyectar scripts anti-detección
            await self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)
            
            logger.info("Navegador Playwright iniciado")
            
        except Exception as e:
            logger.error(f"Error iniciando Playwright: {e}")
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
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Navegador Playwright cerrado")
        except Exception as e:
            logger.error(f"Error cerrando Playwright: {e}")
    
    async def login(self) -> bool:
        """Realiza login usando navegador real."""
        try:
            logger.info(f"Iniciando login con Playwright para usuario: {self.username}")
            
            # Navegar a la página de login
            await self.page.goto(self.LOGIN_URL, wait_until='networkidle')
            await asyncio.sleep(3)  # Esperar a que se cargue completamente
            
            # Verificar si hay Cloudflare
            page_content = await self.page.content()
            if "Just a moment" in page_content or "cloudflare" in page_content.lower():
                logger.warning("Detectado Cloudflare, esperando...")
                await asyncio.sleep(10)  # Esperar más tiempo para Cloudflare
            
            # Buscar campos de login
            username_field = await self.page.query_selector('input[name="username"], input[name="user"], input[type="text"]')
            password_field = await self.page.query_selector('input[type="password"]')
            
            if not username_field or not password_field:
                logger.error("No se encontraron campos de usuario/contraseña")
                return False
            
            # Llenar campos
            await username_field.fill(self.username)
            await asyncio.sleep(1)
            await password_field.fill(self.password)
            await asyncio.sleep(1)
            
            # Buscar botón de login
            login_button = await self.page.query_selector('button[type="submit"], input[type="submit"], button:has-text("Login"), button:has-text("Entrar")')
            
            if login_button:
                await login_button.click()
            else:
                await self.page.keyboard.press('Enter')
            
            # Esperar navegación
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)
            
            # Verificar si el login fue exitoso
            current_url = self.page.url
            page_content = await self.page.content()
            
            logger.info(f"URL actual después del login: {current_url}")
            logger.info(f"Contenido de la página (primeros 500 caracteres): {page_content[:500]}")
            
            if self._is_login_successful(current_url, page_content):
                self._is_authenticated = True
                logger.info("Login exitoso con Playwright")
                return True
            else:
                logger.error("Login fallido - credenciales incorrectas")
                return False
                
        except Exception as e:
            logger.error(f"Error durante login con Playwright: {e}")
            return False
    
    def _is_login_successful(self, current_url: str, page_content: str) -> bool:
        """Verifica si el login fue exitoso."""
        page_content_lower = page_content.lower()
        
        # Verificar mensajes de error específicos y claros
        specific_error_indicators = [
            'usuario o contraseña incorrectos',
            'credenciales incorrectas',
            'login fallido',
            'error de autenticación',
            'invalid credentials',
            'wrong password',
            'incorrect username',
            'authentication failed'
        ]
        
        for error in specific_error_indicators:
            if error in page_content_lower:
                logger.warning(f"Indicador de error específico encontrado: {error}")
                return False
        
        # Verificar si estamos en la página de login (indica fallo)
        if 'login' in current_url.lower():
            logger.warning("Aún en página de login - credenciales incorrectas")
            return False
        
        # Verificar indicadores de éxito más específicos
        success_indicators = [
            'dashboard',
            'panel',
            'welcome',
            'bienvenido',
            'logout',
            'salir',
            'perfil',
            'profile',
            'menu',
            'navegación',
            'job_board',
            'oferta',
            'trabajo'
        ]
        
        for indicator in success_indicators:
            if indicator.lower() in page_content_lower:
                logger.info(f"Indicador de éxito encontrado: {indicator}")
                return True
        
        # Si no hay indicadores claros, verificar si la URL cambió
        if 'dvcarreras.davinci.edu.ar' in current_url and 'login' not in current_url.lower():
            logger.info("URL cambió y no contiene 'login' - posible éxito")
            return True
        
        # Si no hay indicadores claros, asumir fallo
        logger.warning("No se encontraron indicadores claros de éxito o fallo")
        return False
    
    async def scrape_job_board(self, max_pages: int = 1) -> List[JobPostingData]:
        """Scrapea el tablero de ofertas."""
        if not self._is_authenticated:
            logger.error("No se puede scrapear sin estar autenticado")
            return []
        
        try:
            logger.info(f"Iniciando scraping con Playwright en la página específica de ofertas")
            
            job_postings = []
            
            # Ir directamente a la página específica de ofertas
            job_board_url = "https://dvcarreras.davinci.edu.ar/job_board-0.html"
            logger.info(f"Navegando a: {job_board_url}")
            
            await self.page.goto(job_board_url, wait_until='networkidle')
            await asyncio.sleep(3)
            
            # DEBUG: Guardar HTML de la página para inspección
            page_html = await self.page.content()
            logger.info(f"DEBUG: HTML de la página capturado ({len(page_html)} caracteres)")
            
            # Guardar HTML en archivo para debug
            try:
                with open('/app/job_board_debug.html', 'w', encoding='utf-8') as f:
                    f.write(page_html)
                logger.info("DEBUG: HTML guardado en job_board_debug.html")
            except Exception as e:
                logger.error(f"DEBUG: Error guardando HTML: {e}")
            
            # DEBUG: Buscar texto en la página
            page_text = await self.page.text_content('body')
            logger.info(f"DEBUG: Texto de la página (primeros 500 chars): {page_text[:500]}")
            
            # DEBUG: Contar elementos
            divs_count = await self.page.evaluate("document.querySelectorAll('div').length")
            links_count = await self.page.evaluate("document.querySelectorAll('a').length")
            tables_count = await self.page.evaluate("document.querySelectorAll('table').length")
            logger.info(f"DEBUG: Elementos encontrados - divs: {divs_count}, links: {links_count}, tables: {tables_count}")
            
            # Extraer ofertas usando JavaScript específico para el formato de dvcarreras
            page_jobs = await self.page.evaluate("""
                        () => {
                            const jobs = [];
                            
                            // Buscar específicamente filas tr que contengan ofertas
                            const jobRows = document.querySelectorAll('tbody tr');
                            console.log('Total filas tr encontradas:', jobRows.length);
                            
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
                                    
                                    // Buscar enlaces de email protegido por Cloudflare dentro del elemento small
                                    let emailHtml = '';
                                    if (detailsElement) {
                                        const emailLink = detailsElement.querySelector('a[href*="email-protection"]');
                                        if (emailLink) {
                                            emailHtml = emailLink.outerHTML;
                                            console.log('Email protegido encontrado:', emailHtml);
                                        }
                                    }
                                    
                                    // También buscar emails en el texto usando regex
                                    const emailRegex = /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g;
                                    const emailsInText = description.match(emailRegex);
                                    let foundEmail = '';
                                    if (emailsInText && emailsInText.length > 0) {
                                        foundEmail = emailsInText[0]; // Tomar el primer email encontrado
                                        console.log('Email encontrado en texto:', foundEmail);
                                    }
                                    
                                    // Solo procesar si tiene título (más flexible)
                                    if (title && title.length > 3) {
                                        jobs.push({
                                            title: title,
                                            description: description,
                                            email_html: emailHtml,
                                            email_text: foundEmail,
                                            raw_html: firstTd.outerHTML.substring(0, 2000)
                                        });
                                
                                        // Debug más detallado
                                        const finalEmail = foundEmail || (emailHtml ? 'CF_PROTECTED' : '');
                                        console.log('Oferta procesada:', title, '| Email:', finalEmail);
                                    }
                                } catch (e) {
                                    console.error('Error procesando fila:', e);
                                }
                            });
                    
                    console.log('Total ofertas encontradas:', jobs.length);
                    return jobs;
                }
            """)
            
            # Convertir a objetos JobPostingData y verificar duplicados
            new_count = 0
            duplicate_count = 0
            
            for job_data in page_jobs:
                # Decodificar email de Cloudflare
                email_from_html = get_email_from_job_html(job_data.get('email_html', ''))
                
                # Usar email del texto si no hay email decodificado
                email_from_text = job_data.get('email_text', '')
                
                # Priorizar email decodificado, luego email del texto
                final_email = email_from_html or email_from_text
                
                # Crear objeto JobPostingData
                job_posting = JobPostingData(
                    external_id="",  # Se generará después
                    title=job_data['title'],
                    description=job_data['description'],
                    email=final_email,
                    raw_html=job_data['raw_html']
                )
                
                # Generar external_id basado en contenido
                job_posting.external_id = generate_external_id(
                    job_posting.title, 
                    job_posting.email, 
                    job_posting.description
                )
                
                # Verificar si es duplicado
                logger.info(f"Verificando duplicado para: {job_posting.title}")
                duplicate_status = is_duplicate_job(job_posting)
                logger.info(f"Resultado verificación: {duplicate_status}")
                
                if duplicate_status == 'new':
                    job_postings.append(job_posting)
                    new_count += 1
                    logger.info(f"Nueva oferta: {job_posting.title} - Email: {final_email or 'No encontrado'}")
                else:
                    duplicate_count += 1
                    logger.info(f"Oferta duplicada omitida: {job_posting.title}")
            
            logger.info(f"Encontradas {len(page_jobs)} ofertas en la página: {new_count} nuevas, {duplicate_count} duplicadas")
            
            logger.info(f"Scraping con Playwright completado: {len(job_postings)} ofertas nuevas")
            return job_postings
            
        except Exception as e:
            logger.error(f"Error durante scraping con Playwright: {e}")
            return []
    
    def test_login(self) -> bool:
        """
        Prueba el login sin hacer scraping.
        Retorna True si el login es exitoso, False en caso contrario.
        """
        try:
            logger.info(f"Probando login con Playwright para usuario: {self.username}")
            
            # Ejecutar el login de forma asíncrona
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._test_login_async())
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Error durante prueba de login: {e}")
            return False
    
    async def _test_login_async(self) -> bool:
        """Versión asíncrona de la prueba de login."""
        try:
            # Iniciar navegador
            await self.start()
            
            # Realizar login
            login_success = await self.login()
            
            if login_success:
                logger.info("✅ Prueba de login exitosa")
                return True
            else:
                logger.error("❌ Prueba de login fallida - credenciales incorrectas")
                return False
                
        except Exception as e:
            logger.error(f"Error durante prueba de login asíncrona: {e}")
            return False
        finally:
            # Cerrar navegador
            await self.close()
