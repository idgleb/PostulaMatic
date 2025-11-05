"""
Vistas para administración de configuración de IA.
"""

import logging
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from .models import AIConfiguration
from .forms import AIConfigurationForm
from .services.ai_service import ai_email_service

logger = logging.getLogger(__name__)


@staff_member_required
def ai_admin_config_view(request):
    """Vista principal para configurar IA (solo para staff)."""
    
    # Obtener o crear configuración
    config = AIConfiguration.get_config()
    
    if request.method == 'POST':
        form = AIConfigurationForm(request.POST, instance=config)
        if form.is_valid():
            try:
                # Log datos del formulario
                logger.info(f"🔍 Datos del formulario - OpenAI model: {form.cleaned_data.get('openai_model')}, Enabled: {form.cleaned_data.get('openai_enabled')}")
                
                # Log antes de guardar
                logger.info(f"🔍 Antes de guardar - OpenAI model: {config.openai_model}, Enabled: {config.openai_enabled}")
                
                saved_config = form.save()
                
                # Log después de guardar
                logger.info(f"🔍 Después de guardar - OpenAI model: {saved_config.openai_model}, Enabled: {saved_config.openai_enabled}")
                
                messages.success(
                    request, 
                    "✅ Configuración de IA actualizada correctamente"
                )
                # No hacer redirect, renderizar directamente para evitar duplicación
                # return redirect('ai_admin_config')
            except Exception as e:
                logger.error(f"Error guardando configuración IA: {e}")
                messages.error(
                    request, 
                    f"❌ Error guardando configuración: {str(e)}"
                )
        else:
            # No agregar mensaje de error aquí, el template se encarga de mostrar los errores
            pass
    else:
        form = AIConfigurationForm(instance=config)
    
    # Obtener estado de los proveedores
    providers_status = {}
    
    # OpenAI
    providers_status['openai'] = {
        'configured': config.openai_enabled and bool(config.openai_api_key),
        'model': config.openai_model,
        'enabled': config.openai_enabled,
        'key_preview': f"{config.openai_api_key[:8]}..." if config.openai_api_key else "No configurado"
    }
    
    # Anthropic
    providers_status['anthropic'] = {
        'configured': config.anthropic_enabled and bool(config.anthropic_api_key),
        'model': config.anthropic_model,
        'enabled': config.anthropic_enabled,
        'key_preview': f"{config.anthropic_api_key[:12]}..." if config.anthropic_api_key else "No configurado"
    }
    
    context = {
        'form': form,
        'config': config,
        'providers_status': providers_status,
        'available_providers': config.get_available_providers(),
        'is_configured': config.is_configured(),
    }
    
    return render(request, 'matching/ai_admin_config.html', context)


@staff_member_required
@require_http_methods(["POST"])
@csrf_exempt
def test_ai_provider_admin(request):
    """Prueba un proveedor de IA específico (solo para staff)."""
    try:
        data = json.loads(request.body)
        provider = data.get('provider')
        
        if not provider:
            return JsonResponse({
                'success': False,
                'error': 'Proveedor no especificado'
            })
        
        # Obtener configuración
        config = AIConfiguration.get_config()
        
        if provider == 'openai' and not (config.openai_enabled and config.openai_api_key):
            return JsonResponse({
                'success': False,
                'error': 'OpenAI no está configurado'
            })
        
        if provider == 'anthropic' and not (config.anthropic_enabled and config.anthropic_api_key):
            return JsonResponse({
                'success': False,
                'error': 'Anthropic no está configurado'
            })
        
        # Probar el proveedor con un prompt simple pero real
        # IMPORTANTE: use_fallback=False para ver el error real del proveedor
        result = ai_email_service.generate_email(
            job_description="Desarrollador Python con experiencia en Django y PostgreSQL.",
            cv_skills={"skills": ["Python", "Django", "PostgreSQL"]},
            user_profile={"display_name": "Usuario de Prueba", "email": "test@example.com"},
            provider=provider,
            custom_prompt=None,  # Usar generación completa de email para validar cuota
            use_fallback=False  # No usar fallback para ver el error real
        )
        
        # Verificar si hubo error
        if result.error:
            # Detectar errores específicos de cuota/créditos
            error_lower = result.error.lower()
            if any(keyword in error_lower for keyword in ['quota', 'exceeded', '429', 'insufficient', 'credits', 'billing']):
                error_msg = f"❌ {provider.upper()}: Sin créditos o cuota agotada. Verifica tu plan y facturación."
            elif any(keyword in error_lower for keyword in ['401', 'invalid', 'api_key', 'authentication']):
                error_msg = f"❌ {provider.upper()}: API key inválida o no autorizada."
            elif any(keyword in error_lower for keyword in ['403', 'forbidden', 'permission']):
                error_msg = f"❌ {provider.upper()}: Acceso denegado. Verifica permisos de tu cuenta."
            elif any(keyword in error_lower for keyword in ['timeout', 'timed out']):
                error_msg = f"❌ {provider.upper()}: Tiempo de espera agotado. Intenta nuevamente."
            else:
                error_msg = f"❌ {provider.upper()}: {result.error}"
            
            return JsonResponse({
                'success': False,
                'error': error_msg,
                'provider': provider
            })
        
        # Verificar que realmente se generó contenido
        if not result.subject or not result.body:
            return JsonResponse({
                'success': False,
                'error': f"❌ {provider.upper()}: La API respondió pero no generó contenido válido.",
                'provider': provider
            })
        
        return JsonResponse({
            'success': True,
            'response': result.body[:200] + "..." if len(result.body) > 200 else result.body,
            'subject': result.subject,
            'provider': provider,
            'model': result.model,
            'tokens_used': result.tokens_used
        })
        
    except Exception as e:
        logger.error(f"Error probando proveedor IA: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@staff_member_required
def ai_admin_status_view(request):
    """Vista de estado de IA para administradores."""
    
    config = AIConfiguration.get_config()
    
    # Obtener estado detallado
    providers_status = {}
    
    # OpenAI
    openai_key = config.get_openai_key() if config.openai_enabled else None
    providers_status['openai'] = {
        'configured': bool(openai_key),
        'model': config.openai_model,
        'enabled': config.openai_enabled,
        'key_preview': f"{openai_key[:8]}..." if openai_key else "No configurado",
        'status': 'active' if (config.openai_enabled and openai_key) else 'inactive'
    }
    
    # Anthropic
    anthropic_key = config.get_anthropic_key() if config.anthropic_enabled else None
    providers_status['anthropic'] = {
        'configured': bool(anthropic_key),
        'model': config.anthropic_model,
        'enabled': config.anthropic_enabled,
        'key_preview': f"{anthropic_key[:12]}..." if anthropic_key else "No configurado",
        'status': 'active' if (config.anthropic_enabled and anthropic_key) else 'inactive'
    }
    
    context = {
        'config': config,
        'providers_status': providers_status,
        'available_providers': config.get_available_providers(),
        'is_configured': config.is_configured(),
        'default_provider': config.default_provider,
    }
    
    return render(request, 'matching/ai_admin_status.html', context)


@staff_member_required
@require_http_methods(["GET"])
def get_available_models(request):
    """
    Consulta los modelos disponibles en OpenAI y Anthropic.
    Retorna JSON con los modelos que el usuario puede usar.
    """
    try:
        config = AIConfiguration.get_config()
        result = {
            'success': True,
            'openai': {'models': [], 'error': None},
            'anthropic': {'models': [], 'error': None}
        }
        
        # Consultar modelos de OpenAI
        if config.openai_api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=config.get_openai_key(), timeout=10)
                models_response = client.models.list()
                
                # Filtrar solo modelos de chat/completion relevantes
                chat_models = []
                for model in models_response.data:
                    model_id = model.id
                    # Filtrar solo modelos GPT relevantes
                    if any(prefix in model_id for prefix in ['gpt-3.5', 'gpt-4', 'gpt-4o']):
                        # Crear nombre legible
                        display_name = model_id
                        if 'gpt-3.5-turbo' in model_id:
                            display_name = f"GPT-3.5 Turbo ({model_id})"
                        elif 'gpt-4o-mini' in model_id:
                            display_name = f"GPT-4o Mini ({model_id})"
                        elif 'gpt-4o' in model_id:
                            display_name = f"GPT-4o ({model_id})"
                        elif 'gpt-4-turbo' in model_id:
                            display_name = f"GPT-4 Turbo ({model_id})"
                        elif 'gpt-4' in model_id:
                            display_name = f"GPT-4 ({model_id})"
                        
                        chat_models.append({
                            'id': model_id,
                            'name': display_name,
                            'created': model.created if hasattr(model, 'created') else None
                        })
                
                # Ordenar por fecha de creación (más reciente primero)
                chat_models.sort(key=lambda x: x.get('created', 0) or 0, reverse=True)
                result['openai']['models'] = chat_models
                
                logger.info(f"✅ Modelos OpenAI disponibles: {len(chat_models)}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error consultando modelos OpenAI: {error_msg}")
                result['openai']['error'] = f"Error: {error_msg}"
        else:
            result['openai']['error'] = "API Key no configurada"
        
        # Consultar modelos de Anthropic
        if config.anthropic_api_key:
            try:
                from matching.utils.anthropic_model_finder import AnthropicModelFinder
                
                finder = AnthropicModelFinder(api_key=config.get_anthropic_key())
                available_models = finder.get_available_models()
                
                # Formatear modelos para el frontend
                anthropic_models = []
                for model_id in available_models:
                    # Crear nombre legible
                    display_name = model_id
                    if 'haiku' in model_id.lower():
                        display_name = f"Claude Haiku ({model_id})"
                    elif 'sonnet' in model_id.lower():
                        display_name = f"Claude Sonnet ({model_id})"
                    elif 'opus' in model_id.lower():
                        display_name = f"Claude Opus ({model_id})"
                    
                    anthropic_models.append({
                        'id': model_id,
                        'name': display_name
                    })
                
                result['anthropic']['models'] = anthropic_models
                logger.info(f"✅ Modelos Anthropic disponibles: {len(anthropic_models)}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Error consultando modelos Anthropic: {error_msg}")
                result['anthropic']['error'] = f"Error: {error_msg}"
        else:
            result['anthropic']['error'] = "API Key no configurada"
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"❌ Error general consultando modelos: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
