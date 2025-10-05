#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'postulamatic.settings')
django.setup()

from matching.models import UserProfile
from matching.utils.encryption import decrypt_credential

try:
    profile = UserProfile.objects.get(user__username='idgle2')
    print('SMTP Host:', profile.smtp_host)
    print('SMTP Port:', profile.smtp_port)
    print('SMTP User:', profile.smtp_user)
    try:
        password = decrypt_credential(profile.smtp_password)
        print('SMTP Password (decrypted):', '***' + password[-4:] if password else 'None')
    except Exception as e:
        print('Error decrypting password:', e)
        print('Raw password:', profile.smtp_password)
    
    # Test SMTP connection
    import smtplib
    from email.mime.text import MIMEText
    
    print('\nTesting SMTP connection...')
    server = smtplib.SMTP(profile.smtp_host, profile.smtp_port)
    server.starttls()
    server.login(profile.smtp_user, password)
    print('SMTP login successful!')
    server.quit()
    
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
