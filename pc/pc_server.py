# Servidor PC del juego StrangerTEC Morse Translator.
#
# Comunicacion via USB serie usando open() incorporado de Python.
# No requiere librerias externas ni pyserial.
#
# Modos de juego:
#
# MODO TRANSMISION SIMPLE (DIP OFF):
#   1. El Pico selecciona una frase y la envia ("MORSE:<frase>")
#   2. Jugador A ingresa Morse desde el teclado del PC
#   3. Al confirmar, se envia "INICIO" al Pico para que B transmita
#   4. El Pico envia la respuesta de B ("RESP:<texto>")
#   5. Ambos reciben puntaje; se muestra ganador de la ronda
#
# MODO ESCUCHA Y TRANSMISION (DIP ON):
#   1. El servidor elige una frase aleatoria y la envia al Pico
#   2. La maqueta la presenta via LEDs/buzzer
#   3. Jugador A responde en Morse desde el teclado del PC
#   4. Al confirmar frase de A, se habilita el turno de B
#   5. El jugador B responde en Morse desde la maqueta
#   6. Ambos reciben puntaje; se muestra ganador de la ronda
#
# Protocolo de mensajes (texto plano, terminados en \n):
#   PICO -> PC   "LISTO"              Pico listo para jugar
#   PICO -> PC   "MODO:SIMPLE"        Informa el modo activo
#   PICO -> PC   "MODO:ESCUCHA"       Informa el modo activo
#   PC   -> PICO "FRASE:<texto>"      PC envia la frase
#   PICO -> PC   "MORSE:<texto>"      Pico envia frase (Modo Simple)
#   PICO -> PC   "RESP:<texto>"       Respuesta del jugador B
#   PC   -> PICO "PUNTAJE:<n>"        Puntaje calculado por el PC
#   PC   -> PICO "INICIO"             Senal de inicio de transmision
# ============================================================

import time
import random
import threading
import tkinter as tk

# ── Configuracion del puerto serie ───────────────────────────
BAUDRATE = 115200


def _detectar_puerto_pico():
    """
    Detecta automaticamente el puerto USB donde esta conectado el Pico W.
    - Windows: escanea el registro buscando puertos COM activos.
    - Linux/Mac: busca /dev/ttyACM* y /dev/cu.usbmodem*.
    Devuelve el nombre del primer puerto encontrado, o None si no hay ninguno.
    """
    import sys as _sys
    if _sys.platform.startswith('win'):
        import winreg
        puertos = []
        try:
            clave = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DEVICEMAP\SERIALCOMM"
            )
            i = 0
            while True:
                try:
                    _, valor, _ = winreg.EnumValue(clave, i)
                    puertos.append(valor)
                    i += 1
                except OSError:
                    break
        except OSError:
            pass
        # Intentar abrir cada puerto para ver si el Pico responde
        # Preferir puertos con numero alto (los recien conectados suelen ser COM5+)
        for p in sorted(puertos, reverse=True):
            return p   # devolver el primero disponible
        return None
    else:
        import glob
        for patron in ['/dev/ttyACM*', '/dev/ttyUSB*', '/dev/cu.usbmodem*']:
            encontrados = glob.glob(patron)
            if encontrados:
                return sorted(encontrados)[0]
        return None

# ── Frases del juego (sincronizadas con game_logic.py del Pico) ──
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

# ── Tabla Morse (caracter --> secuencia de puntos y rayas) ───
MORSE = {
    'A': '.-',    'B': '-...',  'C': '-.-.',  'D': '-..',
    'E': '.',     'F': '..-.',  'G': '--.',   'H': '....',
    'I': '..',    'J': '.---',  'K': '-.-',   'L': '.-..',
    'M': '--',    'N': '-.',    'O': '---',   'P': '.--.',
    'Q': '--.-',  'R': '.-.',   'S': '...',   'T': '-',
    'U': '..-',   'V': '...-',  'W': '.--',   'X': '-..-',
    'Y': '-.--',  'Z': '--..',
    '0': '-----', '1': '.----', '2': '..---', '3': '...--',
    '4': '....-', '5': '.....', '6': '-....', '7': '--...',
    '8': '---..',  '9': '----.',
    '+': '.-.-.', '-': '-....-',
}

# Tabla inversa: secuencia --> caracter
MORSE_INV = {v: k for k, v in MORSE.items()}

# Velocidades de transmision (ms promedio por caracter)
VELOCIDAD = {
    "Rapido": (0,      2000),
    "Medio":  (2000,   4000),
    "Lento":  (4000, 999999),
}
BONUS_VELOCIDAD = {"Rapido": 5, "Medio": 3, "Lento": 1}

# ── Colores tema Stranger Things ─────────────────────────────
FONDO    = "Black"
AMARILLO = "Yellow"
ROJO     = "Red"
VERDE    = "Green"
GRIS     = "Grey"
BLANCO   = "White"
AZUL     = "#4fc3f7"

# Filas del panel de letras (igual que en la maqueta fisica)
FILA1 = list("ACEGIKMOQSUWY")
FILA2 = list("BDFHJLNPRTVXZ")
FILA3 = list("0123456789-+")


# ============================================================
# Audio: tonos agradables con tkinter (sin librerias externas)
# Usa el modulo winsound en Windows o /dev/audio en Linux.
# Para maxima compatibilidad se genera una onda sin en un hilo.
# ============================================================

def _tono(frecuencia, duracion_ms):
    """
    Reproduce un tono de la frecuencia indicada durante duracion_ms ms.
    Usa winsound en Windows; en Linux/Mac usa el terminal bell como
    respaldo silencioso (no interrumpe el flujo del juego).
    """
    try:
        import winsound
        winsound.Beep(int(frecuencia), int(duracion_ms))
    except Exception:
        # En Linux/Mac: usar tkinter bell (clic del sistema)
        pass


def sonido_punto():
    """Tono corto y agudo: nota La5 (880 Hz), 80 ms."""
    threading.Thread(target=_tono, args=(880, 80), daemon=True).start()


def sonido_raya():
    """Tono suave y grave: nota Re4 (294 Hz), 220 ms."""
    threading.Thread(target=_tono, args=(294, 220), daemon=True).start()


def sonido_letra_ok():
    """Confirmacion de letra: acorde corto Mi5-Sol#5 (659->830 Hz)."""
    def _seq():
        _tono(659, 60)
        _tono(830, 60)
    threading.Thread(target=_seq, daemon=True).start()


def sonido_error():
    """Caracter desconocido: tono grave descendente."""
    def _seq():
        _tono(220, 120)
        _tono(180, 120)
    threading.Thread(target=_seq, daemon=True).start()


def sonido_frase_enviada():
    """Fanfarria corta al enviar la frase de A."""
    def _seq():
        for f in (523, 659, 784):   # Do5 - Mi5 - Sol5
            _tono(f, 80)
            time.sleep(0.02)
    threading.Thread(target=_seq, daemon=True).start()


def sonido_ronda_ganada():
    """Melodia de victoria al ganar la ronda."""
    def _seq():
        for f, d in [(523, 80), (659, 80), (784, 80), (1047, 160)]:
            _tono(f, d)
            time.sleep(0.02)
    threading.Thread(target=_seq, daemon=True).start()


def sonido_empate():
    """Tono neutral para empate."""
    def _seq():
        _tono(440, 120)
        time.sleep(0.05)
        _tono(440, 120)
    threading.Thread(target=_seq, daemon=True).start()

# Comunicacion USB serie usando solo open() de Python

class PuertoSerie:
    """
    Comunicacion USB serie para Windows usando ctypes puro (Win32 API).
    Lee y escribe directamente sobre el HANDLE de Win32 sin pasar por
    msvcrt ni io.open, evitando el error Bad file descriptor.
    """

    def __init__(self, dispositivo, baudrate=115200, timeout=1.0):
        self._dev      = dispositivo
        self._baudrate = baudrate
        self._timeout  = timeout      # segundos
        self._handle   = None         # HANDLE de Win32
        self.is_open   = False

    def open(self):
        import ctypes
        import ctypes.wintypes as wt

        k32 = ctypes.WinDLL('kernel32', use_last_error=True)

        # Abrir el puerto COM (los puertos COM10+ necesitan prefijo \\\\.\\)
        nombre = r'\\\\.\\{}'.format(self._dev)
        GENERIC_READ_WRITE = 0xC0000000
        OPEN_EXISTING      = 3

        handle = k32.CreateFileW(
            nombre, GENERIC_READ_WRITE, 0, None, OPEN_EXISTING, 0, None)

        if handle == wt.HANDLE(-1).value:
            err = ctypes.get_last_error()
            raise OSError("No se pudo abrir {} (error Win32: {})".format(
                self._dev, err))

        # Configurar parametros serie: 8N1, sin control de flujo
        class DCB(ctypes.Structure):
            _fields_ = [
                ("DCBlength",  ctypes.c_ulong),
                ("BaudRate",   ctypes.c_ulong),
                ("fBits",      ctypes.c_ulong),
                ("wReserved",  ctypes.c_ushort),
                ("XonLim",     ctypes.c_ushort),
                ("XoffLim",    ctypes.c_ushort),
                ("ByteSize",   ctypes.c_ubyte),
                ("Parity",     ctypes.c_ubyte),
                ("StopBits",   ctypes.c_ubyte),
                ("XonChar",    ctypes.c_char),
                ("XoffChar",   ctypes.c_char),
                ("ErrorChar",  ctypes.c_char),
                ("EofChar",    ctypes.c_char),
                ("EvtChar",    ctypes.c_char),
                ("wReserved1", ctypes.c_ushort),
            ]

        dcb = DCB()
        dcb.DCBlength = ctypes.sizeof(DCB)
        k32.GetCommState(handle, ctypes.byref(dcb))
        dcb.BaudRate = self._baudrate
        dcb.ByteSize = 8   # 8 bits de datos
        dcb.Parity   = 0   # sin paridad
        dcb.StopBits = 0   # 1 bit de parada
        dcb.fBits    = 0x1 # fBinary = True, resto en 0 (sin flujo)
        k32.SetCommState(handle, ctypes.byref(dcb))

        # Configurar timeouts de lectura
        class COMMTIMEOUTS(ctypes.Structure):
            _fields_ = [
                ("ReadIntervalTimeout",        ctypes.c_ulong),
                ("ReadTotalTimeoutMultiplier",  ctypes.c_ulong),
                ("ReadTotalTimeoutConstant",    ctypes.c_ulong),
                ("WriteTotalTimeoutMultiplier", ctypes.c_ulong),
                ("WriteTotalTimeoutConstant",   ctypes.c_ulong),
            ]

        ct = COMMTIMEOUTS()
        # ReadTotalTimeoutConstant: tiempo maximo total por operacion Read (ms)
        ct.ReadIntervalTimeout        = 0
        ct.ReadTotalTimeoutMultiplier = 0
        ct.ReadTotalTimeoutConstant   = int(self._timeout * 1000)
        ct.WriteTotalTimeoutMultiplier = 0
        ct.WriteTotalTimeoutConstant   = 2000
        k32.SetCommTimeouts(handle, ctypes.byref(ct))

        # Limpiar buffers de entrada/salida
        k32.PurgeComm(handle, 0x000F)  # PURGE_TXABORT|PURGE_RXABORT|PURGE_TXCLEAR|PURGE_RXCLEAR

        self._handle  = handle
        self._k32     = k32
        self.is_open  = True

    def readline(self):
        """Lee bytes hasta '\\n' o timeout, usando ReadFile de Win32."""
        if not self._handle:
            return b''
        import ctypes
        linea    = b''
        buf      = ctypes.create_string_buffer(1)
        leidos   = ctypes.c_ulong(0)
        fin      = time.time() + self._timeout

        while time.time() < fin:
            ok = self._k32.ReadFile(
                self._handle, buf, 1,
                ctypes.byref(leidos), None)
            if ok and leidos.value == 1:
                byte = buf.raw[:1]
                linea += byte
                if byte == b'\n':
                    break
        return linea

    def write(self, datos):
        """Escribe bytes usando WriteFile de Win32."""
        if not self._handle:
            return
        import ctypes
        buf      = ctypes.create_string_buffer(datos)
        escritos = ctypes.c_ulong(0)
        self._k32.WriteFile(
            self._handle, buf, len(datos),
            ctypes.byref(escritos), None)

    def close(self):
        if self._handle:
            self._k32.CloseHandle(self._handle)
            self._handle = None
        self.is_open = False

# Funciones de calificacion

def calcular_puntaje(original, respuesta):
    """
    Compara caracter a caracter, ignorando espacios y mayusculas.
    Retorna la cantidad de posiciones correctas (igual que game_logic_viejo).
    """
    orig = original.upper().replace(' ', '')
    resp = respuesta.upper().replace(' ', '')
    puntos = 0
    for i in range(min(len(orig), len(resp))):
        if orig[i] == resp[i]:
            puntos += 1
    return puntos


def nivel_velocidad(tiempo_ms, num_chars):
    """Clasifica la velocidad de transmision en Rapido/Medio/Lento."""
    if num_chars == 0:
        return "Lento"
    ms_por_char = tiempo_ms / num_chars
    for nivel, (minimo, maximo) in VELOCIDAD.items():
        if minimo <= ms_por_char < maximo:
            return nivel
    return "Lento"


# ============================================================
# Clase principal: interfaz Tkinter + logica del juego
# ============================================================

class AppStrangerTEC:
    """Ventana unica del juego. No hay dialogo previo de puerto."""

    # Duracion de una unidad Morse para la entrada del teclado (ms)
    UNIDAD_MS = 200

    def __init__(self, root):
        self._root = root
        self._root.title("StrangerTEC - Morse Translator")
        self._root.configure(bg=FONDO)
        self._root.resizable(False, False)

        # ── Estado del juego ─────────────────────────────────
        self._frase          = ""
        self._puntaje_a      = 0
        self._puntaje_b      = 0
        self._pts_a_ronda    = 0
        self._pts_b_ronda    = 0
        self._ronda          = 1
        self._turno_a        = True
        self._modo_simple    = False
        self._a_respondio    = False
        self._b_respondio    = False

        # ── Buffers Morse (jugador A) ─────────────────────────
        self._morse_buf   = ""
        self._letras_buf  = ""
        self._tecla_abajo = False
        self._t_press     = 0
        self._t_inicio_a = 0   # inicio del turno de A
        self._t_inicio_b = 0   # inicio del turno de B
        self._resp_a     = ""  # respuesta de A para mostrar en resultado

        # ── Widgets del panel LED ─────────────────────────────
        self._leds = {}

        # ── Puerto serie ──────────────────────────────────────
        self._ser = None

        self._construir_ui()
        self._iniciar_serial()

    # ── Construccion de la UI ─────────────────────────────────

    def _construir_ui(self):
        fuente_titulo = ("Courier", 18, "bold")
        fuente_panel  = ("Courier", 12, "bold")
        fuente_info   = ("Courier", 10)
        fuente_morse  = ("Courier", 13, "bold")

        # Titulo
        tk.Label(self._root, text="STRANGERTEC MORSE TRANSLATOR",
                 font=fuente_titulo, fg=ROJO, bg=FONDO).pack(pady=(12, 4))

        # Panel de letras virtual
        frame_panel = tk.Frame(self._root, bg=FONDO)
        frame_panel.pack(padx=16, pady=8)
        for fila in [FILA1, FILA2, FILA3]:
            fila_frame = tk.Frame(frame_panel, bg=FONDO)
            fila_frame.pack()
            for c in fila:
                lbl = tk.Label(fila_frame, text=c, width=3,
                               font=fuente_panel, fg=GRIS, bg=GRIS,
                               relief="flat", bd=1)
                lbl.pack(side=tk.LEFT, padx=2, pady=2)
                self._leds[c] = lbl

        # Informacion de ronda
        frame_info = tk.Frame(self._root, bg=FONDO)
        frame_info.pack()
        self._lbl_frase = tk.Label(frame_info, text="Frase: ---",
                                   font=fuente_info, fg=AMARILLO, bg=FONDO)
        self._lbl_frase.pack()
        self._lbl_modo  = tk.Label(frame_info, text="Modo: ---",
                                   font=fuente_info, fg=BLANCO, bg=FONDO)
        self._lbl_modo.pack()
        self._lbl_turno = tk.Label(frame_info, text="Turno: ---",
                                   font=fuente_info, fg=VERDE, bg=FONDO)
        self._lbl_turno.pack()
        self._lbl_conexion = tk.Label(frame_info,
                                      text="Conexion: buscando Pico...",
                                      font=fuente_info, fg=GRIS, bg=FONDO)
        self._lbl_conexion.pack()

        # ── Presentacion de frase para Jugador B ─────────────
        # (tomado de game_logic_viejo: muestra la frase y el codigo Morse)
        frame_b = tk.Frame(self._root, bg="#0a0a1a", relief="sunken", bd=1)
        frame_b.pack(padx=16, pady=4, fill=tk.X)
        tk.Label(frame_b, text="JUGADOR B — frase que debe transmitir:",
                 font=fuente_info, fg=AZUL, bg="#0a0a1a").pack(anchor="w", padx=6)
        self._lbl_frase_b = tk.Label(frame_b, text="—",
                                     font=("Courier", 14, "bold"),
                                     fg=AMARILLO, bg="#0a0a1a")
        self._lbl_frase_b.pack(anchor="w", padx=10)
        self._lbl_morse_b = tk.Label(frame_b, text="",
                                     font=("Courier", 10),
                                     fg="#888888", bg="#0a0a1a",
                                     wraplength=480, justify=tk.LEFT)
        self._lbl_morse_b.pack(anchor="w", padx=10, pady=(0, 4))

        # ── Entrada Morse del jugador A ───────────────────────
        frame_entrada = tk.Frame(self._root, bg="#111", relief="sunken", bd=1)
        frame_entrada.pack(padx=16, pady=6, fill=tk.X)
        tk.Label(frame_entrada,
                 text="JUGADOR A: Mantenga [ESPACIO] para ingresar Morse",
                 font=fuente_info, fg="#666", bg="#111").pack()
        self._lbl_simbolos = tk.Label(frame_entrada, text="Simbolos: ",
                                      font=fuente_morse, fg=AMARILLO, bg="#111")
        self._lbl_simbolos.pack()
        self._lbl_letras   = tk.Label(frame_entrada, text="Letras:   ",
                                      font=fuente_morse, fg=VERDE, bg="#111")
        self._lbl_letras.pack()
        fila_btns = tk.Frame(frame_entrada, bg="#111")
        fila_btns.pack(pady=4)
        tk.Button(fila_btns, text="Confirmar letra [ENTER]",
                  command=self._confirmar_letra,
                  bg="#1a0000", fg=AMARILLO, font=fuente_info,
                  relief="flat").pack(side=tk.LEFT, padx=6)
        tk.Button(fila_btns, text="Enviar frase [F1]",
                  command=self._enviar_frase_a,
                  bg="#001a00", fg=VERDE, font=fuente_info,
                  relief="flat").pack(side=tk.LEFT, padx=6)

        # ── Puntajes ─────────────────────────────────────────
        frame_pts = tk.Frame(self._root, bg=FONDO)
        frame_pts.pack(pady=6)
        self._lbl_pts_a = tk.Label(frame_pts, text="Jugador A: 0",
                                   font=fuente_info, fg=VERDE, bg=FONDO)
        self._lbl_pts_a.pack(side=tk.LEFT, padx=20)
        self._lbl_pts_b = tk.Label(frame_pts, text="Jugador B: 0",
                                   font=fuente_info, fg=AMARILLO, bg=FONDO)
        self._lbl_pts_b.pack(side=tk.LEFT, padx=20)

        # ── Botones de control ────────────────────────────────
        frame_ctrl = tk.Frame(self._root, bg=FONDO)
        frame_ctrl.pack(pady=6)
        tk.Button(frame_ctrl, text="Nueva ronda",
                  command=self._nueva_ronda,
                  bg="#002200", fg=VERDE, font=fuente_info, relief="flat"
                  ).pack(side=tk.LEFT, padx=8)
        tk.Button(frame_ctrl, text="Reiniciar juego",
                  command=self._reiniciar,
                  bg="#220000", fg=ROJO, font=fuente_info, relief="flat"
                  ).pack(side=tk.LEFT, padx=8)

        # ── Atajos de teclado del jugador A ──────────────────
        self._root.bind("<KeyPress-space>",   self._tecla_abajo_cb)
        self._root.bind("<KeyRelease-space>", self._tecla_arriba_cb)
        self._root.bind("<Return>",           lambda e: self._confirmar_letra())
        self._root.bind("<F1>",               lambda e: self._enviar_frase_a())

    # ── Presentacion de frase para Jugador B ─────────────────
    # Logica tomada de game_logic_viejo: muestra frase y codigo Morse
    # para que el jugador B sepa exactamente que debe transmitir.

    def _actualizar_panel_b(self, frase):
        """
        Muestra la frase y su representacion Morse completa en el
        panel del Jugador B (igual que _presentar_frase en game_logic_viejo).
        """
        self._lbl_frase_b.config(text=frase)
        # Construir la linea Morse de referencia
        partes = []
        for c in frase.upper():
            if c == ' ':
                partes.append('/')
            elif c in MORSE:
                partes.append(MORSE[c])
            else:
                partes.append('?')
        self._lbl_morse_b.config(text="  ".join(partes))

    def _animar_presentacion_b(self, frase, idx=0):
        """
        Ilumina cada letra de la frase en secuencia en el panel LED,
        con retroalimentacion sonora Morse (igual que _presentar_frase
        en game_logic_viejo pero en el lado del PC).
        """
        chars = [(i, c) for i, c in enumerate(frase.upper()) if c != ' ']
        if idx < len(chars):
            _, c = chars[idx]
            self._iluminar_led(c, color=AZUL, ms=380)
            # Retroalimentacion sonora: reproducir el codigo Morse del caracter
            self._reproducir_morse_letra(c)
            self._root.after(480, lambda: self._animar_presentacion_b(frase, idx + 1))

    def _reproducir_morse_letra(self, letra):
        """
        Reproduce el sonido Morse de una letra en un hilo separado
        para no bloquear la UI. Usa tonos agradables (no beep generico).
        """
        if letra not in MORSE:
            return
        secuencia = MORSE[letra]

        def _tocar():
            u = self.UNIDAD_MS / 1000.0   # unidad en segundos
            for simbolo in secuencia:
                if simbolo == '.':
                    _tono(880, int(u * 1000))        # La5: punto
                else:
                    _tono(523, int(3 * u * 1000))    # Do5: raya (mas suave)
                time.sleep(u)             # pausa entre simbolos
            time.sleep(3 * u)             # pausa entre caracteres

        threading.Thread(target=_tocar, daemon=True).start()

    # ── Entrada Morse del jugador A ───────────────────────────

    def _tecla_abajo_cb(self, event):
        if not self._tecla_abajo and self._turno_a:
            self._tecla_abajo = True
            self._t_press = time.time()

    def _tecla_arriba_cb(self, event):
        if self._tecla_abajo and self._turno_a:
            self._tecla_abajo = False
            duracion_ms = (time.time() - self._t_press) * 1000
            umbral = 2 * self.UNIDAD_MS
            simbolo = '-' if duracion_ms >= umbral else '.'
            self._morse_buf += simbolo
            self._lbl_simbolos.config(text="Simbolos: " + self._morse_buf)
            # Retroalimentacion sonora inmediata al ingresar cada simbolo
            if simbolo == '.':
                sonido_punto()
            else:
                sonido_raya()

    def _confirmar_letra(self):
        """Decodifica el buffer Morse y lo agrega a la frase de A."""
        if not self._morse_buf or not self._turno_a:
            return
        letra = MORSE_INV.get(self._morse_buf, '?')
        self._letras_buf += letra
        self._morse_buf = ""
        self._lbl_simbolos.config(text="Simbolos: ")
        self._lbl_letras.config(text="Letras:   " + self._letras_buf)
        if letra != '?' and letra in self._leds:
            self._leds[letra].config(fg=VERDE, bg=VERDE)
            self._root.after(400, lambda: self._apagar_led(letra))
            sonido_letra_ok()
        else:
            sonido_error()

    def _enviar_frase_a(self):
        """
        Evalua la respuesta de A, otorga puntaje y pasa turno a B.

        En Modo Simple: el Pico ya tiene la frase -> enviar solo INICIO.
        En Modo Escucha: el Pico ya recibio FRASE: al inicio de ronda
                         -> enviar solo INICIO para habilitar turno B.
        En ambos casos el bonus de velocidad de A se mide desde
        self._t_inicio_a (cuando llego MORSE: o cuando arranco la ronda).
        """
        if not self._turno_a:
            return

        resp_a    = self._letras_buf.upper()
        num_chars = len(self._frase.replace(' ', ''))

        # Puntaje base
        pts_a = calcular_puntaje(self._frase, resp_a)

        # Bonus de velocidad (aplica en ambos modos para A)
        t_ms  = (time.time() - self._t_inicio_a) * 1000
        nivel = nivel_velocidad(t_ms, num_chars)
        bonus = BONUS_VELOCIDAD.get(nivel, 1)
        pts_a += bonus
        print("Jugador A: {} pts base + {} bonus ({})".format(
            pts_a - bonus, bonus, nivel))

        self._resp_a      = resp_a    # guardar para mostrar en resultado
        self._pts_a_ronda = pts_a
        self._puntaje_a  += pts_a
        self._a_respondio = True
        self._actualizar_puntajes()

        # Limpiar buffers de entrada
        self._letras_buf = ""
        self._morse_buf  = ""
        self._lbl_simbolos.config(text="Simbolos: ")
        self._lbl_letras.config(text="Letras:   ")

        # Cambiar turno
        self._turno_a = False
        self._lbl_turno.config(
            text="Turno: Jugador B (maqueta)", fg=AMARILLO)

        # Mostrar frase de referencia al Jugador B en pantalla
        self._actualizar_panel_b(self._frase)
        self._animar_presentacion_b(self._frase)

        # En ambos modos: el Pico ya tiene la frase, solo necesita INICIO
        self._t_inicio_b = time.time()   # cronometro para bonus velocidad B
        self._enviar_pico("INICIO")
        sonido_frase_enviada()

    # ── Control del juego ─────────────────────────────────────

    def _nueva_ronda(self):
        """
        Selecciona frase e inicia una nueva ronda.
        Solo se llama en Modo Escucha (el PC elige la frase).
        En Modo Simple el Pico elige la frase y el flujo lo maneja
        _procesar_mensaje al recibir MORSE:.
        """
        self._frase          = random.choice(FRASES)
        self._turno_a        = True
        self._a_respondio    = False
        self._b_respondio    = False
        self._pts_a_ronda    = 0
        self._pts_b_ronda    = 0
        self._resp_a         = ""
        self._morse_buf      = ""
        self._letras_buf     = ""
        self._apagar_todos()
        self._lbl_frase.config(text="Frase: " + self._frase)
        self._lbl_turno.config(text="Turno: Jugador A (teclado)", fg=VERDE)
        self._lbl_simbolos.config(text="Simbolos: ")
        self._lbl_letras.config(text="Letras:   ")
        self._lbl_frase_b.config(text="—")
        self._lbl_morse_b.config(text="")

        # Enviar frase al Pico y animar el panel LED del PC
        self._enviar_pico("FRASE:" + self._frase)
        self._animar_frase(self._frase)
        self._t_inicio_a = time.time()   # cronometro de A arranca aqui

    def _reiniciar(self):
        """Reinicia puntajes y arranca una ronda nueva."""
        self._puntaje_a = 0
        self._puntaje_b = 0
        self._ronda     = 1
        self._actualizar_puntajes()
        self._nueva_ronda()

    def _mostrar_resultado(self, resp_b):
        """
        Muestra resultado completo de la ronda con puntajes
        (logica de puntaje tomada de game_logic_viejo).
        """
        total_chars = len(self._frase.replace(' ', ''))

        if self._pts_a_ronda > self._pts_b_ronda:
            ganador_ronda = "Jugador A"
            sonido_ronda_ganada()
        elif self._pts_b_ronda > self._pts_a_ronda:
            ganador_ronda = "Jugador B"
            sonido_ronda_ganada()
        else:
            ganador_ronda = "EMPATE"
            sonido_empate()

        if self._puntaje_a > self._puntaje_b:
            lider = "Jugador A"
        elif self._puntaje_b > self._puntaje_a:
            lider = "Jugador B"
        else:
            lider = "EMPATE"

        # Puntaje base (sin bonus) para mostrar X/total correctamente
        pts_a_base = calcular_puntaje(self._frase, getattr(self, '_resp_a', ''))
        pts_b_base = calcular_puntaje(self._frase, resp_b)
        bonus_a    = self._pts_a_ronda - pts_a_base
        bonus_b    = self._pts_b_ronda - pts_b_base

        def _linea_pts(base, bonus, total):
            s = "  {} / {} aciertos".format(base, total)
            if bonus > 0:
                s += "  +{}  bonus velocidad".format(bonus)
            return s

        texto = (
            "=== Ronda {} terminada ===\n\n"
            "Frase original:   {}\n"
            "Respuesta de A:   {}\n"
            "Respuesta de B:   {}\n\n"
            "Jugador A:{}\n"
            "Jugador B:{}\n"
            "Ganador ronda:    {}\n\n"
            "--- Puntaje acumulado ---\n"
            "Jugador A: {}\n"
            "Jugador B: {}\n"
            "Va ganando: {}"
        ).format(
            self._ronda,
            self._frase,
            getattr(self, '_resp_a', '---') or '(vacio)',
            resp_b or '(vacio)',
            _linea_pts(pts_a_base, bonus_a, total_chars),
            _linea_pts(pts_b_base, bonus_b, total_chars),
            ganador_ronda,
            self._puntaje_a, self._puntaje_b, lider
        )

        popup = tk.Toplevel(self._root)
        popup.title("Resultado ronda " + str(self._ronda))
        popup.configure(bg=FONDO)
        popup.resizable(False, False)
        tk.Label(popup, text=texto, font=("Courier", 11),
                 fg=AMARILLO, bg=FONDO, justify=tk.LEFT,
                 padx=20, pady=10).pack()
        tk.Button(popup, text="Nueva ronda",
                  command=lambda: [popup.destroy(), self._sig_ronda()],
                  bg="#001a00", fg=VERDE, relief="flat",
                  font=("Courier", 10)).pack(pady=8)
        self._ronda += 1

    def _sig_ronda(self):
        self._nueva_ronda()

    # ── Panel de LEDs virtual ─────────────────────────────────

    def _iluminar_led(self, letra, color=None, ms=350):
        if letra in self._leds:
            c = color or AMARILLO
            self._leds[letra].config(fg=c, bg=c)
            self._root.after(ms, lambda: self._apagar_led(letra))

    def _apagar_led(self, letra):
        if letra in self._leds:
            self._leds[letra].config(fg=GRIS, bg=GRIS)

    def _apagar_todos(self):
        for lbl in self._leds.values():
            lbl.config(fg=GRIS, bg=GRIS)

    def _animar_frase(self, frase, idx=0):
        """Ilumina cada letra de la frase en secuencia (animacion visual)."""
        chars = [c for c in frase.upper() if c != ' ']
        if idx < len(chars):
            self._iluminar_led(chars[idx], ms=380)
            self._root.after(430, lambda: self._animar_frase(frase, idx + 1))

    def _actualizar_puntajes(self):
        self._lbl_pts_a.config(text="Jugador A: " + str(self._puntaje_a))
        self._lbl_pts_b.config(text="Jugador B: " + str(self._puntaje_b))

    # ── Comunicacion USB serie ────────────────────────────────

    def _iniciar_serial(self):
        """
        Detecta el puerto del Pico automaticamente y abre la conexion.
        Si no lo encuentra muestra un boton para reintentar.
        """
        puerto = _detectar_puerto_pico()
        if not puerto:
            self._lbl_conexion.config(
                text="Conexion: Pico no encontrado — conecta el USB",
                fg=ROJO)
            # Boton de reintento: aparece solo cuando falla la deteccion
            if not hasattr(self, '_btn_reintentar'):
                self._btn_reintentar = tk.Button(
                    self._root,
                    text="Reintentar conexion",
                    command=self._reintentar_conexion,
                    bg="#220022", fg=BLANCO,
                    font=("Courier", 10), relief="flat")
                self._btn_reintentar.pack(pady=2)
            return

        try:
            self._ser = PuertoSerie(puerto, baudrate=BAUDRATE, timeout=1.0)
            self._ser.open()
            print("Puerto serie abierto:", puerto)
            self._lbl_conexion.config(
                text="Conexion: " + puerto + "  [conectado]",
                fg=VERDE)
            # Ocultar boton de reintento si estaba visible
            if hasattr(self, '_btn_reintentar'):
                self._btn_reintentar.pack_forget()
            hilo = threading.Thread(target=self._leer_serial, daemon=True)
            hilo.start()
        except Exception as e:
            print("Error al abrir puerto serie:", e)
            self._lbl_conexion.config(
                text="Conexion: " + puerto + "  [ERROR: " + str(e)[:40] + "]",
                fg=ROJO)
            if not hasattr(self, '_btn_reintentar'):
                self._btn_reintentar = tk.Button(
                    self._root,
                    text="Reintentar conexion",
                    command=self._reintentar_conexion,
                    bg="#220022", fg=BLANCO,
                    font=("Courier", 10), relief="flat")
                self._btn_reintentar.pack(pady=2)

    def _reintentar_conexion(self):
        """Cierra el puerto si estaba abierto y vuelve a detectar."""
        if self._ser:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
        self._lbl_conexion.config(
            text="Conexion: buscando Pico...", fg=GRIS)
        self._root.after(500, self._iniciar_serial)  # pequena pausa antes de reintentar

    def _leer_serial(self):
        """Lee mensajes del Pico en un hilo separado."""
        while True:
            try:
                if self._ser and self._ser.is_open:
                    linea = self._ser.readline()
                    if linea:
                        msg = linea.decode('utf-8', errors='replace').strip()
                        if msg:
                            print("Pico ->", msg)
                            self._root.after(
                                0, lambda m=msg: self._procesar_mensaje(m))
            except Exception as e:
                print("Conexion serie perdida:", e)
                self._root.after(0, lambda: self._lbl_conexion.config(
                    text="Conexion: [desconectado — reconecta el USB y reintenta]",
                    fg=ROJO))
                break

    def _procesar_mensaje(self, msg):
        """
        Maneja los mensajes recibidos del Pico (hilo principal de UI).

        Flujo Modo Simple (DIP OFF):
          Pico  -> LISTO
          Pico  -> MODO:SIMPLE
          PC    -> INICIO          (habilita turno A en la maqueta)
          Pico  -> MORSE:<frase>   (frase elegida por el Pico)
          [Jugador A ingresa en PC; al confirmar con F1:]
          PC    -> INICIO          (habilita turno B en la maqueta)
          Pico  -> RESP:<texto>
          PC    -> PUNTAJE:<n>

        Flujo Modo Escucha (DIP ON):
          Pico  -> LISTO
          Pico  -> MODO:ESCUCHA
          PC    -> FRASE:<texto>   (frase elegida por el PC)
          [Jugador A ingresa en PC; al confirmar con F1:]
          PC    -> INICIO          (habilita turno B en la maqueta)
          Pico  -> RESP:<texto>
          PC    -> PUNTAJE:<n>
        """
        print("Pico [proc]->", msg)

        if msg == "LISTO":
            # El Pico esta listo: informar el modo para que el PC reaccione
            # correctamente cuando llegue el siguiente mensaje MODO:*
            pass

        elif msg == "MODO:SIMPLE":
            # Modo Simple: el Pico elige la frase.
            # Enviar INICIO para que el Pico sepa que el PC esta listo
            # y pueda transmitir la frase seleccionada (MORSE:).
            self._modo_simple = True
            self._lbl_modo.config(text="Modo: Transmision Simple")
            self._lbl_turno.config(text="Esperando frase del Pico...", fg=GRIS)
            self._enviar_pico("INICIO")   # <-- desbloquea al Pico para enviar MORSE:

        elif msg == "MODO:ESCUCHA":
            # Modo Escucha: el PC elige la frase y la envia al Pico.
            self._modo_simple = False
            self._lbl_modo.config(text="Modo: Escucha y Transmision")
            self._nueva_ronda()           # envia FRASE: al Pico

        elif msg.startswith("MORSE:"):
            # Solo Modo Simple: el Pico informa la frase que eligio.
            # El panel LED del Pico ya la esta mostrando.
            # Arrancar el turno de A en el PC.
            frase_pico = msg[6:].strip()
            self._frase          = frase_pico
            self._resp_a         = ""     # resetear respuesta A
            self._a_respondio    = False
            self._b_respondio    = False
            self._lbl_frase.config(text="Frase: " + frase_pico)
            self._animar_frase(frase_pico)
            self._lbl_frase_b.config(text="—")
            self._lbl_morse_b.config(text="")
            self._morse_buf   = ""
            self._letras_buf  = ""
            self._lbl_simbolos.config(text="Simbolos: ")
            self._lbl_letras.config(text="Letras:   ")
            self._turno_a = True
            self._lbl_turno.config(text="Turno: Jugador A (teclado)", fg=VERDE)
            self._t_inicio_a = time.time()   # cronometro especifico de A

        elif msg.startswith("RESP:"):
            # El Pico envia la respuesta del jugador B.
            resp_b = msg[5:].strip()
            num_chars = len(self._frase.replace(' ', ''))

            # Puntaje base: aciertos caracter a caracter
            pts_b = calcular_puntaje(self._frase, resp_b)

            # Bonus de velocidad para B en Modo Simple
            # (se mide desde que se envio INICIO al Pico para turno B)
            if self._modo_simple:
                t_ms  = (time.time() - self._t_inicio_b) * 1000
                nivel = nivel_velocidad(t_ms, num_chars)
                bonus = BONUS_VELOCIDAD.get(nivel, 1)
                pts_b += bonus
                print("Jugador B: {} pts base + {} bonus ({})".format(
                    pts_b - bonus, bonus, nivel))
            else:
                print("Jugador B:", pts_b, "pts")

            self._pts_b_ronda = pts_b
            self._puntaje_b  += pts_b
            self._b_respondio = True
            self._enviar_pico("PUNTAJE:" + str(pts_b))
            self._actualizar_puntajes()

            # Mostrar resultado solo cuando ambos jugadores respondieron
            if self._a_respondio and self._b_respondio:
                self._mostrar_resultado(resp_b)

    def _enviar_pico(self, mensaje):
        """Envia un mensaje de texto al Pico W via puerto USB serie."""
        if self._ser and self._ser.is_open:
            try:
                self._ser.write((mensaje + '\n').encode('utf-8'))
                print("PC ->", mensaje)
            except Exception as e:
                print("Error al enviar al Pico:", e)


# ── Punto de entrada ──────────────────────────────────────────
# No hay dialogo de puerto: la ventana del juego se abre directamente.
# Ajusta la constante PUERTO_PICO en la parte superior del archivo
# si el Pico aparece en un puerto diferente.

if __name__ == "__main__":
    root = tk.Tk()
    app = AppStrangerTEC(root)
    root.mainloop()
