"""Enlace Raspberry Pi <-> ESP32 por el cable USB.

Uso:
    from esp32_link import ESP32
    with ESP32() as robot:
        robot.vel(0.3, 0)          # 0.3 m/s recto (mandar seguido: watchdog de 0.5 s)
        print(robot.tel)           # ultima telemetria (dict)
        robot.frena()
"""
import glob
import queue
import threading
import time

import serial

import config

CAMPOS = ["ms", "modo", "motivo", "v_izq", "v_der", "ref_izq", "ref_der", "x", "y", "th_deg", "dist",
          "tof_mm", "tof_estado", "lux", "us_cm", "ir1", "ir2", "ir3", "bat_v"]
TEXTO = {"modo", "motivo"}
ENTERO = {"ms", "tof_mm", "tof_estado", "ir1", "ir2", "ir3"}


def buscar_puerto():
    for p in sorted(glob.glob("/dev/ttyUSB*")) + sorted(glob.glob("/dev/ttyACM*")):
        return p
    raise RuntimeError("No encuentro el ESP32. Revisa el cable USB (debe ser de datos) y: ls /dev/ttyUSB*")


class ESP32:
    def __init__(self, puerto=None, baudios=None, eco=False):
        self.puerto = puerto or config.PUERTO or buscar_puerto()
        self.ser = serial.Serial(self.puerto, baudios or config.BAUDIOS, timeout=0.1)
        self.tel = {}
        self.t_tel = 0.0
        self.eventos = queue.Queue()
        self.eco = eco
        self._vivo = True
        self._lock = threading.Lock()
        self._hilo = threading.Thread(target=self._leer, daemon=True)
        self._hilo.start()
        # al abrir el puerto el ESP32 se reinicia: esperar a que diga LISTO
        if not self.esperar("LISTO", 4.0):
            if self.ping() is None:
                raise RuntimeError(f"El ESP32 en {self.puerto} no responde. ¿Cargaste robot_esp32.ino?")
        self.esperar_tel(2.0)

    # ---------------- lectura ----------------
    def _leer(self):
        while self._vivo:
            try:
                linea = self.ser.readline().decode("utf-8", "replace").strip()
            except (serial.SerialException, OSError):
                break
            if not linea:
                continue
            if linea.startswith("T,"):
                p = linea.split(",")[1:]
                if len(p) == len(CAMPOS):
                    d = {}
                    for k, v in zip(CAMPOS, p):
                        try:
                            d[k] = v if k in TEXTO else (int(v) if k in ENTERO else float(v))
                        except ValueError:
                            d[k] = None
                    self.tel = d
                    self.t_tel = time.time()
            else:
                if self.eco or linea.startswith(("ALERTA", "ERR", "DIAG")):
                    print("[ESP32]", linea)
                self.eventos.put((time.time(), linea))

    def esperar(self, prefijo, timeout=2.0):
        """Espera una linea del ESP32 que empiece con prefijo. Devuelve la linea o None."""
        fin = time.time() + timeout
        while time.time() < fin:
            try:
                _, l = self.eventos.get(timeout=max(0.01, fin - time.time()))
            except queue.Empty:
                return None
            if l.startswith(prefijo):
                return l
        return None

    def esperar_tel(self, timeout=2.0):
        fin = time.time() + timeout
        while time.time() < fin:
            if self.tel:
                return True
            time.sleep(0.02)
        return False

    def vaciar(self):
        while not self.eventos.empty():
            self.eventos.get_nowait()

    # ---------------- escritura ----------------
    def enviar(self, texto):
        with self._lock:
            self.ser.write((texto + "\n").encode())

    def vel(self, v, w=0.0):
        """v en m/s (adelante +), w en rad/s (izquierda +). Repetir cada < 0.5 s."""
        self.enviar(f"V {v:.3f} {w:.3f}")

    def ruedas(self, v_izq, v_der):
        self.enviar(f"M {v_izq:.3f} {v_der:.3f}")

    def frena(self):
        self.enviar("S")

    def pwm(self, izq, der):
        self.enviar(f"PWM {int(izq)} {int(der)}")

    def faros(self, encendido=True):
        self.enviar(f"FAROS {1 if encendido else 0}")

    def reset_odometria(self):
        self.vaciar()
        self.enviar("RST")
        self.esperar("OK RST", 1.0)
        time.sleep(0.1)

    def anticolision(self, activa=True, cm=0):
        self.enviar(f"ANTI {1 if activa else 0} {cm}")

    def ping(self, n=0, timeout=0.5):
        """Ida y vuelta en ms, o None."""
        self.vaciar()
        t0 = time.perf_counter()
        self.enviar(f"PING {n}")
        l = self.esperar(f"PONG {n}", timeout)
        return None if l is None else (time.perf_counter() - t0) * 1000

    def contadores(self):
        self.vaciar()
        self.enviar("CNT")
        l = self.esperar("CNT", 1.0)
        return None if l is None else tuple(int(x) for x in l.split()[1:3])

    def recto(self, metros, v=0.3, timeout=None):
        """Avanza 'metros' con correccion de rumbo. Devuelve (dist_encoder_m, desvio_rumbo_deg)."""
        self.vaciar()
        self.enviar(f"RECTO {metros:.3f} {v:.3f}")
        l = self.esperar("FIN RECTO", timeout or abs(metros) / max(v, 0.05) * 2 + 5)
        if l is None:
            self.frena()
            return None
        _, _, d, th = l.split()
        return float(d), float(th)

    def giro(self, grados, w=1.5, timeout=10):
        """Gira en el sitio (+ izquierda). Devuelve el angulo medido por encoders."""
        self.vaciar()
        self.enviar(f"GIRO {grados:.2f} {w:.2f}")
        l = self.esperar("FIN GIRO", timeout)
        if l is None:
            self.frena()
            return None
        return float(l.split()[2])

    def cerrar(self):
        try:
            self.frena()
            time.sleep(0.05)
        except Exception:
            pass
        self._vivo = False
        self.ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.cerrar()


if __name__ == "__main__":
    with ESP32(eco=True) as r:
        print("Conectado en", r.puerto)
        for i in range(5):
            print(f"ping {i}: {r.ping(i):.1f} ms")
        print("Telemetria:", r.tel)
