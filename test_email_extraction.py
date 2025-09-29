#!/usr/bin/env python3
"""
Script para probar la extracción de emails del HTML real.
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')
django.setup()

from matching.utils.email_decoder import get_email_from_job_html
from bs4 import BeautifulSoup
import re

def test_email_extraction_from_html():
    """Prueba la extracción de emails del HTML real."""
    
    # Leer el HTML de debug
    try:
        with open('/app/job_board_debug.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print("❌ Archivo job_board_debug.html no encontrado")
        return False
    
    print("🧪 Probando extracción de emails del HTML real...")
    
    # Parsear HTML con BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Buscar todos los enlaces de email protegido
    email_links = soup.find_all('a', href=lambda x: x and 'email-protection' in x)
    
    print(f"📧 Encontrados {len(email_links)} enlaces de email protegido")
    
    emails_found = []
    
    for i, link in enumerate(email_links):
        email_html = str(link)
        print(f"\n🔍 Email {i+1}:")
        print(f"HTML: {email_html}")
        
        # Decodificar email
        decoded_email = get_email_from_job_html(email_html)
        print(f"Decodificado: {decoded_email}")
        
        if decoded_email:
            emails_found.append(decoded_email)
    
    # También buscar emails en texto plano
    print(f"\n📝 Buscando emails en texto plano...")
    email_regex = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    text_emails = email_regex.findall(html_content)
    
    print(f"📧 Emails encontrados en texto: {len(text_emails)}")
    for email in set(text_emails):  # Eliminar duplicados
        print(f"  - {email}")
    
    total_emails = len(emails_found) + len(set(text_emails))
    print(f"\n✅ Total de emails únicos encontrados: {total_emails}")
    
    return total_emails > 0

if __name__ == "__main__":
    success = test_email_extraction_from_html()
    sys.exit(0 if success else 1)


