#!/usr/bin/env python3
"""
Script para configurar las API keys de IA en PostulaMatic.
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

def configure_openai_key():
    """Configura la API key de OpenAI."""
    print("\n🔧 Configuración de OpenAI")
    print("=" * 50)
    
    api_key = input("Ingresa tu API key de OpenAI (sk-...): ").strip()
    
    if not api_key:
        print("❌ No se ingresó API key")
        return False
    
    if not api_key.startswith('sk-'):
        print("⚠️  Advertencia: La API key de OpenAI debería empezar con 'sk-'")
    
    # Configurar variable de entorno
    os.environ['OPENAI_API_KEY'] = api_key
    
    print(f"✅ API key configurada: {api_key[:8]}...")
    return True

def configure_anthropic_key():
    """Configura la API key de Anthropic."""
    print("\n🔧 Configuración de Anthropic")
    print("=" * 50)
    
    api_key = input("Ingresa tu API key de Anthropic (sk-ant-...): ").strip()
    
    if not api_key:
        print("❌ No se ingresó API key")
        return False
    
    if not api_key.startswith('sk-ant-'):
        print("⚠️  Advertencia: La API key de Anthropic debería empezar con 'sk-ant-'")
    
    # Configurar variable de entorno
    os.environ['ANTHROPIC_API_KEY'] = api_key
    
    print(f"✅ API key configurada: {api_key[:12]}...")
    return True

def test_providers():
    """Prueba la conectividad con los proveedores configurados."""
    print("\n🧪 Probando Conectividad")
    print("=" * 50)
    
    try:
        from matching.services.ai_service import ai_email_service
        
        # Probar OpenAI
        if os.getenv('OPENAI_API_KEY'):
            print("🔍 Probando OpenAI...")
            try:
                result = ai_email_service.generate_email(
                    prompt="Escribe 'Hola' en español",
                    provider='openai'
                )
                if result.error:
                    print(f"❌ OpenAI Error: {result.error}")
                else:
                    print(f"✅ OpenAI: {result.body[:50]}...")
            except Exception as e:
                print(f"❌ OpenAI Error: {e}")
        else:
            print("⚠️  OpenAI no configurado")
        
        # Probar Anthropic
        if os.getenv('ANTHROPIC_API_KEY'):
            print("🔍 Probando Anthropic...")
            try:
                result = ai_email_service.generate_email(
                    prompt="Escribe 'Hola' en español",
                    provider='anthropic'
                )
                if result.error:
                    print(f"❌ Anthropic Error: {result.error}")
                else:
                    print(f"✅ Anthropic: {result.body[:50]}...")
            except Exception as e:
                print(f"❌ Anthropic Error: {e}")
        else:
            print("⚠️  Anthropic no configurado")
            
    except Exception as e:
        print(f"❌ Error probando servicios: {e}")

def save_to_env_file():
    """Guarda la configuración en un archivo .env"""
    env_file = project_root / '.env'
    
    # Leer archivo existente si existe
    env_content = []
    if env_file.exists():
        with open(env_file, 'r') as f:
            env_content = f.readlines()
    
    # Actualizar o agregar variables
    new_vars = {}
    for line in env_content:
        if line.strip() and not line.startswith('#'):
            if '=' in line:
                key, value = line.strip().split('=', 1)
                new_vars[key] = value
    
    # Actualizar con nuevas variables
    if os.getenv('OPENAI_API_KEY'):
        new_vars['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')
    if os.getenv('ANTHROPIC_API_KEY'):
        new_vars['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY')
    
    # Escribir archivo actualizado
    try:
        with open(env_file, 'w') as f:
            f.write("# Configuración de PostulaMatic\n")
            f.write("DEBUG=True\n")
            f.write("SECRET_KEY=your-secret-key-here\n\n")
            f.write("# Configuración de IA\n")
            
            if 'OPENAI_API_KEY' in new_vars:
                f.write(f"OPENAI_API_KEY={new_vars['OPENAI_API_KEY']}\n")
                f.write("OPENAI_MODEL=gpt-3.5-turbo\n\n")
            
            if 'ANTHROPIC_API_KEY' in new_vars:
                f.write(f"ANTHROPIC_API_KEY={new_vars['ANTHROPIC_API_KEY']}\n")
                f.write("ANTHROPIC_MODEL=claude-3-haiku-20240307\n\n")
            
            f.write("AI_PROVIDER=openai\n\n")
            f.write("# Configuración de email\n")
            f.write("EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend\n\n")
            f.write("# Configuración de Celery\n")
            f.write("CELERY_BROKER_URL=redis://redis:6379/0\n")
            f.write("CELERY_RESULT_BACKEND=redis://redis:6379/0\n")
        
        print(f"✅ Configuración guardada en {env_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error guardando archivo .env: {e}")
        return False

def main():
    """Función principal."""
    print("🤖 Configurador de API Keys de IA para PostulaMatic")
    print("=" * 60)
    
    configured_any = False
    
    while True:
        print("\n📋 Opciones disponibles:")
        print("1. Configurar OpenAI")
        print("2. Configurar Anthropic")
        print("3. Probar conectividad")
        print("4. Guardar configuración")
        print("5. Salir")
        
        choice = input("\nSelecciona una opción (1-5): ").strip()
        
        if choice == '1':
            if configure_openai_key():
                configured_any = True
        
        elif choice == '2':
            if configure_anthropic_key():
                configured_any = True
        
        elif choice == '3':
            test_providers()
        
        elif choice == '4':
            if configured_any:
                save_to_env_file()
            else:
                print("⚠️  No hay configuración nueva para guardar")
        
        elif choice == '5':
            if configured_any:
                save_choice = input("¿Guardar configuración antes de salir? (y/n): ").strip().lower()
                if save_choice == 'y':
                    save_to_env_file()
            print("👋 ¡Hasta luego!")
            break
        
        else:
            print("❌ Opción inválida")

if __name__ == '__main__':
    main()
