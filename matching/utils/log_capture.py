import logging
from typing import Any, Dict, List


class LogCapture:
    """Captura logs y los almacena en memoria para enviar al frontend."""

    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
        self.original_handlers = []

    def add_log(self, level: str, message: str, step: str = ""):
        """Agrega un log a la colección."""
        self.logs.append(
            {
                "level": level,
                "message": message,
                "step": step,
                "timestamp": self._get_timestamp(),
            }
        )

    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def get_logs(self) -> List[Dict[str, Any]]:
        """Retorna todos los logs capturados."""
        return self.logs.copy()

    def clear_logs(self):
        """Limpia todos los logs."""
        self.logs.clear()

    def get_logs_as_string(self) -> str:
        """Retorna logs como string formateado."""
        if not self.logs:
            return "No hay logs disponibles"

        formatted_logs = []
        for log in self.logs:
            timestamp = log["timestamp"]
            level = log["level"]
            step = f"[{log['step']}] " if log["step"] else ""
            message = log["message"]
            formatted_logs.append(f"{timestamp} {level} {step}{message}")

        return "\n".join(formatted_logs)


# Instancia global para capturar logs
log_capture = LogCapture()


class LogCaptureHandler(logging.Handler):
    """Handler personalizado que captura logs y los envía a LogCapture."""

    def __init__(self, log_capture_instance: LogCapture):
        super().__init__()
        self.log_capture = log_capture_instance

    def emit(self, record):
        """Captura el log y lo envía a LogCapture."""
        try:
            # Extraer información del log
            level = record.levelname
            message = record.getMessage()

            # Determinar el paso basado en el mensaje
            step = ""
            if "PASO 1" in message:
                step = "PDF→Imágenes"
            elif "PASO 2" in message:
                step = "IA Visión"
            elif "PASO 3" in message:
                step = "Combinar"
            elif "PASO 4" in message:
                step = "Post-procesar"
            elif "OPENAI" in message:
                step = "OpenAI"
            elif "ANTHROPIC" in message:
                step = "Anthropic"
            elif "ABRIENDO PDF" in message:
                step = "PDF"
            elif "CREANDO PROMPT" in message:
                step = "Prompt"

            # Agregar a la captura
            self.log_capture.add_log(level, message, step)

        except Exception:
            # Si hay error capturando, no hacer nada para evitar loops
            pass


def setup_log_capture():
    """Configura la captura de logs."""
    # Limpiar logs anteriores
    log_capture.clear_logs()

    # Crear handler personalizado
    handler = LogCaptureHandler(log_capture)
    handler.setLevel(logging.INFO)

    # Agregar al logger principal
    logger = logging.getLogger()
    logger.addHandler(handler)

    return log_capture


def cleanup_log_capture():
    """Limpia la captura de logs."""
    logger = logging.getLogger()
    for handler in logger.handlers[:]:
        if isinstance(handler, LogCaptureHandler):
            logger.removeHandler(handler)
