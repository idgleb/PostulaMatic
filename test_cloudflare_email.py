#!/usr/bin/env python3
"""
Script para probar el decodificador con el ejemplo específico del usuario.
"""
import os
import sys

import django

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postulamatic.settings")
django.setup()

from matching.utils.email_decoder import get_email_from_job_html


def test_specific_cloudflare_email():
    """Prueba con el ejemplo específico del usuario."""

    # Ejemplo exacto del usuario
    test_html = """
    <a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="14733a76717a7d60716e547666757a70727b6679757a77713a7875">[email&#160;protected]</a>
    """

    print("🧪 Probando decodificador con ejemplo del usuario...")
    print(f"HTML de entrada: {test_html.strip()}")

    # Decodificar el email
    decoded_email = get_email_from_job_html(test_html)

    print(f"Email decodificado: {decoded_email}")

    if decoded_email:
        print("✅ ¡Email decodificado exitosamente!")
        return True
    else:
        print("❌ No se pudo decodificar el email")
        return False


if __name__ == "__main__":
    success = test_specific_cloudflare_email()
    sys.exit(0 if success else 1)
