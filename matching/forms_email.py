from django import forms
from django.core.exceptions import ValidationError
from .models import UserProfile


class EmailConfigForm(forms.ModelForm):
    """Formulario para configuración de envíos de emails."""
    
    class Meta:
        model = UserProfile
        fields = ['daily_limit', 'min_pause_seconds', 'max_pause_seconds']
        widgets = {
            'daily_limit': forms.NumberInput(attrs={
                'type': 'range',
                'min': 1,
                'max': 40,
                'step': 1,
                'class': 'form-range'
            }),
            'min_pause_seconds': forms.NumberInput(attrs={
                'type': 'range',
                'min': 5,
                'max': 90,
                'step': 5,
                'class': 'form-range'
            }),
            'max_pause_seconds': forms.NumberInput(attrs={
                'type': 'range',
                'min': 90,
                'max': 500,
                'step': 10,
                'class': 'form-range'
            }),
        }
    
    def clean_daily_limit(self):
        value = self.cleaned_data.get('daily_limit')
        if value is not None and (value < 1 or value > 40):
            raise ValidationError('El límite diario debe estar entre 1 y 40.')
        return value
    
    def clean_min_pause_seconds(self):
        value = self.cleaned_data.get('min_pause_seconds')
        if value is not None and (value < 5 or value > 90):
            raise ValidationError('La pausa mínima debe estar entre 5 y 90 segundos.')
        return value
    
    def clean_max_pause_seconds(self):
        value = self.cleaned_data.get('max_pause_seconds')
        if value is not None and (value < 90 or value > 500):
            raise ValidationError('La pausa máxima debe estar entre 90 y 500 segundos.')
        return value
    
    def clean(self):
        cleaned_data = super().clean()
        min_pause = cleaned_data.get('min_pause_seconds')
        max_pause = cleaned_data.get('max_pause_seconds')
        
        if min_pause and max_pause and min_pause > max_pause:
            raise ValidationError("La pausa mínima no puede ser mayor que la máxima.")
        
        return cleaned_data


