import asyncio
import logging
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')
django.setup()

from matching.clients.dvcarreras_playwright_simple import DVCarrerasPlaywrightSimple
from django.contrib.auth.models import User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_job_board():
    try:
        user = User.objects.get(id=1)
        profile = user.userprofile
        username = profile.dv_username
        password = profile.dv_password
        
        logger.info(f'Debugging job board para usuario: {username}')
        
        async with DVCarrerasPlaywrightSimple(username=username, password=password) as client:
            if not await client.login():
                logger.error('Login fallido')
                return
            
            logger.info('Login exitoso, navegando a la página de ofertas...')
            
            await client.page.goto('https://dvcarreras.davinci.edu.ar/job_board-0.html', wait_until='networkidle')
            await asyncio.sleep(3)
            
            # Capturar el HTML completo de la página
            page_html = await client.page.content()
            logger.info(f'HTML de la página capturado ({len(page_html)} caracteres)')
            
            # Guardar HTML en archivo
            with open('/app/job_board_debug.html', 'w', encoding='utf-8') as f:
                f.write(page_html)
            logger.info('HTML guardado en job_board_debug.html')
            
            # Buscar texto que indique ofertas
            page_text = await client.page.text_content('body')
            logger.info(f'Texto de la página: {page_text[:500]}...')
            
            # Buscar elementos comunes
            divs = await client.page.query_selector_all('div')
            logger.info(f'Encontrados {len(divs)} divs')
            
            # Buscar enlaces
            links = await client.page.query_selector_all('a')
            logger.info(f'Encontrados {len(links)} enlaces')
            
            for i, link in enumerate(links[:5]):
                href = await link.get_attribute('href')
                text = await link.text_content()
                if href and text:
                    logger.info(f'  Enlace {i+1}: {text.strip()} -> {href}')
                    
    except Exception as e:
        logger.error(f'Error durante debug: {e}')

if __name__ == "__main__":
    asyncio.run(debug_job_board())
