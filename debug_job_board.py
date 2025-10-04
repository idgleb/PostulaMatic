#!/usr/bin/env python3
"""
Script para inspeccionar la estructura HTML de la página de ofertas
y determinar los selectores CSS correctos.
"""
import asyncio
import logging

from django.contrib.auth.models import User

from matching.clients.dvcarreras_playwright_simple import \
    DVCarrerasPlaywrightSimple

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_job_board():
    """Inspecciona la página de ofertas para encontrar los selectores correctos."""
    try:
        # Obtener usuario
        user = User.objects.get(id=1)

        # Obtener credenciales del perfil
        profile = user.userprofile
        username = profile.dv_username
        password = profile.dv_password

        logger.info(f"Debugging job board para usuario: {username}")

        async with DVCarrerasPlaywrightSimple(
            username=username, password=password
        ) as client:
            # Login
            if not await client.login():
                logger.error("Login fallido")
                return

            logger.info("Login exitoso, navegando a la página de ofertas...")

            # Ir a la página de ofertas
            await client.page.goto(
                "https://dvcarreras.davinci.edu.ar/job_board-0.html",
                wait_until="networkidle",
            )
            await asyncio.sleep(3)

            # Capturar el HTML completo de la página
            page_html = await client.page.content()
            logger.info(f"HTML de la página capturado ({len(page_html)} caracteres)")

            # Guardar HTML en archivo para inspección
            with open("job_board_debug.html", "w", encoding="utf-8") as f:
                f.write(page_html)
            logger.info("HTML guardado en job_board_debug.html")

            # Buscar elementos que podrían ser ofertas
            possible_selectors = [
                "div",
                '[class*="job"]',
                '[class*="offer"]',
                '[class*="posting"]',
                '[class*="card"]',
                '[class*="item"]',
                "tr",
                "li",
                "article",
                ".row",
                ".col",
                '[id*="job"]',
                '[id*="offer"]',
            ]

            for selector in possible_selectors:
                try:
                    elements = await client.page.query_selector_all(selector)
                    if len(elements) > 0:
                        logger.info(
                            f"Selector '{selector}': {len(elements)} elementos encontrados"
                        )

                        # Mostrar algunos ejemplos del contenido
                        for i, element in enumerate(
                            elements[:3]
                        ):  # Solo los primeros 3
                            text = await element.text_content()
                            if (
                                text and len(text.strip()) > 10
                            ):  # Solo elementos con contenido significativo
                                logger.info(
                                    f"  Elemento {i+1}: {text.strip()[:100]}..."
                                )
                except Exception as e:
                    logger.error(f"Error con selector '{selector}': {e}")

            # Buscar texto que indique ofertas
            page_text = await client.page.text_content("body")
            if (
                "oferta" in page_text.lower()
                or "trabajo" in page_text.lower()
                or "empleo" in page_text.lower()
            ):
                logger.info(
                    "La página contiene palabras relacionadas con ofertas de trabajo"
                )
            else:
                logger.warning(
                    "La página NO contiene palabras relacionadas con ofertas de trabajo"
                )

            # Buscar enlaces
            links = await client.page.query_selector_all("a")
            logger.info(f"Encontrados {len(links)} enlaces en la página")

            for i, link in enumerate(links[:5]):  # Solo los primeros 5
                href = await link.get_attribute("href")
                text = await link.text_content()
                if href and text:
                    logger.info(f"  Enlace {i+1}: {text.strip()} -> {href}")

    except Exception as e:
        logger.error(f"Error durante debug: {e}")


if __name__ == "__main__":
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postulamatic.settings")
    django.setup()

    asyncio.run(debug_job_board())
