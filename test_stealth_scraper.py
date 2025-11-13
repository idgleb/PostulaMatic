#!/usr/bin/env python
"""
Script de prueba para el scraper stealth de DV Carreras.
"""

import os
import sys
import django
import asyncio
import logging

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postulamatic.settings")
django.setup()

from matching.clients.dvcarreras_stealth import DVCarrerasStealth

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_stealth_scraper():
    """Prueba el scraper stealth."""

    print("🚀 Iniciando prueba del scraper stealth...")

    # Usar usuario ID 2 (que ya tiene credenciales configuradas)
    user_id = 2

    try:
        # Crear cliente stealth
        client = DVCarrerasStealth(
            user_id=user_id, headless=False
        )  # headless=False para ver el navegador

        print(f"✅ Cliente stealth creado para usuario {user_id}")

        # Iniciar navegador
        print("🔧 Iniciando navegador...")
        if not await client.start():
            print("❌ Error iniciando navegador")
            return

        print("✅ Navegador iniciado correctamente")

        # Realizar login
        print("🔐 Realizando login...")
        if await client.login():
            print("✅ Login exitoso")

            # Scrapear ofertas
            print("📋 Scrapeando ofertas...")
            jobs = await client.scrape_job_board(max_pages=1)

            print(f"✅ Scraping completado: {len(jobs)} ofertas encontradas")

            # Mostrar resultados
            for i, job in enumerate(jobs, 1):
                print(f"\n--- Oferta {i} ---")
                print(f"Título: {job.get('title', 'N/A')}")
                print(f"Descripción: {job.get('description', 'N/A')[:100]}...")
                print(f"Email: {job.get('email_text', 'N/A')}")

        else:
            print("❌ Login fallido")

    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
        import traceback

        traceback.print_exc()

    finally:
        # Cerrar navegador
        try:
            await client.close()
            print("🔒 Navegador cerrado")
        except:
            pass


if __name__ == "__main__":
    asyncio.run(test_stealth_scraper())
