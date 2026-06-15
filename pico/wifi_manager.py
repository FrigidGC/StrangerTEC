# wifi_manager.py
# Este modulo ya no se usa en la version con USB serie.
# Se conserva como stub para evitar errores de importacion
# en caso de que algun archivo lo referencie.
# ============================================================


def conectar_wifi(timeout_seg=20):
    """Stub: WiFi eliminado. Devuelve False siempre."""
    print("wifi_manager: modulo desactivado (version USB serie)")
    return False


def obtener_ip():
    """Stub: WiFi eliminado. Devuelve '0.0.0.0'."""
    return '0.0.0.0'


def obtener_servidor():
    """Stub: WiFi eliminado. Devuelve valores por defecto."""
    return ('0.0.0.0', 8001)
