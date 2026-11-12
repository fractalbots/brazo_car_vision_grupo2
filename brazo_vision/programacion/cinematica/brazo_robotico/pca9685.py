# -*- coding: utf-8 -*-
"""
Driver del PCA9685 por I2C, escrito a nivel de registro.

Se maneja directo con smbus2 en vez de una libreria de terceros para que
puedas explicar en el documento exactamente que se le escribe al chip.

Conexion a la Raspberry Pi:
    PCA9685 VCC  -> Pi pin 1  (3.3 V)   <-- logica, NO 5 V
    PCA9685 GND  -> Pi pin 6  (GND)
    PCA9685 SDA  -> Pi pin 3  (GPIO 2)
    PCA9685 SCL  -> Pi pin 5  (GPIO 3)
    PCA9685 V+   -> fuente de 6 V de los servos (bornera, NO la Pi)
    GND de la fuente de servos -> GND comun con la Pi

Habilitar I2C:  sudo raspi-config -> Interface Options -> I2C -> Yes
Verificar:      i2cdetect -y 1      (debe aparecer 40)
"""

import time

try:
    from smbus2 import SMBus
except ImportError:                     # permite importar el modulo en PC
    SMBus = None

# --- registros del PCA9685 (hoja de datos NXP) ---
MODE1        = 0x00
MODE2        = 0x01
PRESCALE     = 0xFE
LED0_ON_L    = 0x06
ALL_LED_ON_L = 0xFA

# --- bits de MODE1 / MODE2 ---
RESTART = 0x80
AI      = 0x20      # auto incremento de registro
SLEEP   = 0x10
ALLCALL = 0x01
OUTDRV  = 0x04      # salidas totem-pole

OSC_HZ = 25_000_000  # oscilador interno. Algunos clones traen 27 MHz:
                     # si los pulsos salen corridos, ajusta este valor.


class PCA9685:
    def __init__(self, bus=1, direccion=0x40, frecuencia=50, osc_hz=OSC_HZ):
        if SMBus is None:
            raise RuntimeError("Falta smbus2:  pip install smbus2")
        self.bus = SMBus(bus)
        self.dir = direccion
        self.osc = osc_hz
        self.frecuencia = frecuencia

        self._w(MODE1, ALLCALL)
        self._w(MODE2, OUTDRV)
        time.sleep(0.005)
        self.apagar_todos()
        self.set_frecuencia(frecuencia)

    # ---------- acceso crudo ----------
    def _w(self, reg, val):
        self.bus.write_byte_data(self.dir, reg, val & 0xFF)

    def _r(self, reg):
        return self.bus.read_byte_data(self.dir, reg)

    # ---------- configuracion ----------
    def set_frecuencia(self, hz):
        """Los servos analogicos y digitales de hobby trabajan a 50 Hz."""
        prescale = int(round(self.osc / (4096.0 * hz))) - 1
        prescale = max(3, min(255, prescale))
        viejo = self._r(MODE1)
        self._w(MODE1, (viejo & ~RESTART) | SLEEP)   # hay que dormirlo
        self._w(PRESCALE, prescale)                  # para tocar PRESCALE
        self._w(MODE1, viejo)
        time.sleep(0.005)
        self._w(MODE1, viejo | RESTART | AI)
        self.frecuencia = hz

    # ---------- salidas ----------
    def set_pwm(self, canal, on, off):
        base = LED0_ON_L + 4 * canal
        self.bus.write_i2c_block_data(self.dir, base, [
            on & 0xFF, (on >> 8) & 0x0F, off & 0xFF, (off >> 8) & 0x0F])

    def pulso_us(self, canal, microsegundos):
        """Ancho de pulso en us -> cuentas de 12 bits."""
        cuentas = int(round(microsegundos * self.frecuencia * 4096 / 1_000_000))
        cuentas = max(0, min(4095, cuentas))
        self.set_pwm(canal, 0, cuentas)

    def apagar(self, canal):
        """Deja el canal sin señal: el servo queda libre, sin fuerza."""
        base = LED0_ON_L + 4 * canal
        self.bus.write_i2c_block_data(self.dir, base, [0, 0, 0, 0x10])

    def apagar_todos(self):
        self.bus.write_i2c_block_data(self.dir, ALL_LED_ON_L, [0, 0, 0, 0x10])

    def cerrar(self):
        self.apagar_todos()
        self.bus.close()
