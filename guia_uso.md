# StrangerTEC Morse Translator - Guía de Uso

# Estructura de archivos
Copiar al Raspberry Pi Pico W
  main.py = Punto de entrada (correr primero)
  wifi_manager.py = Conexión WiFi
  led_panel.py = Control de LEDs via 74HC164
  morse_input.py = Lectura del botón y buzzer
  game_logic.py = Lógica del juego en el Pico
  server_comm.py = Comunicación TCP con la PC
  config.txt = CREAR ESTE ARCHIVO (ver abajo)

pc/
  pc_server.py = Servidor Python + GUI Tkinter
# 1. Configuración previa

# Archivo "config.txt" (en el Pico W)
Crear este archivo en el Pico antes de correr el código:

SSID= "nombre de la red wifi"
PASSWORD="la contraseña de la red wifi"
SERVER_IP=192.168.X.X
SERVER_PORT=8001

> **NO subir este archivo a GitHub**  
> Agregar "config.txt" al "gitignore"

### Conocer la IP de la PC

En Windows:
ipconfig

Usar la IP de la interfaz WiFi (ej. "192.168.8.134")  
Actualizar "SERVER_IP" en "config.txt"

-------------------------------------------------------------------------------------------------------
## 2. Instalación en el Pico W

1. Instalar **Thonny**
2. Conectar el Pico W por USB
3. En Thonny -> "Run" -> Select Interpreter -> MicroPython (Raspberry Pi Pico).
4. Subir todos los archivos de la carpeta "pico/" al Pico W:
   - File → Save as → MicroPython device
5. Verificar que "main.py" esté en la raíz del Pico.

-------------------------------------------------------------------------------------------------------
## 3. Correr el servidor en la PC

Requiere Python 3.8+ con Tkinter.
cd pc/
python pc_server.py

La ventana del juego se abre automáticamente y el servidor empieza a escuchar en el puerto 8001.

-------------------------------------------------------------------------------------------------------
## 4. Iniciar el juego

### Modo Escucha y Transmisión. (DIP-switch en OFF)
En la Maqueta, la Raspberry Pi Pico W recibe una de las frases. El
mensaje puede presentarse de 2 formas, las cuales se asocian en la
pantalla de configuración inicial de juego, que va depender del nivel
o Mediante señales luminosas utilizando los Leds de la maqueta.
o Mediante señales sonoras utilizando un buzzer, diferenciando
entre puntos, rayas y espacios, siguiendo una temporización del
código morse.

### Modo Transmisión Simple (DIP-switch en ON)
Desde la maqueta se realiza la transmisión de un mensaje, previamente
seleccionado de la lista de mensajes, por los jugadores, que se debe
recibir en el computador. La aplicación debe validar el mensaje y asignar
puntaje basados en la velocidad (tres niveles) y coincidencia de caracteres.
Posteriormente debe haber cambio de turno.

## 5. Cómo ingresar Morse (Jugador A en PC)

| Acción | Resultado |
|--------|-----------|
| Presionar "Espacio" < 400 ms | Punto "." |
| Presionar "Espacio" ≥ 400 ms | Raya "-" |
| Presionar "Enter" | Confirmar letra actual |
| Presionar "Esperar 1 segundo" | Enviar frase completa |

## 6. Cómo ingresar Morse (Jugador B en maqueta)

| Acción | Resultado |
|--------|-----------|
| Presión corta del botón | Punto "." |
| Presión larga del botón (≥ 2× unidad) | Raya "-" |
| Pausa de 3 unidades | Fin de carácter |
| Pausa de 7 unidades | Fin de frase |

El buzzer suena durante toda la presión del botón como retroalimentación.


## 7. Pines del hardware (según diagrama)

| Función | GPIO |
|---------|------|
| CLK (74HC164) | GP26 |
| DATA (74HC164) | GP27 |
| CLR (74HC164) | Conectado a la fuente de poder |
| Botón Morse | GP16 (PULL_DOWN) |
| DIP-switch modo | GP15 (PULL_DOWN) |
| Buzzer (PWM) | GP05 |

## 8. Temporización Morse

| Elemento | Unidad A (ms) | Unidad B (ms) |
|----------|-------------- |--------------|
| Punto    | 200           | 300 |
| Raya     | 600           | 900 |
| Pausa entre símbolos | 200 | 300 |
| Pausa entre letras | 600 | 900 |
| Pausa entre palabras | 1400 | 2100 |

Se puede configurar "UNIDAD_MS" en "morse_input.py" y "game_logic.py".

## 9. Protocolo de mensajes TCP

PC  -> Pico : FRASE:<texto>      # envía la frase a mostrar
Pico -> PC  : LISTO              # Pico listo para recibir
Pico -> PC  : RESP:<texto>       # respuesta del jugador B
PC  -> Pico : PUNTAJE:<n>        # puntaje calculado (opcional)

