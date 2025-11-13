"""
Adapters personalizados para django-allauth que restringen el registro
a emails institucionales de @davinci.edu.ar
"""

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class RestrictedEmailAdapter(DefaultAccountAdapter):
    """Adapter que restringe el registro a emails @davinci.edu.ar"""

    ALLOWED_DOMAINS = ["davinci.edu.ar"]

    def clean_email(self, email):
        """Validar que el email sea de un dominio permitido."""
        email = super().clean_email(email)

        # Extraer el dominio del email
        domain = email.split("@")[-1].lower()

        if domain not in self.ALLOWED_DOMAINS:
            raise ValidationError(
                _("Solo se permiten cuentas con email institucional de @davinci.edu.ar")
            )

        return email

    def is_open_for_signup(self, request):
        """Permitir registro solo con emails válidos."""
        return True


class RestrictedSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adapter para cuentas sociales (Google OAuth) que restringe a @davinci.edu.ar"""

    ALLOWED_DOMAINS = ["davinci.edu.ar"]

    def pre_social_login(self, request, sociallogin):
        """Validar email antes de permitir login/registro con Google."""
        email = sociallogin.account.extra_data.get("email", "")

        if email:
            domain = email.split("@")[-1].lower()
            if domain not in self.ALLOWED_DOMAINS:
                # Usar el método de respuesta de allauth para rechazar el login
                from allauth.exceptions import ImmediateHttpResponse
                from django.http import HttpResponseRedirect
                from django.contrib import messages

                messages.error(
                    request,
                    "Solo se permiten cuentas con email institucional de @davinci.edu.ar",
                )
                # Redirigir al login con mensaje de error
                raise ImmediateHttpResponse(
                    HttpResponseRedirect("/matching/login/")
                )

    def is_open_for_signup(self, request, sociallogin):
        """Permitir registro solo con emails válidos."""
        email = sociallogin.account.extra_data.get("email", "")
        if email:
            domain = email.split("@")[-1].lower()
            return domain in self.ALLOWED_DOMAINS
        return False

