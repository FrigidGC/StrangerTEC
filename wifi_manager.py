# Conexion WiFi del Pico W.
# Basado en raspyConnection.py provisto por la catedra.
#
# CORRECCIONES:
#   - Se agrego feedback auditivo opcional via buzzer.
#   - Se usa un timeout explicito en lugar de un bucle infinito.
#   - Se imprime la IP asignada al conectar.
# ============================================================

import network
import time


SSID     = "Redmi"         # nombre de la red WiFi
PASSWORD = "ev5pm72kk"     # contrasena de la red WiFi


def conectar_wifi(timeout_seg=20, buzzer=None):
    """
    Conecta el Pico W a la red WiFi configurada.
    Parametros:
        timeout_seg : segundos maximos de espera (default 20).
        buzzer      : instancia de LectorMorse para feedback auditivo.
    Devuelve True si conecta, False si se agota el tiempo.
    """

    def _pip(hz, ms):
        if buzzer is None:
            return
        buzzer._buz.freq(hz)
        buzzer.buzzer_on()
        time.sleep_ms(ms)
        buzzer.buzzer_off()
        buzzer._buz.freq(buzzer.FREC_BUZZER)
        time.sleep_ms(40)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    # Si ya estaba conectado, desconectar primero para forzar reconexion limpia
    if wlan.isconnected():
        wlan.disconnect()
        time.sleep(1)

    print("Conectando a WiFi '{}'...".format(SSID))
    _pip(600, 60)   # pip inicio: intentando conectar
    wlan.connect(SSID, PASSWORD)

    for seg in range(timeout_seg):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("WiFi OK. IP: {}".format(ip))
            # Dos pips ascendentes: WiFi exitoso
            _pip(700, 80)
            _pip(1000, 120)
            return True
        print("Esperando WiFi... ({}/{})".format(seg + 1, timeout_seg))
        # Un pip grave por segundo mientras espera
        _pip(350, 50)
        time.sleep(1)

    print("Sin WiFi tras {} segundos".format(timeout_seg))
    # Tres pips graves: fallo WiFi
    for _ in range(3):
        _pip(220, 120)
    return False
