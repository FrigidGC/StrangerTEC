# Implementa los dos modos de juego:
#
# MODO TRANSMISION SIMPLE (DIP-switch OFF):
#   Ambos jugadores reciben la misma frase y la transmiten en
#   Morse. La frase es seleccionada desde la maqueta (Pico).
#   Turno 1: jugador A ingresa desde el teclado del PC.
#   Turno 2: jugador B transmite desde la maqueta.
#   La maqueta presenta la frase mediante seniales luminosas
#   o sonoras segun el nivel configurado.
#   La aplicacion del PC califica velocidad y precision.
#
# MODO ESCUCHA Y TRANSMISION (DIP-switch ON):
#   El PC envia una frase aleatoria al Pico.
#   La maqueta la presenta via LEDs y buzzer.
#   Turno 1: jugador A la retransmite desde el teclado del PC.
#   Turno 2: jugador B la retransmite en Morse desde la maqueta.
#   Ambos reciben puntaje por precision.
#   Al finalizar ambos turnos se muestra el ganador de la ronda.
#
# Protocolo de mensajes (texto plano por USB serie):
#   PICO -> PC   "LISTO"              Pico listo para jugar
#   PICO -> PC   "MODO:SIMPLE"        Informa el modo activo
#   PICO -> PC   "MODO:ESCUCHA"       Informa el modo activo
#   PC   -> PICO "FRASE:<texto>"      PC envia la frase
#   PICO -> PC   "MORSE:<texto>"      Pico envia la frase seleccionada
#                                     para Modo Simple
#   PICO -> PC   "RESP:<texto>"       Respuesta del jugador B
#   PC   -> PICO "PUNTAJE:<n>"        Puntaje calculado por el PC
#   PC   -> PICO "INICIO"             Senial de inicio de transmision
# ============================================================

import time
from led_panel   import PanelLEDs
from morse_input import LectorMorse, CHAR_A_MORSE

# Lista de frases del juego
FRASES = [
    "SOS",
    "SI",
    "NO",
    "HOLA3",
    "S+E",
    "TEST",
    "MORSE",
    "TEC CR",
    "8 PICO",
    "ADIOS-1",
]

# Unidades de tiempo Morse
UNIDAD_A_MS = 200  # Unidad A = 0.2 segundos (nivel rapido)
UNIDAD_B_MS = 300  # Unidad B = 0.3 segundos (nivel lento)


def seleccionar_frase():
    """
    Elige una frase de la lista usando el tiempo del sistema
    como semilla pseudo-aleatoria (sin importar random).
    """
    indice = time.ticks_ms() % len(FRASES)
    return FRASES[indice]


class Juego:
    """Controlador principal del juego en el lado del Pico."""

    def __init__(self, panel, morse, comm, modo_simple):
        self._panel       = panel       # instancia de PanelLEDs
        self._morse       = morse       # instancia de LectorMorse
        self._comm        = comm        # instancia de ServerComm
        self._modo_simple = modo_simple # True = Transmision Simple, False = Escucha

    # ── Bucle principal ──────────────────────────────────────

    def iniciar(self):
        """Arranca el bucle de partidas (bucle infinito)."""
        print("--- Juego iniciado ---")
        self._panel.animacion_inicio()  # animacion de bienvenida

        while True:
            if self._modo_simple:
                self._ronda_transmision_simple()
            else:
                self._ronda_escucha_y_transmision()
            time.sleep(2)  # pausa breve entre rondas

    # ── Modo Transmision Simple ──────────────────────────────

    def _ronda_transmision_simple(self):
        """
        Ambos jugadores reciben la misma frase y la transmiten
        en Morse. Primero el jugador A desde el teclado del PC,
        luego el jugador B desde la maqueta.

        Paso 1: el Pico selecciona la frase y la informa al PC.
        Paso 2: esperar senal INICIO -> turno A en el PC.
        Paso 3: segunda senal INICIO -> turno B en la maqueta.
        Paso 4: el Pico envia RESP:<texto> al PC para calificacion.
        Paso 5: el PC devuelve PUNTAJE:<n> al Pico.
        """
        # Informar al servidor el modo activo
        if self._comm:
            self._comm.enviar("LISTO")
            self._comm.enviar("MODO:SIMPLE")

        # Seleccionar una frase de la lista
        frase = seleccionar_frase()
        print("Frase seleccionada:", frase)

        # Mostrar la frase al jugador B en el panel LED
        # para que la conozca antes de su turno de transmision
        print("Mostrando frase en LEDs...")
        self._panel.mostrar_frase_leds(frase, self._morse.unidad_ms)

        # Informar la frase al servidor PC
        if self._comm:
            self._comm.enviar("MORSE:" + frase)

        # Esperar senal INICIO: el jugador A termino su turno en el PC
        # El servidor envia INICIO cuando A confirma su frase
        print("Esperando turno del jugador A en el PC...")
        if self._comm:
            respuesta = self._comm.recibir(timeout_ms=60000)  # hasta 60 s
            if respuesta != "INICIO":
                print("Senal inesperada:", respuesta)

        # Turno del jugador B: transmitir la frase en Morse
        # Reproducir la frase en el buzzer como referencia
        print("Reproduciendo frase en buzzer para jugador B...")
        self._morse.reproducir_morse(frase, self._morse.unidad_ms)
        time.sleep(1)

        print("Transmita ahora en Morse (jugador B):")
        t_inicio = time.ticks_ms()
        transmitido = self._morse.leer_frase(max_chars=16)
        t_fin = time.ticks_ms()
        tiempo_ms = time.ticks_diff(t_fin, t_inicio)
        print("Transmitido:", transmitido, "en", tiempo_ms, "ms")

        # Enviar la respuesta del jugador B al servidor
        if self._comm:
            self._comm.enviar("RESP:" + transmitido)
            # Esperar el puntaje calculado por el servidor
            puntaje = self._comm.recibir(timeout_ms=10000)
            print("Resultado:", puntaje)

        # Parpadear el panel para indicar fin de ronda
        self._parpadear_panel(3)

    # ── Modo Escucha y Transmision ───────────────────────────

    def _ronda_escucha_y_transmision(self):
        """
        El PC envia una frase aleatoria al Pico.
        La maqueta la presenta a ambos jugadores via LEDs y buzzer.
        Turno 1: jugador A responde desde el teclado del PC.
        Turno 2: jugador B responde desde la maqueta en Morse.
        Ambos reciben puntaje del servidor.

        Paso 1: avisar LISTO y MODO:ESCUCHA al servidor.
        Paso 2: recibir FRASE:<texto> del servidor.
        Paso 3: presentar la frase via LEDs y buzzer.
        Paso 4: esperar INICIO del servidor (A termino su turno).
        Paso 5: capturar la respuesta de B en Morse.
        Paso 6: enviar RESP:<texto> y recibir PUNTAJE:<n>.
        """
        # Avisar al servidor que el Pico esta listo
        if self._comm:
            self._comm.enviar("LISTO")
            self._comm.enviar("MODO:ESCUCHA")

        # Esperar la frase del servidor (hasta 60 segundos)
        frase = ""
        if self._comm:
            datos = self._comm.recibir(timeout_ms=60000)
            if datos and datos.startswith("FRASE:"):
                frase = datos[6:]  # extraer texto despues de "FRASE:"
        if not frase:
            # Sin respuesta del servidor: usar frase local de respaldo
            frase = seleccionar_frase()
        print("Frase recibida:", frase)

        # Presentar la frase via LEDs para que ambos jugadores la vean
        print("Presentando frase en LEDs...")
        self._panel.mostrar_frase_leds(frase, self._morse.unidad_ms)
        time.sleep(1)

        # Reproducir la frase en el buzzer (retroalimentacion sonora)
        print("Reproduciendo en buzzer...")
        self._morse.reproducir_morse(frase, self._morse.unidad_ms)
        time.sleep(1)

        # Esperar la senal INICIO del servidor (el jugador A termino)
        print("Esperando turno del jugador A en el PC...")
        if self._comm:
            senal = self._comm.recibir(timeout_ms=60000)
            if senal != "INICIO":
                print("Senal inesperada:", senal)

        # Turno del jugador B: capturar su respuesta en Morse
        print("Jugador B: ingrese en Morse ahora:")
        respuesta = self._morse.leer_frase(max_chars=16)
        print("Respuesta jugador B:", respuesta)

        # Enviar la respuesta al servidor para calificacion
        if self._comm:
            self._comm.enviar("RESP:" + respuesta)
            puntaje = self._comm.recibir(timeout_ms=10000)
            print("Puntaje:", puntaje)

        # Parpadear el panel para indicar fin de turno
        self._parpadear_panel(3)

    # ── Animaciones ──────────────────────────────────────────

    def _parpadear_panel(self, veces):
        """
        Apaga y enciende todos los LEDs del panel el numero
        de veces indicado para senializar el fin de ronda.
        """
        for _ in range(veces):
            self._panel.animacion_inicio()
            time.sleep_ms(200)
