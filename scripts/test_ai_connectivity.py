#!/usr/bin/env python3
"""
Script para probar la conectividad con proveedores de IA.
"""

import asyncio
import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configurar Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "postulamatic.settings")

import django

django.setup()

from matching.services.ai_service import ai_email_service


def test_openai_connectivity():
    """Prueba la conectividad con OpenAI."""
    print("🔵 Probando conectividad con OpenAI...")

    try:
        # Verificar configuración
        if not ai_email_service.is_provider_configured("openai"):
            print("❌ OpenAI no configurado")
            return False

        # Datos de prueba simples
        job_description = "Desarrollador Python con Django"
        cv_skills = {
            "skills": ["Python", "Django", "PostgreSQL"],
            "experience_years": 3,
            "experience_summary": "Desarrollador Python",
        }
        user_profile = {"display_name": "Juan Pérez", "email": "juan@example.com"}

        # Generar email simple
        result = ai_email_service.generate_email(
            job_description=job_description,
            cv_skills=cv_skills,
            user_profile=user_profile,
            provider="openai",
        )

        if result.error:
            print(f"❌ Error: {result.error}")
            return False

        print("✅ OpenAI: Conectividad exitosa")
        print(f"   Asunto: {result.subject}")
        print(f"   Cuerpo: {result.body[:100]}...")
        print(f"   Tokens: {result.tokens_used}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_anthropic_connectivity():
    """Prueba la conectividad con Anthropic."""
    print("\n🟣 Probando conectividad con Anthropic...")

    try:
        # Verificar configuración
        if not ai_email_service.is_provider_configured("anthropic"):
            print("❌ Anthropic no configurado")
            return False

        # Datos de prueba simples
        job_description = "Desarrollador Python con Django"
        cv_skills = {
            "skills": ["Python", "Django", "PostgreSQL"],
            "experience_years": 3,
            "experience_summary": "Desarrollador Python",
        }
        user_profile = {"display_name": "Juan Pérez", "email": "juan@example.com"}

        # Generar email simple
        result = ai_email_service.generate_email(
            job_description=job_description,
            cv_skills=cv_skills,
            user_profile=user_profile,
            provider="anthropic",
        )

        if result.error:
            print(f"❌ Error: {result.error}")
            return False

        print("✅ Anthropic: Conectividad exitosa")
        print(f"   Asunto: {result.subject}")
        print(f"   Cuerpo: {result.body[:100]}...")
        print(f"   Tokens: {result.tokens_used}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Función principal."""

    print("🤖 Prueba de Conectividad con Proveedores de IA")
    print("=" * 50)

    # Verificar configuración
    print("🔧 Verificando configuración...")

    openai_key = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not openai_key or openai_key == "your-openai-api-key-here":
        print("⚠️ OpenAI API Key no configurada")
    else:
        print("✅ OpenAI API Key configurada")

    if not anthropic_key or anthropic_key == "your-anthropic-api-key-here":
        print("⚠️ Anthropic API Key no configurada")
    else:
        print("✅ Anthropic API Key configurada")

    print("\n" + "=" * 50)

    # Probar proveedores
    openai_success = False
    anthropic_success = False

    if openai_key and openai_key != "your-openai-api-key-here":
        openai_success = test_openai_connectivity()

    if anthropic_key and anthropic_key != "your-anthropic-api-key-here":
        anthropic_success = test_anthropic_connectivity()

    # Resumen
    print("\n" + "=" * 50)
    print("📊 Resumen de Pruebas:")

    if openai_success:
        print("✅ OpenAI: Funcionando correctamente")
    else:
        print("❌ OpenAI: No disponible o con errores")

    if anthropic_success:
        print("✅ Anthropic: Funcionando correctamente")
    else:
        print("❌ Anthropic: No disponible o con errores")

    if not openai_success and not anthropic_success:
        print("\n⚠️ Ningún proveedor de IA está funcionando.")
        print("   Verifica la configuración de las API keys.")
    elif openai_success or anthropic_success:
        print("\n🎉 ¡Al menos un proveedor está funcionando!")
        print("   El sistema de emails con IA está listo para usar.")


if __name__ == "__main__":
    main()
