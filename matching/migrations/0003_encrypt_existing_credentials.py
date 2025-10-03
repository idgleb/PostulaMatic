# Generated manually for encrypting existing credentials

from django.db import migrations


def encrypt_existing_credentials(apps, schema_editor):
    """Encripta las credenciales existentes en la base de datos."""
    try:
        from matching.utils.encryption_temp import encrypt_credential, is_credential_encrypted
        
        UserProfile = apps.get_model('matching', 'UserProfile')
        
        profiles = UserProfile.objects.all()
        encrypted_count = 0
        
        for profile in profiles:
            updated = False
            
            # Encriptar contraseña SMTP si existe y no está encriptada
            if profile.smtp_password and not is_credential_encrypted(profile.smtp_password):
                profile.smtp_password = encrypt_credential(profile.smtp_password)
                updated = True
            
            # El usuario DVCarreras no se encripta (es público)
            
            # Encriptar contraseña DVCarreras si existe y no está encriptada
            if profile.dv_password and not is_credential_encrypted(profile.dv_password):
                profile.dv_password = encrypt_credential(profile.dv_password)
                updated = True
            
            if updated:
                profile.save(update_fields=['smtp_password', 'dv_username', 'dv_password'])
                encrypted_count += 1
        
        print(f"Migración completada: {encrypted_count} perfiles encriptados")
        
    except ImportError:
        print("Advertencia: No se pudo importar el módulo de encriptación. Las credenciales permanecen sin encriptar.")
    except Exception as e:
        print(f"Error durante la encriptación: {e}")


def decrypt_existing_credentials(apps, schema_editor):
    """Desencripta las credenciales (para rollback)."""
    try:
        from matching.utils.encryption_temp import decrypt_credential, is_credential_encrypted
        
        UserProfile = apps.get_model('matching', 'UserProfile')
        
        profiles = UserProfile.objects.all()
        decrypted_count = 0
        
        for profile in profiles:
            updated = False
            
            # Desencriptar contraseña SMTP si está encriptada
            if profile.smtp_password and is_credential_encrypted(profile.smtp_password):
                profile.smtp_password = decrypt_credential(profile.smtp_password)
                updated = True
            
            # El usuario DVCarreras no se encripta (es público)
            
            # Desencriptar contraseña DVCarreras si está encriptada
            if profile.dv_password and is_credential_encrypted(profile.dv_password):
                profile.dv_password = decrypt_credential(profile.dv_password)
                updated = True
            
            if updated:
                profile.save(update_fields=['smtp_password', 'dv_username', 'dv_password'])
                decrypted_count += 1
        
        print(f"Rollback completado: {decrypted_count} perfiles desencriptados")
        
    except ImportError:
        print("Advertencia: No se pudo importar el módulo de encriptación. No se pudo hacer rollback.")
    except Exception as e:
        print(f"Error durante el rollback: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('matching', '0002_jobposting_scrapinglog_usercv_matchscore_and_more'),
    ]

    operations = [
        migrations.RunPython(
            encrypt_existing_credentials,
            reverse_code=decrypt_existing_credentials,
        ),
    ]
