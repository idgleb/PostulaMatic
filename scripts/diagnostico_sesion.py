#!/usr/bin/env python3
"""
Script de diagnóstico para entender por qué las sesiones se marcan como inválidas.
"""

import json
import os
from datetime import datetime


def diagnosticar_sesion():
    """Diagnostica el archivo de sesión guardado."""

    session_file = "media/sessions/user_2_stealth_session.json"

    if not os.path.exists(session_file):
        print("ERROR: No existe archivo de sesion")
        return

    try:
        with open(session_file, "r", encoding="utf-8") as f:
            session_data = json.load(f)

        print("DIAGNOSTICO DE SESION")
        print("=" * 50)

        # Información básica
        timestamp = session_data.get("timestamp", "No disponible")
        print(f"Timestamp: {timestamp}")

        # Calcular antigüedad
        if timestamp != "No disponible":
            session_time = datetime.fromisoformat(timestamp)
            age_seconds = (datetime.now() - session_time).total_seconds()
            age_hours = age_seconds / 3600
            print(f"Antiguedad: {age_hours:.1f} horas ({age_seconds:.0f} segundos)")

            if age_seconds > 86400:
                print("ADVERTENCIA: SESION EXPIRADA (mas de 24 horas)")
            else:
                print("OK: Sesion dentro del tiempo valido")

        # Información de cookies
        cookies = session_data.get("cookies", [])
        print(f"Total de cookies: {len(cookies)}")

        if cookies:
            print("\nDETALLE DE COOKIES:")
            for i, cookie in enumerate(cookies, 1):
                name = cookie.get("name", "Sin nombre")
                domain = cookie.get("domain", "Sin dominio")
                path = cookie.get("path", "Sin path")
                secure = cookie.get("secure", False)
                http_only = cookie.get("httpOnly", False)

                print(f"  {i}. {name}")
                print(f"     Dominio: {domain}")
                print(f"     Path: {path}")
                print(f"     Secure: {secure}")
                print(f"     HttpOnly: {http_only}")
                print()

        # Verificar si hay cookies críticas
        cookie_names = [c.get("name", "") for c in cookies]
        critical_cookies = ["PHPSESSID", "cf_clearance", "session_id"]

        print("COOKIES CRITICAS:")
        for critical in critical_cookies:
            if critical in cookie_names:
                print(f"  OK {critical} - PRESENTE")
            else:
                print(f"  ERROR {critical} - AUSENTE")

        print("\nPOSIBLES CAUSAS DE 'SESION INVALIDA':")
        print("1. Cookies expiradas en el servidor")
        print("2. Dominio de cookies incorrecto")
        print("3. Cookies de Cloudflare (cf_clearance) expiradas")
        print("4. Sesion PHP (PHPSESSID) expirada")
        print("5. Cambios en la estructura del sitio")

    except Exception as e:
        print(f"ERROR leyendo sesion: {e}")


if __name__ == "__main__":
    diagnosticar_sesion()
