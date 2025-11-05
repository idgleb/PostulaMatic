"""
Script de diagnóstico para verificar las API keys de OpenAI.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')
django.setup()

from matching.models import AIConfiguration

def check_openai_keys():
    """Verifica las API keys de OpenAI configuradas."""
    print("\n" + "="*80)
    print("🔍 DIAGNÓSTICO DE API KEYS DE OPENAI")
    print("="*80 + "\n")
    
    try:
        config = AIConfiguration.objects.first()
        
        if not config:
            print("❌ No hay configuración de IA en la base de datos")
            return
        
        print(f"📊 Estado de OpenAI:")
        print(f"   - Habilitado: {config.openai_enabled}")
        print(f"   - Modelo: {config.openai_model}")
        print(f"   - API Key (encriptada) existe: {bool(config.openai_api_key)}")
        
        if config.openai_api_key:
            # Intentar desencriptar
            try:
                decrypted_key = config.get_openai_key()
                print(f"   - API Key desencriptada: {decrypted_key[:8]}...{decrypted_key[-4:]}")
                print(f"   - Longitud de la key: {len(decrypted_key)} caracteres")
                
                # Verificar formato
                if decrypted_key.startswith('sk-'):
                    print(f"   ✅ Formato correcto (comienza con 'sk-')")
                else:
                    print(f"   ⚠️ Formato sospechoso (NO comienza con 'sk-')")
                
                # Probar la key con OpenAI
                print("\n🧪 Probando la API key con OpenAI...")
                try:
                    import openai
                    openai.api_key = decrypted_key
                    
                    # Hacer una llamada simple
                    response = openai.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": "Di 'hola'"}],
                        max_tokens=10
                    )
                    print(f"   ✅ API key VÁLIDA y con CRÉDITOS")
                    print(f"   ✅ Respuesta: {response.choices[0].message.content}")
                    
                except openai.AuthenticationError as e:
                    print(f"   ❌ API key INVÁLIDA o NO AUTORIZADA")
                    print(f"   ❌ Error: {e}")
                    
                except openai.RateLimitError as e:
                    print(f"   ⚠️ API key VÁLIDA pero SIN CRÉDITOS (cuota agotada)")
                    print(f"   ⚠️ Error: {e}")
                    
                except Exception as e:
                    print(f"   ❌ Error al probar la API key: {e}")
                    
            except Exception as e:
                print(f"   ❌ Error al desencriptar la key: {e}")
        else:
            print(f"   ❌ No hay API key configurada")
        
        print("\n" + "="*80)
        print("📋 RECOMENDACIONES:")
        print("="*80)
        
        if not config.openai_api_key:
            print("1. Ve a: http://localhost:8000/matching/admin/ai-config/")
            print("2. Ingresa una API key válida de OpenAI")
            print("3. Obtén tu API key en: https://platform.openai.com/api-keys")
        else:
            print("1. Verifica que tu API key sea correcta en:")
            print("   https://platform.openai.com/api-keys")
            print("2. Verifica que tengas créditos en:")
            print("   https://platform.openai.com/account/billing")
            print("3. Si la key es incorrecta, genera una nueva y actualízala en:")
            print("   http://localhost:8000/matching/admin/ai-config/")
        
        print("\n")
        
    except Exception as e:
        print(f"❌ Error en el diagnóstico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_openai_keys()

