# game_logic.py — StrangerTEC Morse Translator
# Controla las dos rondas de juego desde el Pico.
#
# Modo Simple (DIP OFF):
#   El Pico elige la frase, la muestra en LEDs y buzzer.
#   Jugador A transmite desde el PC, jugador B desde la maqueta.
#
# Modo Escucha (DIP ON):
#   El PC envia la frase. La maqueta la presenta.
#   Jugador A responde en el PC, jugador B en la maqueta.
#
# Protocolo USB serie con el PC:
#   PICO->PC  LISTO | MODO:SIMPLE | MODO:ESCUCHA | MORSE:<f> | RESP:<r>
#   PC->PICO  FRASE:<f> | INICIO | PUNTAJE:<n>
# ============================================================

import time
from led_panel   import PanelLEDs
from morse_input import LectorMorse, CHAR_A_MORSE

FRASES = ["SOS","SI","NO","HOLA3","S+E","TEST","MORSE","TEC CR","8 PICO","ADIOS-1"]

UNIDAD_A_MS = 200   # 0.2 s (normal)
UNIDAD_B_MS = 300   # 0.3 s (lento)


def frase_aleatoria():
    return FRASES[time.ticks_ms() % len(FRASES)]


class Juego:

    def __init__(self, panel, morse, comm, modo_simple):
        self._panel       = panel
        self._morse       = morse
        self._comm        = comm
        self._modo_simple = modo_simple

    def iniciar(self):
        print("Juego iniciado")
        self._panel.animacion_inicio()
        while True:
            if self._modo_simple:
                self._ronda_simple()
            else:
                self._ronda_escucha()
            time.sleep(2)

    # ── Modo Simple ───────────────────────────────────────────

    def _ronda_simple(self):
        self._enviar("LISTO")
        self._enviar("MODO:SIMPLE")

        frase = frase_aleatoria()
        print("Frase:", frase)
        self._panel.mostrar_frase_leds(frase, self._morse.unidad_ms)
        self._enviar("MORSE:" + frase)

        # Esperar turno A
        if self._comm and self._comm.recibir(timeout_ms=60000) != "INICIO":
            print("Senal inesperada")

        # Turno B
        self._morse.reproducir_morse(frase, self._morse.unidad_ms)
        time.sleep(1)
        print("Jugador B: transmita en Morse")
        t0 = time.ticks_ms()
        resp = self._morse.leer_frase(max_chars=16)
        print("Transmitido:", resp, "en", time.ticks_diff(time.ticks_ms(), t0), "ms")

        self._enviar("RESP:" + resp)
        print("Resultado:", self._recibir(10000))
        self._parpadear(3)

    # ── Modo Escucha ──────────────────────────────────────────

    def _ronda_escucha(self):
        self._enviar("LISTO")
        self._enviar("MODO:ESCUCHA")

        datos = self._recibir(60000)
        frase = datos[6:] if datos.startswith("FRASE:") else frase_aleatoria()
        print("Frase:", frase)

        self._panel.mostrar_frase_leds(frase, self._morse.unidad_ms)
        time.sleep(1)
        self._morse.reproducir_morse(frase, self._morse.unidad_ms)
        time.sleep(1)

        # Esperar turno A
        if self._comm and self._comm.recibir(timeout_ms=60000) != "INICIO":
            print("Senal inesperada")

        # Turno B
        print("Jugador B: transmita en Morse")
        resp = self._morse.leer_frase(max_chars=16)
        print("Respuesta:", resp)

        self._enviar("RESP:" + resp)
        print("Puntaje:", self._recibir(10000))
        self._parpadear(3)

    # ── Utiles ────────────────────────────────────────────────

    def _enviar(self, msg):
        if self._comm:
            self._comm.enviar(msg)

    def _recibir(self, timeout_ms):
        return self._comm.recibir(timeout_ms=timeout_ms) if self._comm else ''

    def _parpadear(self, veces):
        for _ in range(veces):
            self._panel.animacion_inicio()
            time.sleep_ms(200)
