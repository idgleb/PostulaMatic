# 🔒 Política de Seguridad

## 🛡️ Versiones Soportadas

Actualmente soportamos las siguientes versiones con actualizaciones de seguridad:

| Versión | Soportada          |
| ------- | ------------------ |
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

---

## 🚨 Reportar una Vulnerabilidad

La seguridad de PostulaMatic es una prioridad. Si descubres una vulnerabilidad de seguridad, por favor:

### **NO** abras un issue público

En su lugar:

1. **Envía un email a:** security@postulamatic.app
2. **Incluye:**
   - Descripción detallada de la vulnerabilidad
   - Pasos para reproducir
   - Versión afectada
   - Impacto potencial
   - Sugerencias de mitigación (opcional)

### Tiempo de Respuesta

- **Primera respuesta:** 48 horas
- **Actualización inicial:** 7 días
- **Fix objetivo:** 30 días (dependiendo de la severidad)

### Proceso

1. **Confirmamos** la recepción del reporte
2. **Investigamos** y validamos la vulnerabilidad
3. **Desarrollamos** un fix
4. **Probamos** en entorno de staging
5. **Desplegamos** el patch
6. **Publicamos** un advisory de seguridad (con tu crédito si lo deseas)

---

## 🔐 Buenas Prácticas de Seguridad

### Para Usuarios

- ✅ **Mantén actualizada** tu instalación de PostulaMatic
- ✅ **Usa contraseñas fuertes** (mínimo 12 caracteres)
- ✅ **Habilita 2FA** en tu cuenta de Google OAuth
- ✅ **No compartas** tus credenciales SMTP o DV
- ✅ **Revisa regularmente** los logs de emails enviados
- ✅ **Configura límites** de envío diario razonables

### Para Desarrolladores

- ✅ **Nunca commitees** credenciales o API keys
- ✅ **Usa `.env`** para variables sensibles
- ✅ **Revisa dependencias** con `pip-audit` o `safety`
- ✅ **Valida inputs** tanto en frontend como backend
- ✅ **Usa parametrized queries** para prevenir SQL injection
- ✅ **Sanitiza outputs** para prevenir XSS
- ✅ **Implementa rate limiting** en endpoints críticos

---

## 🔒 Medidas de Seguridad Implementadas

### Encriptación

- ✅ **Credenciales SMTP** - Fernet (symmetric encryption)
- ✅ **Contraseñas DV** - Fernet (symmetric encryption)
- ✅ **API Keys de IA** - Fernet (symmetric encryption)
- ✅ **Passwords de usuarios** - Django's PBKDF2 (default)
- ✅ **HTTPS obligatorio** - TLS 1.2+ con Let's Encrypt

### Autenticación y Autorización

- ✅ **Django Auth** - Password hashing con PBKDF2
- ✅ **Google OAuth** - django-allauth
- ✅ **Restricción de dominios** - @davinci.edu.ar whitelist
- ✅ **CSRF protection** - Tokens en todos los formularios
- ✅ **Session security** - HttpOnly, Secure cookies

### Infraestructura

- ✅ **Nginx** - Reverse proxy con rate limiting
- ✅ **HSTS** - Strict-Transport-Security header
- ✅ **Docker** - Contenedores aislados
- ✅ **Secrets management** - Variables de entorno
- ✅ **Logs auditables** - Tracking de todas las acciones

### Rate Limiting

- ✅ **Scraping** - Lock global, 1 proceso a la vez
- ✅ **Email sending** - Pausas aleatorias (20-90 seg)
- ✅ **Límite diario** - Configurable por usuario (default: 20)
- ✅ **API endpoints** - Throttling en endpoints críticos

---

## 🔍 Auditorías de Seguridad

### Última Auditoría

- **Fecha:** Enero 2025
- **Alcance:** Código fuente, infraestructura, dependencias
- **Hallazgos:** 0 críticos, 0 altos, 2 medios (resueltos)
- **Próxima auditoría:** Julio 2025

### Dependencias

Monitoreamos continuamente nuestras dependencias con:

- **Dependabot** (GitHub) - Alertas automáticas
- **pip-audit** - Vulnerabilidades en paquetes Python
- **Safety** - Check de base de datos de vulnerabilidades

```bash
# Verificar vulnerabilidades en dependencias
pip install pip-audit
pip-audit

# O con safety
pip install safety
safety check
```

---

## 📋 Checklist de Seguridad para Deployment

Antes de desplegar a producción:

- [ ] Variables sensibles en `.env` (no en código)
- [ ] `DEBUG=False` en producción
- [ ] `SECRET_KEY` aleatoria y segura (50+ caracteres)
- [ ] `ALLOWED_HOSTS` configurado correctamente
- [ ] HTTPS habilitado con certificado válido
- [ ] HSTS header activo
- [ ] Firewall configurado (solo puertos 80, 443, 22)
- [ ] SSH con key-based auth (no passwords)
- [ ] Backups automáticos de BD
- [ ] Logs rotados y monitoreados
- [ ] Dependencias actualizadas
- [ ] Tests de seguridad ejecutados

---

## 🚫 Vulnerabilidades Conocidas (Historial)

### CVE-YYYY-XXXX (Ejemplo)
**Severidad:** Baja  
**Afecta:** v1.0.0 - v1.0.5  
**Descripción:** [Descripción]  
**Fix:** Actualizar a v1.0.6+  
**Workaround:** [Si aplica]  

_Actualmente no hay vulnerabilidades conocidas abiertas._

---

## 📚 Recursos Adicionales

### Documentación de Seguridad

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Django Security](https://docs.djangoproject.com/en/5.2/topics/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

### Herramientas Recomendadas

- **Bandit** - Security linter for Python
- **Safety** - Check dependencies for vulnerabilities
- **pip-audit** - Audit Python packages
- **OWASP ZAP** - Web app security scanner

```bash
# Instalar herramientas de seguridad
pip install bandit safety pip-audit

# Ejecutar análisis de seguridad
bandit -r matching/ postulamatic/
safety check
pip-audit
```

---

## 🏆 Hall of Fame

Agradecemos a los investigadores de seguridad que han reportado vulnerabilidades de forma responsable:

- _[Pendiente de primeros reportes]_

---

## 📞 Contacto

- **Security Email:** security@postulamatic.app
- **PGP Key:** [Pendiente]
- **Response Time:** 48 horas

---

<div align="center">

**🔒 La seguridad es responsabilidad de todos. Gracias por ayudarnos a mantener PostulaMatic seguro. 🔒**

[🏠 Volver al README](README.md)

</div>

