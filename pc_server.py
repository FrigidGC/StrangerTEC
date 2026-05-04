# Servidor que recibe la conexion del Pico W y muestra
# la interfaz grafica del juego con Tkinter.
#
# Modos de juego:
#
# MODO TRANSMISION SIMPLE:
#   1. El Pico selecciona una frase y la envia ("MORSE:<frase>")
#   2. El servidor responde "INICIO" para arrancar el cronometro
#   3. El jugador B transmite en Morse desde la maqueta
#   4. El Pico envia la respuesta ("RESP:<texto>")
#   5. El servidor califica: puntaje por letra correcta + nivel de velocidad
#   6. Se cambia de turno: ahora el jugador A escribe desde el teclado
#
# MODO ESCUCHA Y TRANSMISION:
#   1. El servidor elige una frase aleatoria y la envia al Pico
#   2. La maqueta la presenta via LEDs/buzzer
#   3. El jugador B responde en Morse desde la maqueta
#   4. El jugador A responde en Morse desde el teclado del PC
#   5. Ambos reciben puntaje
#   6. Se cambia de turno
# ============================================================

import socket
import _thread
import time
import random
import tkinter as tk
from tkinter import messagebox

# ── Configuracion de red ──────────────────────────────────
IP_SERVIDOR  = "0.0.0.0"  # escuchar en todas las interfaces
PUERTO       = 8001        # puerto TCP

# ── Frases del juego ──────────────────────────────────────
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

# ── Tabla Morse ───────────────────────────────────────────
MORSE = {
    'A':'.-',   'B':'-...',  'C':'-.-.',  'D':'-..',
    'E':'.',    'F':'..-.',  'G':'--.',   'H':'....',
    'I':'..',   'J':'.---',  'K':'-.-',   'L':'.-..',
    'M':'--',   'N':'-.',    'O':'---',   'P':'.--.',
    'Q':'--.-', 'R':'.-.',   'S':'...',   'T':'-',
    'U':'..-',  'V':'...-',  'W':'.--',   'X':'-..-',
    'Y':'-.--', 'Z':'--..',
    '0':'-----','1':'.----', '2':'..---', '3':'...--',
    '4':'....-','5':'.....', '6':'-....', '7':'--...',
    '8':'---..',  '9':'----.',
    '+':'.-.-.', '-':'-....-',
}

# Velocidades para Modo Transmision Simple (ms por caracter promedio)
VELOCIDAD = {
    "Rapido":  (0,     2000),    # menos de 2 segundos por caracter
    "Medio":   (2000,  4000),
    "Lento":   (4000,  999999),
}

# Colores tema Stranger Things
FONDO   = "Black"
AMARILLO = "Yellow"
ROJO    = "Red"
VERDE   = "Green"
GRIS    = "Grey"
BLANCO  = "White"

# Filas del panel de letras
FILA1 = list("ACEGIKMOQSUWY")
FILA2 = list("BDFHJLNPRTVXZ")
FILA3 = list("0123456789-+")


def calcular_puntaje(original, respuesta):
    """Compara caracter a caracter y devuelve la cantidad de aciertos."""
    orig = original.upper().replace(' ', '')
    resp = respuesta.upper().replace(' ', '')
    return sum(1 for i in range(min(len(orig), len(resp))) if orig[i] == resp[i])


def nivel_velocidad(tiempo_ms, num_chars):
    """
    Califica la velocidad de transmision.
    Devuelve el nombre del nivel ("Rapido", "Medio" o "Lento").
    """
    if num_chars == 0:
        return "Lento"
    ms_por_char = tiempo_ms / num_chars  # tiempo promedio por caracter
    for nivel, (minimo, maximo) in VELOCIDAD.items():
        if minimo <= ms_por_char < maximo:
            return nivel
    return "Lento"


# ============================================================
# Clase principal de la interfaz y logica del juego
# ============================================================

class AppStrangerTEC:
    """Ventana principal del juego con Tkinter."""

    UNIDAD_MS = 200  # duracion de una unidad Morse para entrada del teclado

    def __init__(self, root):
        self._root = root
        self._root.title("StrangerTEC - Morse Translator")
        self._root.configure(bg=FONDO)
        self._root.resizable(False, False)

        # Estado del juego
        self._frase          = ""       # frase de la ronda actual
        self._puntaje_a      = 0        # puntaje acumulado jugador A
        self._puntaje_b      = 0        # puntaje acumulado jugador B
        self._ronda          = 1        # numero de ronda
        self._turno_a        = True     # True = turno de A, False = B
        self._modo_simple    = False    # modo recibido del Pico
        self._morse_buf      = ""       # simbolos Morse acumulados (jugador A)
        self._letras_buf     = ""       # letras decodificadas (jugador A)
        self._tecla_abajo    = False    # True mientras espacio esta presionado
        self._t_press        = 0        # tiempo en que se presiono la tecla
        self._t_inicio_ronda = 0        # tiempo de inicio de transmision

        # Widgets del panel de letras
        self._leds = {}   # {caracter: Label}

        # Servidor TCP (se inicia en hilo separado)
        self._cliente = None  # socket del cliente conectado (Pico)

        self._construir_ui()
        self._iniciar_servidor()

    # ── Construccion de la UI ─────────────────────────────

    def _construir_ui(self):
        """Construye todos los elementos de la ventana."""
        fuente_titulo = ("Courier", 18, "bold")
        fuente_panel  = ("Courier", 12, "bold")
        fuente_info   = ("Courier", 10)
        fuente_morse  = ("Courier", 13, "bold")

        # Titulo
        tk.Label(self._root, text="STRANGERTEC MORSE TRANSLATOR",
                 font=fuente_titulo, fg=ROJO, bg=FONDO).pack(pady=(12, 4))

        # Panel de letras (3 filas)
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

        # Area de entrada Morse del jugador A
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

        # Puntajes
        frame_pts = tk.Frame(self._root, bg=FONDO)
        frame_pts.pack(pady=6)
        self._lbl_pts_a = tk.Label(frame_pts, text="Jugador A: 0",
                                   font=fuente_info, fg=VERDE, bg=FONDO)
        self._lbl_pts_a.pack(side=tk.LEFT, padx=20)
        self._lbl_pts_b = tk.Label(frame_pts, text="Jugador B: 0",
                                   font=fuente_info, fg=AMARILLO, bg=FONDO)
        self._lbl_pts_b.pack(side=tk.LEFT, padx=20)

        # Botones de control
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

        # Atajos de teclado
        self._root.bind("<KeyPress-space>",   self._tecla_abajo_cb)
        self._root.bind("<KeyRelease-space>", self._tecla_arriba_cb)
        self._root.bind("<Return>",           lambda e: self._confirmar_letra())
        self._root.bind("<F1>",               lambda e: self._enviar_frase_a())

    # ── Entrada Morse jugador A ───────────────────────────

    def _tecla_abajo_cb(self, event):
        """Registrar inicio de presion de la tecla espacio."""
        if not self._tecla_abajo and self._turno_a:
            self._tecla_abajo = True
            self._t_press = time.time()  # guardar tiempo de inicio

    def _tecla_arriba_cb(self, event):
        """Determinar punto o raya al soltar la tecla espacio."""
        if self._tecla_abajo and self._turno_a:
            self._tecla_abajo = False
            duracion_ms = (time.time() - self._t_press) * 1000  # en ms
            umbral = 2 * self.UNIDAD_MS   # limite entre punto y raya
            simbolo = '-' if duracion_ms >= umbral else '.'
            self._morse_buf += simbolo   # agregar al buffer
            self._lbl_simbolos.config(text="Simbolos: " + self._morse_buf)

    def _confirmar_letra(self):
        """Decodifica el buffer Morse actual como una letra."""
        if not self._morse_buf:
            return
        # Buscar en la tabla Morse inversa
        tabla = {v: k for k, v in MORSE.items()}
        letra = tabla.get(self._morse_buf, '?')
        self._letras_buf += letra   # agregar letra al buffer de texto
        self._morse_buf = ""        # limpiar buffer de simbolos
        self._lbl_simbolos.config(text="Simbolos: ")
        self._lbl_letras.config(text="Letras:   " + self._letras_buf)
        if letra in self._leds:
            # Iluminar brevemente el LED de la letra en el panel
            self._leds[letra].config(fg=VERDE, bg=VERDE)
            self._root.after(400, lambda: self._apagar_led(letra))

    def _enviar_frase_a(self):
        """Evalua la frase ingresada por el jugador A y otorga puntaje."""
        respuesta = self._letras_buf.upper()
        pts = calcular_puntaje(self._frase, respuesta)

        # En Modo Simple: calcular nivel de velocidad
        if self._modo_simple:
            t_ms = (time.time() - self._t_inicio_ronda) * 1000
            nivel = nivel_velocidad(t_ms, len(self._frase.replace(' ', '')))
            pts_velocidad = {"Rapido": 5, "Medio": 3, "Lento": 1}.get(nivel, 1)
            pts += pts_velocidad
            print("Jugador A:", pts, "pts - Velocidad:", nivel)
        else:
            print("Jugador A:", pts, "pts")

        self._puntaje_a += pts
        self._actualizar_puntajes()
        self._letras_buf = ""
        self._morse_buf  = ""
        self._lbl_simbolos.config(text="Simbolos: ")
        self._lbl_letras.config(text="Letras:   ")

        # Cambiar turno al jugador B (maqueta)
        self._turno_a = False
        self._lbl_turno.config(text="Turno: Jugador B (maqueta)", fg=AMARILLO)

        # Enviar frase al Pico (para Modo Escucha) o senal de inicio (Modo Simple)
        if self._modo_simple:
            self._enviar_pico("INICIO")  # indicar al Pico que B puede transmitir
        else:
            self._enviar_pico("FRASE:" + self._frase)

    # ── Servidor TCP ──────────────────────────────────────

    def _iniciar_servidor(self):
        """Crea el socket servidor y arranca el hilo de escucha."""
        try:
            self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._server.bind((IP_SERVIDOR, PUERTO))
            self._server.listen(1)  # solo un cliente (el Pico)
            print("Servidor escuchando en puerto", PUERTO)
            # Arrancar el hilo de aceptacion de conexiones
            _thread.start_new_thread(self._aceptar_conexiones, ())
        except OSError as e:
            print("Error al iniciar servidor:", e)

    def _aceptar_conexiones(self):
        """Acepta una conexion entrante y la atiende (hilo)."""
        while True:
            try:
                cliente, addr = self._server.accept()  # esperar conexion
                print("Pico conectado desde:", addr)
                self._cliente = cliente
                # Atender al cliente en otro hilo
                _thread.start_new_thread(self._atender_cliente, (cliente,))
            except Exception as e:
                print("Error aceptando conexion:", e)

    def _atender_cliente(self, cliente):
        """Recibe mensajes del Pico y los procesa (hilo)."""
        try:
            while True:
                datos = cliente.recv(1024)  # recibir hasta 1024 bytes
                if not datos:
                    print("Pico desconectado")
                    break
                msg = datos.decode('utf-8').strip()  # decodificar mensaje
                print("Pico ->", msg)
                # Procesar el mensaje en el hilo principal de Tkinter
                self._root.after(0, lambda m=msg: self._procesar_mensaje(m))
        except ConnectionError as e:
            print("Error de conexion con Pico:", e)
        finally:
            cliente.close()
            self._cliente = None

    def _procesar_mensaje(self, msg):
        """Maneja los mensajes recibidos del Pico (ejecutado en hilo UI)."""
        if msg == "LISTO":
            # Pico listo: enviar modo y frase si es Modo Escucha
            pass  # el modo se gestiona cuando llega MODO:xxx

        elif msg == "MODO:SIMPLE":
            # Modo Transmision Simple activo en el Pico
            self._modo_simple = True
            self._lbl_modo.config(text="Modo: Transmision Simple")
            self._nueva_ronda()  # iniciar ronda

        elif msg == "MODO:ESCUCHA":
            # Modo Escucha y Transmision activo en el Pico
            self._modo_simple = False
            self._lbl_modo.config(text="Modo: Escucha y Transmision")
            self._nueva_ronda()  # iniciar ronda

        elif msg.startswith("MORSE:"):
            # Pico informa la frase seleccionada (Modo Simple)
            frase_pico = msg[6:]  # extraer texto
            self._frase = frase_pico
            self._lbl_frase.config(text="Frase: " + frase_pico)
            # Animar la frase en el panel LED virtual
            self._animar_frase(frase_pico)
            # Enviar senal de inicio al Pico
            self._enviar_pico("INICIO")
            self._t_inicio_ronda = time.time()  # iniciar cronometro
            self._lbl_turno.config(
                text="Turno: Jugador B (transmitiendo desde maqueta)",
                fg=AMARILLO)

        elif msg.startswith("RESP:"):
            # Respuesta del jugador B recibida
            resp_b = msg[5:]  # extraer texto
            pts = calcular_puntaje(self._frase, resp_b)

            if self._modo_simple:
                # Calcular velocidad para Modo Simple
                t_ms = (time.time() - self._t_inicio_ronda) * 1000
                nivel = nivel_velocidad(t_ms, len(self._frase.replace(' ', '')))
                pts_vel = {"Rapido": 5, "Medio": 3, "Lento": 1}.get(nivel, 1)
                pts += pts_vel

            self._puntaje_b += pts
            self._enviar_pico("PUNTAJE:" + str(pts))  # informar puntaje al Pico
            self._actualizar_puntajes()
            self._mostrar_resultado(resp_b, pts)

    def _enviar_pico(self, mensaje):
        """Envia un mensaje al Pico W conectado."""
        if self._cliente:
            try:
                self._cliente.sendall((mensaje + '\n').encode('utf-8'))
                print("PC ->", mensaje)
            except Exception as e:
                print("Error al enviar al Pico:", e)

    # ── Control del juego ─────────────────────────────────

    def _nueva_ronda(self):
        """Selecciona frase aleatoria e inicia una nueva ronda."""
        self._frase  = random.choice(FRASES)  # elegir frase aleatoria
        self._turno_a = True                   # jugador A empieza
        self._morse_buf  = ""
        self._letras_buf = ""
        self._apagar_todos()
        self._lbl_frase.config(text="Frase: " + self._frase)
        self._lbl_ronda_text()
        self._lbl_turno.config(text="Turno: Jugador A", fg=VERDE)
        self._lbl_simbolos.config(text="Simbolos: ")
        self._lbl_letras.config(text="Letras:   ")
        # Enviar la frase al Pico si es Modo Escucha
        if not self._modo_simple:
            self._enviar_pico("FRASE:" + self._frase)
        # Animar la frase en el panel virtual
        self._root.after(300, lambda: self._animar_frase(self._frase))
        self._t_inicio_ronda = time.time()

    def _lbl_ronda_text(self):
        """Actualiza el texto del label de ronda si existe."""
        pass  # se puede agregar un label de ronda en la UI

    def _reiniciar(self):
        """Reinicia puntajes y arranca una ronda nueva."""
        self._puntaje_a = 0
        self._puntaje_b = 0
        self._ronda     = 1
        self._actualizar_puntajes()
        self._nueva_ronda()

    def _mostrar_resultado(self, resp_b, pts_b):
        """Muestra ventana emergente con el resultado de la ronda."""
        ganador = ("A" if self._puntaje_a > self._puntaje_b
                   else "B" if self._puntaje_b > self._puntaje_a
                   else "EMPATE")
        texto = (
            "Ronda {} terminada\n\n"
            "Respuesta de B: {}\n"
            "Puntos de B esta ronda: {}\n\n"
            "Puntaje total A: {}\n"
            "Puntaje total B: {}\n\n"
            "Va ganando: Jugador {}".format(
                self._ronda, resp_b, pts_b,
                self._puntaje_a, self._puntaje_b, ganador)
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
                  bg="#001a00", fg=VERDE, relief="flat").pack(pady=8)
        self._ronda += 1

    def _sig_ronda(self):
        """Prepara la siguiente ronda."""
        self._turno_a = True
        self._nueva_ronda()

    # ── Panel de LEDs virtual ─────────────────────────────

    def _iluminar_led(self, letra, color=None, ms=350):
        """Enciende brevemente el LED de la letra indicada."""
        if letra in self._leds:
            c = color or AMARILLO
            self._leds[letra].config(fg=c, bg=c)
            self._root.after(ms, lambda: self._apagar_led(letra))

    def _apagar_led(self, letra):
        """Apaga el LED de la letra indicada."""
        if letra in self._leds:
            self._leds[letra].config(fg=GRIS, bg=GRIS)

    def _apagar_todos(self):
        """Apaga todos los LEDs del panel virtual."""
        for lbl in self._leds.values():
            lbl.config(fg=GRIS, bg=GRIS)

    def _animar_frase(self, frase, idx=0):
        """Ilumina cada letra de la frase en secuencia."""
        chars = [c for c in frase.upper() if c != ' ']
        if idx < len(chars):
            self._iluminar_led(chars[idx], ms=380)
            self._root.after(430, lambda: self._animar_frase(frase, idx + 1))

    def _actualizar_puntajes(self):
        """Actualiza las etiquetas de puntaje en pantalla."""
        self._lbl_pts_a.config(text="Jugador A: " + str(self._puntaje_a))
        self._lbl_pts_b.config(text="Jugador B: " + str(self._puntaje_b))


# ── Punto de entrada ──────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app  = AppStrangerTEC(root)
    root.mainloop()
