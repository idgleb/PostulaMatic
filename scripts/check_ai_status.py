#!/usr/bin/env python3
"""
Script para verificar el estado de las API keys de IA.
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')

import django
django.setup()

def check_ai_status():
    """Verifica el estado de las API keys de IA."""
    print("🤖 Estado de Configuración de IA en PostulaMatic")
    print("=" * 60)
    
    # Verificar OpenAI
    openai_key = os.getenv('OPENAI_API_KEY')
    print(f"\n🔍 OpenAI:")
    print(f"   API Key: {'✅ CONFIGURADA' if openai_key else '❌ NO CONFIGURADA'}")
    if openai_key:
        print(f"   Preview: {openai_key[:8]}...")
        print(f"   Modelo: {os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')}")
    else:
        print(f"   Variable: OPENAI_API_KEY no encontrada")
    
    # Verificar Anthropic
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    print(f"\n🔍 Anthropic:")
    print(f"   API Key: {'✅ CONFIGURADA' if anthropic_key else '❌ NO CONFIGURADA'}")
    if anthropic_key:
        print(f"   Preview: {anthropic_key[:12]}...")
        print(f"   Modelo: {os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')}")
    else:
        print(f"   Variable: ANTHROPIC_API_KEY no encontrada")
    
    # Proveedor por defecto
    default_provider = os.getenv('AI_PROVIDER', 'openai')
    print(f"\n🎯 Proveedor por defecto: {default_provider}")
    
    # Verificar servicios disponibles
    try:
        from matching.services.ai_service import ai_email_service
        available_providers = ai_email_service.get_available_providers()
        print(f"\n📋 Proveedores disponibles: {', '.join(available_providers)}")
    except Exception as e:
        print(f"\n❌ Error verificando servicios: {e}")
    
    # Estado general
    print(f"\n📊 Estado General:")
    if openai_key or anthropic_key:
        print("   ✅ Al menos un proveedor está configurado")
        print("   🚀 El sistema de IA debería funcionar")
    else:
        print("   ❌ Ningún proveedor está configurado")
        print("   ⚠️  El sistema de IA no funcionará")
    
    # Instrucciones
    print(f"\n📝 Próximos pasos:")
    if not openai_key and not anthropic_key:
        print("   1. Configura al menos una API key:")
        print("      - OpenAI: https://platform.openai.com/api-keys")
        print("      - Anthropic: https://console.anthropic.com/")
        print("   2. Agrega la variable al archivo .env:")
        print("      OPENAI_API_KEY=sk-...")
        print("      ANTHROPIC_API_KEY=sk-ant-...")
        print("   3. Reinicia los contenedores:")
        print("      docker compose restart")
    else:
        print("   ✅ Sistema configurado correctamente")
        print("   🌐 Ve a: http://localhost:8000/matching/ai-providers-status/")
        print("   🧪 Prueba en: http://localhost:8000/matching/email-generation-test/")

if __name__ == '__main__':
    check_ai_status()
