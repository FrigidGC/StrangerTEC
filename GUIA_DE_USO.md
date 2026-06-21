# Guía de Uso — StrangerTEC Morse Translator

## Descripción general

El juego conecta una maqueta física (Raspberry Pi Pico W) con una
aplicación de escritorio en Python. Dos jugadores compiten transmitiendo
frases en código Morse: el **Jugador A** usa el teclado del PC y el
**Jugador B** usa los botones de la maqueta.

---

## Archivos del proyecto

| Archivo | Ejecuta en | Descripción |
|---|---|---|
| `main.py` | Pico W | Punto de entrada; inicializa hardware y arranca el juego |
| `game_logic.py` | Pico W | Lógica de los dos modos de juego |
| `led_panel.py` | Pico W | Control del panel de 13 LEDs via 74HC164 |
| `morse_input.py` | Pico W | Lectura del botón Morse y buzzer |
| `server_comm.py` | Pico W | Comunicación USB serie con el PC |
| `wifi_manager.py` | Pico W | Stub vacío (WiFi desactivado) |
| `pc_server.py` | PC | Interfaz gráfica Tkinter + comunicación USB |

---

## Requisitos

### PC
- Python 3.8 o superior
- Solo librerías de la biblioteca estándar de Python:
  `tkinter`, `threading`, `io`, `os`, `time`, `random`
- **No se necesita instalar `pyserial` ni ninguna otra librería externa**

### Maqueta (Pico W)
- MicroPython instalado (firmware oficial RP2040)
- Todos los archivos `.py` del proyecto copiados a la raíz del Pico

---

## Conexión de hardware

```
GP26 --> CLK de los 74HC164 (IC1 e IC2 en paralelo)
GP27 --> Entrada A/B del IC1 (datos)
GP13 --> LED14  Fila 1: A C E G I K M O Q S U W Y
GP14 --> LED15  Fila 2: B D F H J L N P R T V X Z
GP15 --> LED16  Fila 3: 0 1 2 3 4 5 6 7 8 9 - +
GP16 --> Botón Morse S1 (PULL_DOWN, activo en ALTO)
GP18 --> DIP-switch S2 (PULL_DOWN, activo en ALTO)
GP5  --> Buzzer LS1 (PWM)
```

El CLR de los 74HC164 va conectado a VCC (siempre activo).

---

## Instalación

### 1. Cargar el firmware al Pico

1. Mantener presionado el botón **BOOTSEL** del Pico mientras se conecta
   el cable USB.
2. Copiar el archivo `.uf2` de MicroPython al dispositivo de
   almacenamiento que aparece.

### 2. Copiar los archivos al Pico

Usando **Thonny** u otro IDE compatible con MicroPython:

1. Abrir cada archivo `.py` del proyecto.
2. Guardarlos en el Pico (File → Save as → Raspberry Pi Pico):
   - `main.py`
   - `game_logic.py`
   - `led_panel.py`
   - `morse_input.py`
   - `server_comm.py`
   - `wifi_manager.py`

### 3. Preparar el PC

Solo se necesita Python con Tkinter (ya incluido en la instalación
estándar de Python en Windows y macOS). En Linux puede requerirse:

```bash
sudo apt install python3-tk
```

---

## Iniciar el juego

### Paso 1 — Elegir el modo en la maqueta

Configurar el **DIP-switch S2** antes de conectar el USB:

| Posición del DIP-switch | Modo |
|---|---|
| **OFF** (0 V) | Modo Transmisión Simple |
| **ON** (3.3 V) | Modo Escucha y Transmisión |

### Paso 2 — Conectar la maqueta al PC

Conectar el cable USB entre el Pico W y el PC. El Pico arrancará
automáticamente al detectar alimentación.

### Paso 3 — Ejecutar el servidor en el PC

```bash
python pc_server.py
```

Aparecerá un diálogo para seleccionar el puerto serie:
- **Windows**: buscar un puerto `COMn` cuya descripción incluya
  "USB Serial" o "Pico".
- **Linux**: seleccionar `/dev/ttyACM0` o `/dev/ttyACM1`.
- **macOS**: seleccionar `/dev/cu.usbmodem...`.

Hacer clic en **Conectar**.

---

## Flujo de juego

### Modo Escucha y Transmisión

1. El PC selecciona una frase aleatoria y la envía al Pico.
2. La maqueta presenta la frase:
   - **LEDs**: ilumina cada letra en secuencia.
   - **Buzzer**: reproduce los puntos y rayas de cada carácter.
3. **Turno A**: el Jugador A ingresa la frase en Morse desde el PC
   usando la tecla `[ESPACIO]`:
   - Presión corta (< 400 ms) = punto `.`
   - Presión larga (≥ 400 ms) = raya `-`
   - `[ENTER]` = confirmar letra actual.
   - `[F1]` = enviar frase completa y pasar turno a B.
4. **Turno B**: el Pico recibe la señal de inicio y el Jugador B
   transmite la frase en Morse con el botón S1 de la maqueta.
5. El PC califica ambas respuestas y muestra el resultado de la ronda.
6. Se presiona **Nueva ronda** para continuar.

### Modo Transmisión Simple

1. El Pico selecciona una frase de su lista interna.
2. La maqueta muestra la frase en los LEDs.
3. **Turno A**: el PC muestra la frase; el Jugador A la ingresa en
   Morse usando la misma mecánica de teclado descrita arriba y
   presiona `[F1]` para confirmar.
4. **Turno B**: el Pico recibe la señal de inicio, reproduce la frase
   en el buzzer como referencia y el Jugador B la transmite con S1.
5. El PC califica con puntaje por precisión **y** por velocidad:

   | Nivel | ms promedio por carácter | Bonificación |
   |---|---|---|
   | Rápido | < 2 000 ms | +5 puntos |
   | Medio | 2 000 – 4 000 ms | +3 puntos |
   | Lento | > 4 000 ms | +1 punto |

---

## Técnica Morse con el botón (Jugador B)

| Acción | Resultado |
|---|---|
| Presión corta (< 2 × unidad) | Punto `.` |
| Presión larga (≥ 2 × unidad) | Raya `-` |
| Silencio de 3 unidades | Fin de carácter |
| Silencio de 7 unidades | Fin de frase |

La **unidad de tiempo** predeterminada es **200 ms** (configurable
en `main.py` cambiando `UNIDAD_A_MS` o `UNIDAD_B_MS`).

---

## Técnica Morse con el teclado (Jugador A)

| Acción | Resultado |
|---|---|
| `[ESPACIO]` presión corta (< 400 ms) | Punto `.` |
| `[ESPACIO]` presión larga (≥ 400 ms) | Raya `-` |
| `[ENTER]` | Confirmar y decodificar carácter |
| `[F1]` | Enviar frase completa |

La unidad del teclado es **200 ms** (constante `UNIDAD_MS` en
`pc_server.py`).

---

## Puntuación

- **1 punto** por cada carácter correcto en la posición correcta.
- **Bonificación de velocidad** solo en Modo Transmisión Simple
  (ver tabla de niveles arriba).
- Al finalizar cada ronda se muestra:
  - Puntos de A y B en esa ronda.
  - Ganador de la ronda.
  - Puntaje acumulado total.

---

## Resolución de problemas

| Síntoma | Solución |
|---|---|
| No aparecen puertos en el diálogo | Reconectar el USB; verificar drivers USB en Windows |
| "No se pudo abrir COMn" | Cerrar Thonny u otros programas que usen el puerto |
| El Pico no responde | Verificar que `main.py` está en la raíz del Pico |
| LEDs no encienden | Revisar conexión de GP26/GP27 y la alimentación de los 74HC164 |
| Buzzer no suena | Verificar conexión de GP5 y que el buzzer es pasivo (PWM) |
| Caracteres decodificados como `?` | Ajustar el tiempo de presión; revisar `UNIDAD_MS` |

---

## Cambiar la velocidad del juego

En `main.py`, modificar la línea:

```python
morse = LectorMorse(
    ...
    unidad_ms = UNIDAD_A_MS,  # cambiar a UNIDAD_B_MS para más lento
)
```

- `UNIDAD_A_MS = 200` → velocidad normal (recomendada)
- `UNIDAD_B_MS = 300` → velocidad reducida (nivel principiante)

---

## Agregar frases al juego

Editar la lista `FRASES` en `game_logic.py` (Pico) **y** en
`pc_server.py` (PC) para mantenerlas sincronizadas. Se recomienda
usar solo caracteres del mapa de LEDs:

```
A–Z  0–9  +  -  [espacio]
```
