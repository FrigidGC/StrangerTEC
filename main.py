# Punto de entrada del sistema empotrado.
# Lee el DIP-switch, conecta WiFi, abre socket TCP y arranca el juego.
# Basado en raspyConnection.py provisto por la catedra.
#
# Pines:
#   GP26 --> CLK 74HC164      GP27 --> DATA 74HC164
#   GP13 --> Fila1 LEDs       GP14 --> Fila2 LEDs    GP15 --> Fila3 LEDs
#   GP16 --> Boton Morse S1   GP18 --> DIP-switch S2  GP5  --> Buzzer PWM
#
# DIP-switch S2: OFF=Transmision Simple  ON=Escucha y Transmision
#
# CAMBIOS respecto a la version anterior:
#   - Se pasa la instancia de LectorMorse a wifi_manager y ServerComm
#     para que puedan emitir feedback auditivo durante la conexion.
#   - Se usa el buzzer para indicar error fatal al usuario.
# ============================================================

import machine
import time

from led_panel    import PanelLEDs
from morse_input  import LectorMorse
from game_logic   import Juego, UNIDAD_A_MS
from wifi_manager import conectar_wifi
from server_comm  import ServerComm

# ── Pines ─────────────────────────────────────────────────────
PIN_CLK    = 26
PIN_DATA   = 27
PIN_FILA1  = 13
PIN_FILA2  = 14
PIN_FILA3  = 15
PIN_BOTON  = 16
PIN_DIP    = 18
PIN_BUZZER = 5


def _beep_error_fatal(morse):
    """Tres pips graves: error de inicio irrecuperable."""
    for _ in range(3):
        morse._buz.freq(220)
        morse.buzzer_on()
        time.sleep_ms(150)
        morse.buzzer_off()
        time.sleep_ms(100)
    morse._buz.freq(morse.FREC_BUZZER)


def main():
    print("--- StrangerTEC Morse Translator ---")

    # 1. Leer modo de juego desde el DIP-switch
    dip = machine.Pin(PIN_DIP, machine.Pin.IN, machine.Pin.PULL_DOWN)
    modo_simple = dip.value() == 0   # OFF=Simple, ON=Escucha
    print("Modo:", "Simple" if modo_simple else "Escucha")

    # 2. Inicializar hardware
    panel = PanelLEDs(PIN_CLK, PIN_DATA, PIN_FILA1, PIN_FILA2, PIN_FILA3)
    panel.apagar_todo()
    morse = LectorMorse(PIN_BOTON, PIN_BUZZER, UNIDAD_A_MS)

    # 3. Conectar WiFi — pasa el buzzer para feedback auditivo
    if not conectar_wifi(buzzer=morse):
        print("Sin WiFi: no se puede iniciar")
        _beep_error_fatal(morse)
        return

    # 4. Conectar al servidor PC via TCP — pasa el buzzer para feedback
    comm = ServerComm(buzzer=morse)
    if not comm.conectar():
        print("Sin TCP: no se puede iniciar")
        _beep_error_fatal(morse)
        return

    # 5. Iniciar el juego
    Juego(panel, morse, comm, modo_simple).iniciar()


main()
