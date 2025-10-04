from django import forms
from django.core.exceptions import ValidationError

from .models import UserCV, UserProfile
from .utils.encryption import encrypt_credential


class UserProfileForm(forms.ModelForm):
    """Formulario para configurar perfil de usuario."""

    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "smtp_host",
            "smtp_port",
            "smtp_use_tls",
            "smtp_use_ssl",
            "smtp_username",
            "smtp_password",
            "dv_username",
            "dv_password",
            "match_threshold",
            "daily_limit",
            "min_pause_seconds",
            "max_pause_seconds",
        ]
        widgets = {
            "smtp_password": forms.PasswordInput(
                attrs={"placeholder": "Contraseña SMTP"}
            ),
            "dv_password": forms.PasswordInput(
                attrs={"placeholder": "Contraseña dvcarreras"}
            ),
            "smtp_port": forms.NumberInput(attrs={"min": 1, "max": 65535}),
            "match_threshold": forms.NumberInput(attrs={"min": 0, "max": 100}),
            "daily_limit": forms.NumberInput(attrs={"min": 1, "max": 100}),
            "min_pause_seconds": forms.NumberInput(attrs={"min": 1, "max": 300}),
            "max_pause_seconds": forms.NumberInput(attrs={"min": 1, "max": 600}),
        }
        help_texts = {
            "match_threshold": "Porcentaje mínimo de coincidencia para enviar email (0-100)",
            "daily_limit": "Máximo número de emails por día",
            "min_pause_seconds": "Pausa mínima entre envíos (segundos)",
            "max_pause_seconds": "Pausa máxima entre envíos (segundos)",
        }

    def clean(self):
        cleaned_data = super().clean()
        smtp_use_tls = cleaned_data.get("smtp_use_tls")
        smtp_use_ssl = cleaned_data.get("smtp_use_ssl")

        if smtp_use_tls and smtp_use_ssl:
            raise ValidationError(
                "No se puede usar TLS y SSL simultáneamente. Elige solo uno."
            )

        min_pause = cleaned_data.get("min_pause_seconds")
        max_pause = cleaned_data.get("max_pause_seconds")

        if min_pause and max_pause and min_pause > max_pause:
            raise ValidationError("La pausa mínima no puede ser mayor que la máxima.")

        return cleaned_data

    def clean_smtp_port(self):
        port = self.cleaned_data["smtp_port"]
        if port and (port < 1 or port > 65535):
            raise ValidationError("El puerto debe estar entre 1 y 65535.")
        return port


class CVUploadForm(forms.ModelForm):
    """Formulario para subir CV."""

    class Meta:
        model = UserCV
        fields = ["original_file"]
        widgets = {
            "original_file": forms.FileInput(
                attrs={"accept": ".pdf,.docx", "class": "form-control"}
            )
        }

    def clean_original_file(self):
        file = self.cleaned_data["original_file"]
        if file:
            # Validar tipo de archivo
            allowed_extensions = [".pdf", ".docx"]
            file_extension = file.name.lower().split(".")[-1]

            if f".{file_extension}" not in allowed_extensions:
                raise ValidationError("Solo se permiten archivos PDF y DOCX.")

            # Validar tamaño (máximo 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError("El archivo no puede ser mayor a 10MB.")

            # No filtrar por nombre de archivo - procesar todos los archivos

        return file

    def save(self, commit=True):
        """Guarda el CV normalmente."""
        instance = super().save(commit)
        return instance


class SMTPConfigForm(forms.ModelForm):
    """Formulario para configuración SMTP."""

    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "smtp_host",
            "smtp_port",
            "smtp_use_tls",
            "smtp_use_ssl",
            "smtp_username",
            "smtp_password",
        ]
        widgets = {
            "smtp_host": forms.TextInput(
                attrs={"class": "form-control", "required": True}
            ),
            "smtp_port": forms.NumberInput(
                attrs={
                    "min": 1,
                    "max": 65535,
                    "class": "form-control",
                    "required": True,
                }
            ),
            "smtp_username": forms.EmailInput(
                attrs={"class": "form-control", "required": True}
            ),
            "smtp_password": forms.PasswordInput(
                attrs={
                    "placeholder": "Contraseña SMTP",
                    "autocomplete": "new-password",
                    "spellcheck": "false",
                    "class": "form-control",
                    "required": True,
                }
            ),
        }
        labels = {
            "smtp_password": "Contraseña SMTP",
        }
        help_texts = {
            "smtp_password": "Contraseña de tu cuenta de email SMTP",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clases CSS a todos los campos
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ == "CheckboxInput":
                field.widget.attrs["class"] = "form-check-input"
            else:
                field.widget.attrs["class"] = "form-control"

        # Configurar placeholder dinámico para contraseña
        if self.instance and self.instance.smtp_password:
            self.fields["smtp_password"].widget.attrs[
                "placeholder"
            ] = "•••••••• (contraseña guardada)"

    def clean_smtp_password(self):
        password = self.cleaned_data.get("smtp_password")
        if not password:
            raise ValidationError("La contraseña SMTP es obligatoria.")
        return password

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Manejar encriptación de contraseña SMTP
        smtp_password = self.cleaned_data.get("smtp_password")
        if smtp_password:
            # Encriptar nueva contraseña
            instance.smtp_password = encrypt_credential(smtp_password)
        elif self.instance and self.instance.smtp_password:
            # Mantener contraseña existente si no se proporciona una nueva
            instance.smtp_password = self.instance.smtp_password

        if commit:
            instance.save()
        return instance


class DVCredentialsForm(forms.ModelForm):
    """Formulario para credenciales INTRANET DAVINCI."""

    class Meta:
        model = UserProfile
        fields = ["dv_username", "dv_password"]
        widgets = {
            "dv_username": forms.TextInput(
                attrs={"class": "form-control", "required": True}
            ),
            "dv_password": forms.PasswordInput(
                attrs={
                    "placeholder": "Contraseña INTRANET DAVINCI",
                    "autocomplete": "new-password",
                    "spellcheck": "false",
                    "class": "form-control",
                    "required": True,
                }
            ),
        }
        labels = {
            "dv_password": "Contraseña INTRANET DAVINCI",
        }
        help_texts = {
            "dv_password": "Contraseña de tu cuenta de INTRANET DAVINCI",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clases CSS a todos los campos
        for field_name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"

        # Configurar placeholder dinámico para contraseña
        if self.instance and self.instance.dv_password:
            self.fields["dv_password"].widget.attrs[
                "placeholder"
            ] = "•••••••• (contraseña guardada)"

    def clean_dv_password(self):
        password = self.cleaned_data.get("dv_password")
        if not password:
            raise ValidationError("La contraseña INTRANET DAVINCI es obligatoria.")
        return password

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Manejar encriptación de credenciales DVCarreras
        dv_username = self.cleaned_data.get("dv_username")
        dv_password = self.cleaned_data.get("dv_password")

        if dv_username:
            # Establecer usuario (no encriptado)
            instance.dv_username = dv_username
        elif self.instance and self.instance.dv_username:
            # Mantener usuario existente si no se proporciona uno nuevo
            instance.dv_username = self.instance.dv_username

        if dv_password:
            # Encriptar nueva contraseña
            instance.dv_password = encrypt_credential(dv_password)
        elif self.instance and self.instance.dv_password:
            # Mantener contraseña existente si no se proporciona una nueva
            instance.dv_password = self.instance.dv_password

        # Resetear estado de conexión cuando se cambian las credenciales
        if dv_username or dv_password:
            instance.set_dv_connection_verified(False)

        if commit:
            instance.save()
        return instance


class MatchingConfigForm(forms.ModelForm):
    """Formulario para configuración de matching."""

    class Meta:
        model = UserProfile
        fields = ["match_threshold"]
        widgets = {
            "match_threshold": forms.NumberInput(
                attrs={
                    "type": "range",
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "class": "form-range",
                }
            ),
        }

    def clean_match_threshold(self):
        value = self.cleaned_data.get("match_threshold")
        if value is not None and (value < 0 or value > 100):
            raise ValidationError("El umbral debe estar entre 0 y 100.")
        return value
