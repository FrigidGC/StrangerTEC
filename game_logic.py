# Implementa los dos modos de juego en el lado del Pico W.
#
# MODO TRANSMISION SIMPLE (DIP-switch OFF):
#   El Pico selecciona una frase y la presenta via LEDs y buzzer.
#   Turno A: jugador A ingresa desde el PC.
#   Turno B: jugador B transmite en Morse desde la maqueta.
#
# MODO ESCUCHA Y TRANSMISION (DIP-switch ON):
#   El PC envia una frase al Pico. La maqueta la presenta.
#   Turno A: jugador A la retransmite desde el teclado del PC.
#   Turno B: jugador B la retransmite en Morse desde la maqueta.
#
# Protocolo TCP (texto plano, terminado en \n):
#   PICO -> PC   "LISTO"           PICO -> PC   "MODO:SIMPLE"
#   PICO -> PC   "MODO:ESCUCHA"    PC   -> PICO "FRASE:<texto>"
#   PICO -> PC   "MORSE:<texto>"   PICO -> PC   "RESP:<texto>"
#   PC   -> PICO "PUNTAJE:<n>"     PC   -> PICO "INICIO"
# ============================================================

import time
from led_panel   import PanelLEDs
from morse_input import LectorMorse
from server_comm import ServerComm

FRASES = ["SOS","SI","NO","HOLA3","S+E","TEST","MORSE","TEC CR","8 PICO","ADIOS-1"]
UNIDAD_A_MS = 200   # unidad Morse en ms (nivel rapido)
UNIDAD_B_MS = 300   # unidad Morse en ms (nivel lento)


def seleccionar_frase():
    """Elige una frase usando ticks del sistema (sin importar random)."""
    return FRASES[time.ticks_ms() % len(FRASES)]


class Juego:
    """Controlador principal del juego en el lado del Pico."""

    def __init__(self, panel, morse, comm, modo_simple):
        self._panel  = panel         # instancia de PanelLEDs
        self._morse  = morse         # instancia de LectorMorse
        self._comm   = comm          # instancia de ServerComm
        self._simple = modo_simple   # True=Simple, False=Escucha

    # ── Helpers de comunicacion ───────────────────────────────

    def _tx(self, msg):
        """Envia un mensaje al PC via ServerComm."""
        self._comm.enviar(msg)

    def _rx(self, timeout_ms=120000):
        """Recibe un mensaje del PC con timeout."""
        return self._comm.recibir(timeout_ms=timeout_ms)

    # ── Bucle principal ──────────────────────────────────────

    def iniciar(self):
        """Arranca el bucle infinito de partidas."""
        print("--- Juego iniciado ---")
        self._panel.animacion_inicio()
        while True:
            if self._simple:
                self._ronda_simple()
            else:
                self._ronda_escucha()
            time.sleep(2)

    # ── Modo Transmision Simple ──────────────────────────────

    def _ronda_simple(self):
        """
        Paso 1: avisar modo. Mostrar frase en LEDs, enviar MORSE:.
        Paso 2: esperar INICIO (jugador A termino en el PC).
        Paso 3: reproducir frase en buzzer para jugador B.
        Paso 4: capturar Morse de B, enviar RESP:, recibir PUNTAJE:.
        """
        self._tx("LISTO")
        self._tx("MODO:SIMPLE")

        frase = seleccionar_frase()
        print("Frase:", frase)
        self._panel.mostrar_frase_leds(frase, self._morse.unidad_ms)
        self._tx("MORSE:" + frase)

        print("Esperando turno A...")
        if self._rx() != "INICIO":
            print("Timeout o senal inesperada")

        self._morse.reproducir_morse(frase, self._morse.unidad_ms)
        time.sleep(1)

        print("Transmita (jugador B):")
        resp = self._morse.leer_frase(max_chars=16)
        self._tx("RESP:" + resp)
        print("Puntaje:", self._rx(timeout_ms=10000))
        self._parpadear()

    # ── Modo Escucha y Transmision ───────────────────────────

    def _ronda_escucha(self):
        """
        Paso 1: avisar modo, recibir FRASE: del PC.
        Paso 2: presentar frase via LEDs y buzzer.
        Paso 3: esperar INICIO (jugador A termino en el PC).
        Paso 4: capturar Morse de B, enviar RESP:, recibir PUNTAJE:.
        """
        self._tx("LISTO")
        self._tx("MODO:ESCUCHA")

        datos = self._rx()
        frase = datos[6:] if datos.startswith("FRASE:") else seleccionar_frase()
        print("Frase:", frase)

        self._panel.mostrar_frase_leds(frase, self._morse.unidad_ms)
        time.sleep(1)
        self._morse.reproducir_morse(frase, self._morse.unidad_ms)
        time.sleep(1)

        print("Esperando turno A...")
        if self._rx() != "INICIO":
            print("Timeout o senal inesperada")

        print("Transmita (jugador B):")
        resp = self._morse.leer_frase(max_chars=16)
        self._tx("RESP:" + resp)
        print("Puntaje:", self._rx(timeout_ms=10000))
        self._parpadear()

    # ── Animacion fin de ronda ───────────────────────────────

    def _parpadear(self, veces=3):
        """Parpadea los LEDs para senalizar el fin de ronda."""
        for _ in range(veces):
            self._panel.animacion_inicio()
            time.sleep_ms(200)
