#!/usr/bin/env python3
"""Script para monitorear el progreso del procesamiento de CV en tiempo real."""

import subprocess
import re
import time
from datetime import datetime

def get_latest_progress():
    """Obtiene el último progreso del worker."""
    try:
        result = subprocess.run(
            ['docker-compose', 'logs', 'worker', '--tail=100'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        lines = result.stdout.split('\n')
        
        # Buscar la última página procesada
        last_page = None
        last_timestamp = None
        fallback_count = 0
        
        for line in reversed(lines):
            # Buscar patrón "PASO 2.X: Procesando página X"
            match = re.search(r'PASO 2\.(\d+): Procesando página (\d+)', line)
            if match and not last_page:
                last_page = int(match.group(2))
                # Extraer timestamp
                ts_match = re.search(r'\[([^\]]+)\]', line)
                if ts_match:
                    last_timestamp = ts_match.group(1)
            
            # Contar fallbacks
            if 'Fallback detectado' in line:
                fallback_count += 1
        
        # Buscar si ya completó
        completed = any('✅ CV procesado exitosamente' in line for line in lines[-50:])
        error = any('❌ Error procesando CV' in line for line in lines[-50:])
        
        return {
            'current_page': last_page,
            'total_pages': 27,
            'fallback_count': fallback_count,
            'timestamp': last_timestamp,
            'completed': completed,
            'error': error
        }
    except Exception as e:
        return {'error': str(e)}

def print_progress_bar(current, total, width=40):
    """Imprime una barra de progreso."""
    if not current or not total:
        return ""
    
    percentage = (current / total) * 100
    filled = int((current / total) * width)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percentage:.1f}%"

def main():
    """Monitorea el progreso del CV."""
    print("=" * 60)
    print("MONITOREANDO PROCESAMIENTO DE CV")
    print("=" * 60)
    print()
    
    last_page = None
    start_time = time.time()
    
    while True:
        progress = get_latest_progress()
        
        if 'error' in progress:
            print(f"[ERROR] Error obteniendo progreso: {progress['error']}")
            time.sleep(10)
            continue
        
        current_page = progress.get('current_page')
        total_pages = progress.get('total_pages', 27)
        
        # Limpiar pantalla
        print('\n' * 50)
        
        print("=" * 60)
        print(f"MONITOREO DE PROCESAMIENTO - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        print()
        
        if progress.get('completed'):
            elapsed = time.time() - start_time
            print("[OK] PROCESAMIENTO COMPLETADO!")
            print(f"Tiempo total: {elapsed/60:.1f} minutos")
            print()
            break
        
        if progress.get('error'):
            print("[ERROR] ERROR EN EL PROCESAMIENTO")
            print()
            break
        
        if current_page:
            print(f"Pagina actual: {current_page} de {total_pages}")
            print()
            print(print_progress_bar(current_page, total_pages))
            print()
            
            # Calcular tiempo estimado
            if current_page > 1:
                elapsed = time.time() - start_time
                avg_time_per_page = elapsed / current_page
                remaining_pages = total_pages - current_page
                estimated_remaining = avg_time_per_page * remaining_pages
                
                print(f"Tiempo transcurrido: {elapsed/60:.1f} min")
                print(f"Tiempo estimado restante: {estimated_remaining/60:.1f} min")
                print(f"Promedio por pagina: {avg_time_per_page:.1f} seg")
            
            print()
            print(f"Fallbacks a Anthropic: {progress.get('fallback_count', 0)}")
            
            if progress.get('timestamp'):
                print(f"Ultima actualizacion: {progress['timestamp']}")
            
            # Detectar si avanzó
            if last_page and current_page > last_page:
                print(f"[OK] Progreso: +{current_page - last_page} pagina(s)")
            
            last_page = current_page
        else:
            print("Esperando inicio del procesamiento...")
        
        print()
        print("=" * 60)
        print("Actualizando en 10 segundos... (Ctrl+C para salir)")
        
        time.sleep(10)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoreo detenido por el usuario")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")

