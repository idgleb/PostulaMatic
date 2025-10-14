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
                form.save()
                messages.success(
                    request, 
                    "✅ Configuración de IA actualizada correctamente"
                )
                return redirect('ai_admin_config')
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
        
        # Probar el proveedor
        result = ai_email_service.generate_email(
            prompt="Escribe 'Hola, soy PostulaMatic' en español",
            provider=provider
        )
        
        if result.error:
            return JsonResponse({
                'success': False,
                'error': result.error,
                'provider': provider
            })
        
        return JsonResponse({
            'success': True,
            'response': result.body,
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
