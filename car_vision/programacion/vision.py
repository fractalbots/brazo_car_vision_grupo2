"""Camara, detector YOLO (NCNN) y distancia monocular por plano del suelo."""
import json
import math
import os
import threading
import time

import cv2

import config


# ===================== CAMARA (siempre el cuadro mas nuevo) =====================
class Camara:
    """Lee la C270 en un hilo aparte: asi el robot nunca procesa un cuadro viejo.
    Tambien acepta un video (ruta .mp4) para probar sin robot."""

    def __init__(self, fuente=None):
        fuente = config.CAMARA if fuente is None else fuente
        self.es_video = isinstance(fuente, str)
        if self.es_video:
            self.cap = cv2.VideoCapture(fuente)
        else:
            self.cap = cv2.VideoCapture(fuente, cv2.CAP_V4L2)
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.ANCHO)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.ALTO)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not self.cap.isOpened():
            raise RuntimeError("No se abre la camara. Revisa: v4l2-ctl --list-devices")
        self.cuadro, self.t, self.n = None, 0.0, 0
        self._vivo = True
        if self.es_video:          # un video se lee cuadro por cuadro, sin saltarse ninguno
            return
        self._ev = threading.Event()
        threading.Thread(target=self._bucle, daemon=True).start()
        if not self._ev.wait(5):
            raise RuntimeError("La camara no entrega imagen")

    def _bucle(self):
        while self._vivo:
            ok, f = self.cap.read()
            if not ok:
                time.sleep(0.01)
                continue
            if f.shape[1] != config.ANCHO or f.shape[0] != config.ALTO:
                f = cv2.resize(f, (config.ANCHO, config.ALTO))
            self.cuadro, self.t = f, time.time()
            self.n += 1
            self._ev.set()

    def leer(self, n_anterior=-1, timeout=1.0):
        """Devuelve (n, cuadro, t) con un cuadro distinto al n_anterior."""
        if self.es_video:
            ok, f = self.cap.read() if self._vivo else (False, None)
            if not ok:
                self._vivo = False
                return n_anterior, None, 0
            self.n += 1
            return self.n, cv2.resize(f, (config.ANCHO, config.ALTO)), time.time()
        fin = time.time() + timeout
        while self.n == n_anterior and time.time() < fin and self._vivo:
            time.sleep(0.002)
        if self.n == n_anterior:
            return n_anterior, None, 0
        return self.n, self.cuadro.copy(), self.t

    @property
    def activa(self):
        return self._vivo

    def cerrar(self):
        self._vivo = False
        time.sleep(0.05)
        self.cap.release()


# ===================== DETECTOR =====================
class Detector:
    def __init__(self, modelo=None):
        from ultralytics import YOLO
        modelo = modelo or config.MODELO
        if not os.path.exists(modelo):
            if modelo.endswith(".pt"):
                pass
            elif os.path.exists(config.MODELO_PRUEBA):
                print(f"[AVISO] No existe {modelo}. Uso el modelo general {config.MODELO_PRUEBA} (no detecta baches).")
                modelo = config.MODELO_PRUEBA
            else:
                print("[AVISO] No hay modelo entrenado: convierto yolo11n general a NCNN (1 min)...")
                YOLO("yolo11n.pt").export(format="ncnn", imgsz=config.IMGSZ)
                modelo = config.MODELO_PRUEBA
        self.ruta = modelo
        self.model = YOLO(modelo, task="detect")
        self.nombres = self.model.names if isinstance(self.model.names, dict) else dict(enumerate(self.model.names))
        # calentar (las primeras inferencias son lentas)
        import numpy as np
        vacio = np.zeros((config.ALTO, config.ANCHO, 3), np.uint8)
        for _ in range(3):
            self.model(vacio, imgsz=config.IMGSZ, verbose=False)

    def anomalia(self, nombre):
        return config.ALIAS_CLASES.get(str(nombre).lower().replace(" ", "_").replace("-", "_"))

    def detectar(self, cuadro):
        """Devuelve (lista de detecciones, ms de inferencia).
        Cada deteccion: dict(clase, anomalia, conf, x1, y1, x2, y2)."""
        t = time.perf_counter()
        r = self.model(cuadro, imgsz=config.IMGSZ, conf=0.25, verbose=False)[0]
        ms = (time.perf_counter() - t) * 1000
        dets = []
        for b in r.boxes:
            c = int(b.cls[0])
            x1, y1, x2, y2 = (float(v) for v in b.xyxy[0])
            nombre = self.nombres.get(c, str(c))
            dets.append(dict(clase=nombre, anomalia=self.anomalia(nombre), conf=float(b.conf[0]),
                             x1=x1, y1=y1, x2=x2, y2=y2))
        return dets, ms


def principal(dets, conf_min=None):
    """La anomalia que importa: la mas cercana (borde inferior mas abajo en la imagen)."""
    conf_min = config.CONF_MIN if conf_min is None else conf_min
    validas = [d for d in dets if d["anomalia"] and d["conf"] >= conf_min]
    return max(validas, key=lambda d: d["y2"]) if validas else None


# ===================== DISTANCIA MONOCULAR =====================
class Distancia:
    """Modelo de plano del suelo (camara pinhole a altura h, inclinada 'tilt' hacia abajo):
        alfa = atan((v - cy) / fy)        angulo del pixel bajo el eje optico
        d    = h / tan(tilt + alfa)        distancia horizontal camara -> punto del suelo
    Se usa el borde INFERIOR de la caja (y2): el punto de la anomalia mas cercano al robot."""

    def __init__(self, archivo=None):
        self.h, self.tilt_deg, self.fy, self.cy = (config.CAM_ALTURA_M, config.CAM_INCLINACION_DEG,
                                                    config.CAM_FY_PX, config.ALTO / 2)
        self.calibrada = False
        archivo = archivo or config.CALIBRACION
        if os.path.exists(archivo):
            with open(archivo) as f:
                c = json.load(f)
            self.h, self.tilt_deg, self.fy, self.cy = c["h_m"], c["tilt_deg"], c["fy_px"], c["cy_px"]
            self.calibrada = True

    def metros(self, v_px):
        ang = math.radians(self.tilt_deg) + math.atan((v_px - self.cy) / self.fy)
        if ang <= math.radians(1.0):          # por encima del horizonte: no es suelo
            return None
        return self.h / math.tan(ang)

    def fila(self, d_m):
        """Fila de la imagen donde cae una distancia (para dibujar la regla)."""
        ang = math.atan(self.h / d_m) - math.radians(self.tilt_deg)
        return self.cy + self.fy * math.tan(ang)


def tof_horizontal_m(tof_mm):
    """Lectura del VL53L1X convertida a distancia horizontal desde la camara."""
    if tof_mm is None or tof_mm <= 0:
        return None
    return tof_mm / 1000 * math.cos(math.radians(config.TOF_INCLINACION_DEG)) + config.TOF_DESFASE_M


# ===================== DIBUJO =====================
COLORES = {"bache": (0, 0, 255), "reductor": (0, 200, 255), None: (160, 160, 160)}


def dibujar(img, dets, dist=None, resaltar=None):
    for d in dets:
        col = COLORES.get(d["anomalia"], (160, 160, 160))
        grosor = 3 if d is resaltar else 1
        cv2.rectangle(img, (int(d["x1"]), int(d["y1"])), (int(d["x2"]), int(d["y2"])), col, grosor)
        txt = f'{d["clase"]} {d["conf"]:.2f}'
        if dist and d["anomalia"]:
            m = dist.metros(d["y2"])
            if m:
                txt += f" {m * 100:.0f}cm"
        cv2.putText(img, txt, (int(d["x1"]), max(15, int(d["y1"]) - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)
    if dist:  # regla de distancias en el borde izquierdo
        for cm in (30, 50, 75, 100, 150):
            y = dist.fila(cm / 100)
            if 0 < y < img.shape[0]:
                cv2.line(img, (0, int(y)), (25, int(y)), (255, 255, 255), 1)
                cv2.putText(img, f"{cm}", (28, int(y) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    return img


def texto(img, lineas, x=10, y=20, color=(0, 255, 0)):
    for i, l in enumerate(lineas):
        cv2.putText(img, l, (x, y + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 4)
        cv2.putText(img, l, (x, y + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
