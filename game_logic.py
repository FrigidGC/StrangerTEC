# Implementa los dos modos de juego:
#
# MODO TRANSMISION SIMPLE (DIP-switch OFF):
#   La maqueta (jugador B) selecciona y transmite un mensaje
#   en Morse al PC. El PC recibe, decodifica y califica segun
#   velocidad y precision de caracteres. Luego se cambia turno.
#
# MODO ESCUCHA Y TRANSMISION (DIP-switch ON):
#   El PC envia una frase aleatoria al Pico.
#   La maqueta la presenta via LEDs y buzzer.
#   El jugador B la retransmite en Morse desde la maqueta.
#   El jugador A la retransmite desde el teclado del PC.
#   Ambos reciben puntaje. Luego se cambia turno.
#
# Protocolo TCP (mensajes de texto plano):
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

import machine
import time
from led_panel   import PanelLEDs
from morse_input import LectorMorse, CHAR_A_MORSE

# Lista de frases del juego (minimo 10, maximo 16 caracteres)
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
UNIDAD_A_MS = 200  # Unidad A = 0.2 segundos
UNIDAD_B_MS = 300  # Unidad B = 0.3 segundos


def seleccionar_frase():
    """
    Elige una frase de la lista usando el tiempo del sistema
    como semilla (no se puede usar random en el Pico con las
    librerias permitidas del proyecto).
    """
    indice = time.ticks_ms() % len(FRASES)  # indice pseudo-aleatorio
    return FRASES[indice]


class Juego:
    """Controlador principal del juego en el lado del Pico."""

    def __init__(self, panel, morse, comm, led_estado, modo_simple):
        self._panel       = panel       # instancia de PanelLEDs
        self._morse       = morse       # instancia de LectorMorse
        self._comm        = comm        # instancia de ServerComm (puede ser None)
        self._led_estado  = led_estado  # LED indicador de estado (GPIO directo)
        self._modo_simple = modo_simple # True = Transmision Simple, False = Escucha

    # ── Bucle principal ──────────────────────────────────

    def iniciar(self):
        """Arranca el bucle de partidas."""
        print("--- Juego iniciado ---")
        self._panel.animacion_inicio()  # animacion de bienvenida

        while True:
            if self._modo_simple:
                self._ronda_transmision_simple()
            else:
                self._ronda_escucha_y_transmision()
            time.sleep(2)  # pausa breve entre rondas

    # ── Modo Transmision Simple ──────────────────────────

    def _ronda_transmision_simple(self):
        """
        El jugador B en la maqueta ve la frase, la aprende,
        y luego la transmite en Morse al PC.
        """
        # Informar al servidor el modo activo
        if self._comm:
            self._comm.enviar("LISTO")
            self._comm.enviar("MODO:SIMPLE")

        # Seleccionar una frase de la lista
        frase = seleccionar_frase()
        print("Frase seleccionada:", frase)

        # Mostrar la frase al jugador B en el panel LED
        # para que la memorice antes de transmitirla
        print("Mostrando frase al jugador B...")
        self._led_estado.on()  # encender LED de estado
        self._panel.mostrar_frase_leds(frase, self._morse.unidad_ms)
        self._led_estado.off()

        # Dar tiempo al jugador para prepararse (3 segundos)
        print("Preparate para transmitir...")
        time.sleep(3)

        # Enviar la frase al PC para que el servidor sepa cual es
        if self._comm:
            self._comm.enviar("MORSE:" + frase)
            # Esperar la senal de inicio del servidor
            respuesta = self._comm.recibir(timeout_ms=5000)
            if respuesta != "INICIO":
                print("No se recibio INICIO del servidor")

        # Jugador B transmite la frase en Morse con el boton
        print("Transmita ahora en Morse:")
        self._led_estado.on()
        t_inicio = time.ticks_ms()               # registrar tiempo de inicio
        transmitido = self._morse.leer_frase(max_chars=16)
        t_fin = time.ticks_ms()                  # registrar tiempo de fin
        self._led_estado.off()

        # Calcular tiempo empleado en segundos
        tiempo_ms = time.ticks_diff(t_fin, t_inicio)
        print("Transmitido:", transmitido, "en", tiempo_ms, "ms")

        # Enviar la respuesta del jugador al servidor
        if self._comm:
            self._comm.enviar("RESP:" + transmitido)
            # Esperar puntaje del servidor
            puntaje = self._comm.recibir(timeout_ms=5000)
            print("Resultado:", puntaje)

        # Reproducir la frase correcta en el buzzer como repaso
        self._morse.reproducir_morse(frase, self._morse.unidad_ms)

    # ── Modo Escucha y Transmision ───────────────────────

    def _ronda_escucha_y_transmision(self):
        """
        El Pico recibe una frase del PC, la presenta via LED
        y buzzer, y luego captura la respuesta del jugador B.
        """
        # Avisar al servidor que el Pico esta listo
        if self._comm:
            self._comm.enviar("LISTO")
            self._comm.enviar("MODO:ESCUCHA")

        # Esperar la frase del servidor
        frase = ""
        if self._comm:
            datos = self._comm.recibir(timeout_ms=15000)  # esperar hasta 15 s
            if datos and datos.startswith("FRASE:"):
                frase = datos[6:]  # extraer el texto despues de "FRASE:"
        if not frase:
            # Sin conexion o sin respuesta: usar frase local
            frase = seleccionar_frase()
        print("Frase recibida:", frase)

        # Presentar la frase al jugador B: primero LEDs, luego buzzer
        print("Presentando frase en LEDs...")
        self._led_estado.on()
        self._panel.mostrar_frase_leds(frase, self._morse.unidad_ms)
        self._led_estado.off()
        time.sleep(1)  # breve pausa entre LED y buzzer

        # Reproducir la frase en el buzzer
        print("Reproduciendo en buzzer...")
        self._led_estado.on()
        self._morse.reproducir_morse(frase, self._morse.unidad_ms)
        self._led_estado.off()
        time.sleep(1)  # pausa antes de capturar respuesta

        # Capturar la respuesta del jugador B en Morse
        print("Jugador B: ingrese en Morse ahora:")
        self._led_estado.on()
        respuesta = self._morse.leer_frase(max_chars=16)
        self._led_estado.off()
        print("Respuesta jugador B:", respuesta)

        # Enviar la respuesta al servidor para calificacion
        if self._comm:
            self._comm.enviar("RESP:" + respuesta)
            puntaje = self._comm.recibir(timeout_ms=5000)  # recibir puntaje
            print("Puntaje:", puntaje)

        # Parpadear LED de estado para indicar fin de turno
        self._parpadear(3)

    # ── Animaciones ──────────────────────────────────────

    def _parpadear(self, veces):
        """Parpadea el LED de estado el numero de veces indicado."""
        for _ in range(veces):
            self._led_estado.on()
            time.sleep_ms(200)
            self._led_estado.off()
            time.sleep_ms(200)
