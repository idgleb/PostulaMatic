"""
Vistas para probar la integración con proveedores de IA.
"""

import json
import logging
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.conf import settings
import os

from matching.services.ai_service import ai_email_service

logger = logging.getLogger(__name__)


@login_required


@login_required
@require_http_methods(["POST"])
def test_ai_provider_view(request):
    """Vista AJAX para probar un proveedor específico de IA."""
    
    try:
        provider = request.POST.get('provider', 'openai')
        
        if provider not in ai_email_service.get_available_providers():
            return JsonResponse({
                'success': False,
                'message': f'Proveedor no disponible: {provider}'
            })
        
        # Verificar configuración
        if not ai_email_service.is_provider_configured(provider):
            return JsonResponse({
                'success': False,
                'message': f'Proveedor {provider} no está configurado. Verifica la API key.'
            })
        
        # Datos de prueba
        job_description = """
        Estamos buscando un Desarrollador Python con experiencia en Django.
        
        Requisitos:
        - 3+ años de experiencia en Python
        - Conocimiento en Django, PostgreSQL
        - Experiencia con APIs REST
        - Trabajo remoto disponible
        """
        
        cv_skills = {
            'skills': ['Python', 'Django', 'PostgreSQL', 'REST APIs', 'JavaScript'],
            'experience_years': 4,
            'experience_summary': 'Desarrollador Python',
            'education': 'Universidad de Buenos Aires - Ingeniería en Sistemas',
            'projects': ['Sistema de gestión de inventario', 'API REST para e-commerce']
        }
        
        user_profile = {
            'display_name': request.user.first_name or request.user.username,
            'email': request.user.email
        }
        
        # Generar email de prueba
        result = ai_email_service.generate_email(
            job_description=job_description,
            cv_skills=cv_skills,
            user_profile=user_profile,
            provider=provider
        )
        
        if result.error:
            return JsonResponse({
                'success': False,
                'message': f'Error generando email: {result.error}'
            })
        
        # Preparar respuesta
        response_data = {
            'success': True,
            'provider': result.provider,
            'model': result.model,
            'tokens_used': result.tokens_used,
            'email_data': {
                'subject': result.subject,
                'body': result.body
            }
        }
        
        logger.info(
            f"Prueba de IA exitosa para usuario {request.user.email}, "
            f"proveedor {provider}, tokens {result.tokens_used}"
        )
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error en prueba de IA: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error interno: {str(e)}'
        })


@login_required
@require_http_methods(["GET"])
def ai_integration_guide_view(request):
    """Vista con guía para configurar la integración con IA."""
    
    context = {
        'openai_configured': bool(
            os.getenv('OPENAI_API_KEY') and 
            os.getenv('OPENAI_API_KEY') != 'your-openai-api-key-here'
        ),
        'anthropic_configured': bool(
            os.getenv('ANTHROPIC_API_KEY') and 
            os.getenv('ANTHROPIC_API_KEY') != 'your-anthropic-api-key-here'
        )
    }
    
    return render(request, 'matching/ai_integration_guide.html', context)


@login_required
@require_http_methods(["POST"])
def update_ai_settings_view(request):
    """Vista para actualizar configuración de IA (simulado)."""
    
    try:
        # Por ahora solo simulamos la actualización
        # En el futuro se podría implementar guardado en base de datos
        
        provider = request.POST.get('default_provider')
        openai_model = request.POST.get('openai_model')
        anthropic_model = request.POST.get('anthropic_model')
        
        # Validar proveedor
        if provider not in ai_email_service.get_available_providers():
            return JsonResponse({
                'success': False,
                'message': f'Proveedor no válido: {provider}'
            })
        
        # Simular actualización
        logger.info(
            f"Configuración de IA actualizada por usuario {request.user.email}: "
            f"proveedor={provider}, openai_model={openai_model}, anthropic_model={anthropic_model}"
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Configuración actualizada correctamente (simulado)'
        })
        
    except Exception as e:
        logger.error(f"Error actualizando configuración de IA: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error interno: {str(e)}'
        })

