"""
Formularios para la aplicación matching.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile, UserCV, AIConfiguration


class UserRegistrationForm(UserCreationForm):
    """Formulario de registro de usuario."""
    
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CVUploadForm(forms.ModelForm):
    """Formulario para subir CV."""
    
    class Meta:
        model = UserCV
        fields = ['original_file']
        widgets = {
            'original_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx'
            })
        }
        labels = {
            'original_file': 'Archivo CV'
        }
        help_texts = {
            'original_file': 'Sube tu CV en formato PDF, DOC o DOCX'
        }


class UserProfileForm(forms.ModelForm):
    """Formulario para editar perfil de usuario."""
    
    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "match_threshold",
            "is_active",
            "smtp_host",
            "smtp_port",
            "smtp_use_tls",
            "smtp_use_ssl",
            "smtp_username",
            "smtp_password",
            "dv_username",
            "dv_password",
        ]
        widgets = {
            "match_threshold": forms.NumberInput(
                attrs={
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "class": "form-control",
                }
            ),
            "smtp_password": forms.PasswordInput(
                attrs={
                    "placeholder": "Contraseña SMTP",
                    "autocomplete": "new-password",
                    "spellcheck": "false",
                    "class": "form-control",
                }
            ),
            "dv_password": forms.PasswordInput(
                attrs={
                    "placeholder": "Contraseña INTRANET DAVINCI",
                    "autocomplete": "new-password",
                    "spellcheck": "false",
                    "class": "form-control",
                }
            ),
        }


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
            if field_name not in self.Meta.widgets:
                field.widget.attrs.update({"class": "form-control"})


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
            "dv_username": "Usuario INTRANET DAVINCI",
            "dv_password": "Contraseña INTRANET DAVINCI",
        }
        help_texts = {
            "dv_username": "Tu usuario para acceder al portal de estudiantes",
            "dv_password": "Tu contraseña para acceder al portal de estudiantes",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clases CSS a todos los campos
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets:
                field.widget.attrs.update({"class": "form-control"})


class MatchingConfigForm(forms.ModelForm):
    """Formulario para configuración de matching."""

    class Meta:
        model = UserProfile
        fields = ["match_threshold", "is_active"]
        widgets = {
            "match_threshold": forms.NumberInput(
                attrs={
                    "min": 0,
                    "max": 100,
                    "step": 1,
                    "class": "form-control",
                    "required": True,
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }
        labels = {
            "match_threshold": "Umbral de Coincidencia (%)",
            "is_active": "Aplicación Automática",
        }
        help_texts = {
            "match_threshold": "Porcentaje mínimo de coincidencia para aplicar automáticamente (0-100)",
            "is_active": "Habilitar aplicación automática cuando se supere el umbral",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clases CSS a todos los campos
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets:
                field.widget.attrs.update({"class": "form-control"})

    def clean_match_threshold(self):
        threshold = self.cleaned_data.get("match_threshold")
        if threshold is not None and (threshold < 0 or threshold > 100):
            raise forms.ValidationError(
                "El umbral debe estar entre 0 y 100"
            )
        return threshold


class EmailConfigForm(forms.ModelForm):
    """Formulario para configuración de email."""

    class Meta:
        model = UserProfile
        fields = ["daily_limit", "min_pause_seconds", "max_pause_seconds"]
        widgets = {
            "daily_limit": forms.NumberInput(attrs={"class": "form-control"}),
            "min_pause_seconds": forms.NumberInput(attrs={"class": "form-control"}),
            "max_pause_seconds": forms.NumberInput(attrs={"class": "form-control"}),
        }
        labels = {
            "daily_limit": "Límite Diario de Emails",
            "min_pause_seconds": "Pausa Mínima (segundos)",
            "max_pause_seconds": "Pausa Máxima (segundos)",
        }
        help_texts = {
            "daily_limit": "Número máximo de emails que se pueden enviar por día",
            "min_pause_seconds": "Pausa mínima entre envíos de emails",
            "max_pause_seconds": "Pausa máxima entre envíos de emails",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplicar clases CSS a todos los campos
        for field_name, field in self.fields.items():
            if field_name not in self.Meta.widgets:
                field.widget.attrs.update({"class": "form-control"})


class AIConfigurationForm(forms.ModelForm):
    """Formulario para configuración de IA."""
    
    # Campos adicionales para las API keys (no se guardan en el modelo)
    openai_api_key_input = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'sk-...',
            'autocomplete': 'new-password'
        }),
        help_text="API Key de OpenAI (se encripta automáticamente)"
    )
    
    anthropic_api_key_input = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'sk-ant-...',
            'autocomplete': 'new-password'
        }),
        help_text="API Key de Anthropic (se encripta automáticamente)"
    )
    
    # Definir campos de selección explícitamente
    openai_model = forms.ChoiceField(
        choices=[],  # Se llena en __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'modern-select',
            'data-placeholder': 'Selecciona un modelo de OpenAI...'
        }),
        label='Modelo de OpenAI',
        help_text="Selecciona el modelo de OpenAI a utilizar"
    )
    
    anthropic_model = forms.ChoiceField(
        choices=[],  # Se llena en __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'modern-select',
            'data-placeholder': 'Selecciona un modelo de Anthropic...'
        }),
        label='Modelo de Anthropic',
        help_text="Selecciona el modelo de Anthropic a utilizar"
    )
    
    default_provider = forms.ChoiceField(
        choices=[],  # Se llena en __init__
        required=True,
        widget=forms.Select(attrs={
            'class': 'modern-select',
            'data-placeholder': 'Selecciona el proveedor por defecto...'
        }),
        label='Proveedor por Defecto',
        help_text="Proveedor de IA que se usará por defecto"
    )

    class Meta:
        model = AIConfiguration
        fields = [
            'openai_enabled',
            'anthropic_enabled',
        ]
        widgets = {
            'openai_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anthropic_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'openai_enabled': 'Habilitar OpenAI',
            'anthropic_enabled': 'Habilitar Anthropic',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Agregar opciones de modelos de OpenAI
        self.fields['openai_model'].choices = [
            ('', 'Selecciona un modelo...'),
            ('gpt-3.5-turbo', 'GPT-3.5 Turbo (Recomendado)'),
            ('gpt-4', 'GPT-4 (Mejor calidad, más caro)'),
            ('gpt-4-turbo', 'GPT-4 Turbo'),
            ('gpt-4o', 'GPT-4o (Más reciente)'),
        ]
        
        # Agregar opciones de modelos de Anthropic
        self.fields['anthropic_model'].choices = [
            ('', 'Selecciona un modelo...'),
            ('claude-3-haiku-20240307', 'Claude 3 Haiku (Rápido)'),
            ('claude-3-sonnet-20240229', 'Claude 3 Sonnet (Balanceado)'),
            ('claude-3-opus-20240229', 'Claude 3 Opus (Mejor calidad)'),
            ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet (Más reciente)'),
        ]
        
        # Agregar opciones de proveedor por defecto
        self.fields['default_provider'].choices = [
            ('openai', 'OpenAI'),
            ('anthropic', 'Anthropic'),
        ]
        
        # Hacer campos opcionales inicialmente
        self.fields['openai_model'].required = False
        self.fields['anthropic_model'].required = False
        
        # Si es una instancia existente, mostrar preview de las keys
        if self.instance.pk:
            if self.instance.openai_api_key:
                self.fields['openai_api_key_input'].help_text = "Deja vacío para mantener la clave actual"
            if self.instance.anthropic_api_key:
                self.fields['anthropic_api_key_input'].help_text = "Deja vacío para mantener la clave actual"
    
    def clean(self):
        """Validación personalizada del formulario."""
        cleaned_data = super().clean()
        
        openai_enabled = cleaned_data.get('openai_enabled', False)
        anthropic_enabled = cleaned_data.get('anthropic_enabled', False)
        
        # Si OpenAI está habilitado, validar que tenga modelo y API key
        if openai_enabled:
            if not cleaned_data.get('openai_model'):
                self.add_error('openai_model', 'Debes seleccionar un modelo si habilitas OpenAI.')
            if not cleaned_data.get('openai_api_key_input'):
                self.add_error('openai_api_key_input', 'Debes ingresar una API key si habilitas OpenAI.')
        
        # Si Anthropic está habilitado, validar que tenga modelo y API key
        if anthropic_enabled:
            if not cleaned_data.get('anthropic_model'):
                self.add_error('anthropic_model', 'Debes seleccionar un modelo si habilitas Anthropic.')
            if not cleaned_data.get('anthropic_api_key_input'):
                self.add_error('anthropic_api_key_input', 'Debes ingresar una API key si habilitas Anthropic.')
        
        # Validar que al menos un proveedor esté habilitado
        if not openai_enabled and not anthropic_enabled:
            raise forms.ValidationError('Debes habilitar al menos un proveedor de IA (OpenAI o Anthropic).')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Guarda la configuración y procesa las API keys."""
        instance = super().save(commit=False)
        
        # Procesar API keys si se proporcionaron
        if self.cleaned_data.get('openai_api_key_input'):
            instance.set_openai_key(self.cleaned_data['openai_api_key_input'])
        
        if self.cleaned_data.get('anthropic_api_key_input'):
            instance.set_anthropic_key(self.cleaned_data['anthropic_api_key_input'])
        
        if commit:
            instance.save()
        
        return instance