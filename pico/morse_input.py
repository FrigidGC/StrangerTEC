# Lee el boton pulsador S1 e interpreta presiones como
# puntos o rayas del codigo Morse.
# Activa el buzzer durante toda la presion para que el
# jugador escuche la duracion de la senal que esta enviando.
#
# Temporalizacion Morse (configurable con unidad_ms):
#   Punto      = presion < 2 * unidad_ms
#   Raya       = presion >= 2 * unidad_ms
#   Fin letra  = silencio >= 3 * unidad_ms sin presionar
#   Fin frase  = silencio >= 7 * unidad_ms sin presionar
# ============================================================

import machine
import time

# Tabla Morse: secuencia de puntos y rayas --> caracter
MORSE_A_CHAR = {
    '.-':'A',   '-...':'B',  '-.-.':'C', '-..':'D',
    '.':'E',    '..-.':'F',  '--.':'G',  '....':'H',
    '..':'I',   '.---':'J',  '-.-':'K',  '.-..':'L',
    '--':'M',   '-.':'N',    '---':'O',  '.--.':'P',
    '--.-':'Q', '.-.':'R',   '...':'S',  '-':'T',
    '..-':'U',  '...-':'V',  '.--':'W',  '-..-':'X',
    '-.--':'Y', '--..':'Z',
    '.----':'1','..---':'2', '...--':'3','....-':'4',
    '.....':'5','-....':'6', '--...':'7','---..':'8',
    '----.':'9','-----':'0',
    '.-.-.' :'+',   # signo mas
    '-....-':'-',   # signo menos / guion
}

# Tabla inversa: caracter --> secuencia Morse
CHAR_A_MORSE = {v: k for k, v in MORSE_A_CHAR.items()}


class LectorMorse:
    """Lee el boton y decodifica Morse. Activa el buzzer como
    retroalimentacion auditiva durante la presion."""

    FREC_BUZZER = 200   # Hz - igual al SONALERT del diagrama
    DUTY        = 32768  # 50% ciclo de trabajo (PWM 16 bits)

    def __init__(self, pin_boton, pin_buzzer, unidad_ms=200):
        # Boton con resistencia pull-down interna del Pico
        self._btn = machine.Pin(pin_boton, machine.Pin.IN,
                                machine.Pin.PULL_DOWN)
        # Buzzer controlado por PWM
        self._buz = machine.PWM(machine.Pin(pin_buzzer))
        self._buz.freq(self.FREC_BUZZER)
        self._buz.duty_u16(0)  # buzzer apagado al iniciar
        # Duracion de una unidad Morse en milisegundos
        self.unidad_ms = unidad_ms

    # ── Buzzer ──────────────────────────────────────────

    def buzzer_on(self):
        """Encender el buzzer."""
        self._buz.duty_u16(self.DUTY)

    def buzzer_off(self):
        """Apagar el buzzer."""
        self._buz.duty_u16(0)

    # ── Lectura de un simbolo ────────────────────────────

    def leer_simbolo(self, timeout_ms=None):
        """
        Espera que el jugador presione el boton y devuelve:
          '.'  si la presion fue corta (< 2 * unidad_ms)
          '-'  si la presion fue larga (>= 2 * unidad_ms)
          None si vencio el timeout sin presion
        """
        umbral = 2 * self.unidad_ms   # limite entre punto y raya
        t_inicio_espera = time.ticks_ms()

        # Esperar a que el boton sea presionado
        while self._btn.value() == 0:
            if timeout_ms is not None:
                if time.ticks_diff(time.ticks_ms(), t_inicio_espera) >= timeout_ms:
                    return None  # se acabo el tiempo de espera
            time.sleep_ms(5)  # revisar cada 5 ms

        # Boton presionado: encender buzzer y medir tiempo
        self.buzzer_on()
        t_presion = time.ticks_ms()
        while self._btn.value() == 1:
            time.sleep_ms(5)  # esperar a que se suelte

        # Boton soltado: apagar buzzer y calcular duracion
        self.buzzer_off()
        duracion = time.ticks_diff(time.ticks_ms(), t_presion)
        time.sleep_ms(20)  # anti-rebote

        # Decidir si fue punto o raya
        return '.' if duracion < umbral else '-'

    # ── Lectura de una letra ─────────────────────────────

    def leer_letra(self):
        """
        Acumula simbolos hasta detectar una pausa de 3 unidades
        (fin de caracter) y devuelve el caracter decodificado.
        Devuelve '' si no hubo ninguna presion (solo silencio).
        """
        pausa_letra = 3 * self.unidad_ms  # silencio = fin de letra
        secuencia = ""  # acumular puntos y rayas

        while True:
            simbolo = self.leer_simbolo(timeout_ms=pausa_letra)
            if simbolo is None:
                break  # silencio largo = fin del caracter
            secuencia += simbolo  # agregar punto o raya
            # Pausa minima de 1 unidad entre simbolos del mismo caracter
            time.sleep_ms(self.unidad_ms)

        if not secuencia:
            return ''  # no hubo ninguna presion

        # Buscar el caracter en la tabla Morse
        return MORSE_A_CHAR.get(secuencia, '?')

    # ── Lectura de una frase ─────────────────────────────

    def leer_frase(self, max_chars=16, on_letra=None):
        """
        Acumula letras hasta detectar un silencio de 7 unidades
        (fin de frase) o alcanzar el maximo de caracteres.

        Si se pasa on_letra (una funcion), se llama con cada
        caracter valido apenas se decodifica, ademas de
        agregarlo a la frase. Esto es lo que usa el modulo
        del incrementador en 5 para procesar cada digito al
        momento, sin esperar a que termine la frase completa.
        """
        frase = ""  # resultado acumulado

        while len(frase) < max_chars:
            letra = self.leer_letra()
            if letra == '':
                # Silencio: revisar si hay pausa larga de palabra
                time.sleep_ms(4 * self.unidad_ms)  # esperar 4 unidades mas
                if self._btn.value() == 0:
                    # Sigue sin presionar: fin de frase
                    break
                frase += ' '  # fue espacio entre palabras
            elif letra != '?':
                frase += letra  # agregar letra valida
                if on_letra:
                    on_letra(letra)

        return frase.strip()  # quitar espacios al inicio y fin

    # ── Reproduccion Morse del buzzer ────────────────────

    def reproducir_morse(self, frase, unidad_ms=None):
        """
        Hace sonar el buzzer con el codigo Morse de la frase
        para que el jugador escuche la senal.
        """
        u = unidad_ms or self.unidad_ms  # usar la unidad configurada
        pausa_sim  = u        # pausa entre simbolos del mismo caracter
        pausa_char = 3 * u    # pausa entre caracteres
        pausa_pal  = 7 * u    # pausa entre palabras

        for c in frase.upper():
            if c == ' ':
                time.sleep_ms(pausa_pal)  # silencio largo entre palabras
                continue
            if c not in CHAR_A_MORSE:
                continue  # caracter sin representacion Morse
            for simbolo in CHAR_A_MORSE[c]:
                # Encender buzzer la duracion correcta
                duracion = 3 * u if simbolo == '-' else u
                self.buzzer_on()
                time.sleep_ms(duracion)
                self.buzzer_off()
                time.sleep_ms(pausa_sim)  # pausa entre simbolos
            time.sleep_ms(pausa_char)  # pausa entre letras
