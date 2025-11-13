#!/usr/bin/env python3
"""
Script para configurar las variables de entorno para los proveedores de IA.
"""

import os
import sys
from pathlib import Path


def setup_environment():
    """Configura las variables de entorno para IA."""

    print("🤖 Configurando entorno para proveedores de IA...")

    # Verificar si existe archivo .env
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 Creando archivo .env...")
        # Crear archivo .env con configuración básica
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("# Configuración de PostulaMatic\n")
            f.write("# Configuración de IA\n")
            f.write("OPENAI_API_KEY=your-openai-api-key-here\n")
            f.write("OPENAI_MODEL=gpt-3.5-turbo\n")
            f.write("ANTHROPIC_API_KEY=your-anthropic-api-key-here\n")
            f.write("ANTHROPIC_MODEL=claude-3-haiku-20240307\n")
            f.write("AI_PROVIDER=openai\n")
            f.write("\n")

    # Leer archivo .env existente
    env_vars = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key] = value

    # Configurar variables de IA
    ai_vars = {
        "OPENAI_API_KEY": "your-openai-api-key-here",
        "OPENAI_MODEL": "gpt-3.5-turbo",
        "ANTHROPIC_API_KEY": "your-anthropic-api-key-here",
        "ANTHROPIC_MODEL": "claude-3-haiku-20240307",
        "AI_PROVIDER": "openai",
    }

    # Agregar variables que no existen
    updated = False
    for key, default_value in ai_vars.items():
        if key not in env_vars:
            env_vars[key] = default_value
            updated = True
            print(f"✅ Agregado: {key}={default_value}")

    # Escribir archivo .env actualizado
    if updated:
        with open(env_file, "w", encoding="utf-8") as f:
            f.write("# Configuración de PostulaMatic\n")
            f.write("# Configuración de IA\n")
            for key, value in ai_vars.items():
                f.write(f"{key}={value}\n")
            f.write("\n")

            # Mantener otras variables existentes
            for key, value in env_vars.items():
                if key not in ai_vars:
                    f.write(f"{key}={value}\n")

        print(f"📄 Archivo .env actualizado")
    else:
        print("ℹ️ Archivo .env ya está actualizado")

    # Mostrar instrucciones
    print("\n📋 Próximos pasos:")
    print("1. Edita el archivo .env y agrega tus API keys reales:")
    print("   - OPENAI_API_KEY=sk-...")
    print("   - ANTHROPIC_API_KEY=sk-ant-...")
    print("\n2. Obtén API keys de:")
    print("   - OpenAI: https://platform.openai.com/api-keys")
    print("   - Anthropic: https://console.anthropic.com/")
    print("\n3. Ejecuta el comando de prueba:")
    print("   python manage.py test_ai_integration")


def check_current_config():
    """Verifica la configuración actual."""

    print("🔍 Verificando configuración actual...")

    # Variables a verificar
    vars_to_check = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AI_PROVIDER"]

    configured = True
    for var in vars_to_check:
        value = os.getenv(var)
        if value and value not in [
            "your-openai-api-key-here",
            "your-anthropic-api-key-here",
        ]:
            print(f"✅ {var}: Configurado")
        else:
            print(f"❌ {var}: No configurado o usando valor por defecto")
            configured = False

    return configured


def main():
    """Función principal."""

    if len(sys.argv) > 1 and sys.argv[1] == "check":
        configured = check_current_config()
        if configured:
            print("\n🎉 ¡Configuración completa! Puedes probar la integración.")
        else:
            print(
                "\n⚠️ Configuración incompleta. Ejecuta el script sin argumentos para configurar."
            )
        return

    setup_environment()
    check_current_config()


if __name__ == "__main__":
    main()
