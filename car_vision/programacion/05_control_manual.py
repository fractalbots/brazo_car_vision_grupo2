#!/usr/bin/env python3
"""Manejo con teclado viendo la camara (sirve para el video de la Semana 2).

  w adelante   s atras   a izquierda   d derecha   ESPACIO parar
  + / -  cambiar velocidad     f faros     r reiniciar odometria
  v  grabar video on/off (datos/manual_*.mp4)      q salir
El robot sigue la ultima orden hasta que pulses ESPACIO (o se corte: watchdog)."""
import os
import time

import cv2

import config
from esp32_link import ESP32
from vision import Camara, texto

os.makedirs(config.CARPETA_DATOS, exist_ok=True)
cam = Camara()
robot = ESP32()
v, mov, faros, grab = 0.25, (0, 0), False, None
n = -1
try:
    while True:
        n, img, _ = cam.leer(n)
        if img is None:
            continue
        robot.vel(mov[0] * v, mov[1] * 2.5 * v / 0.25 if mov[1] else 0)
        t = robot.tel
        texto(img, [f"vel pedida {v:.2f} m/s   {'GRABANDO' if grab else ''}",
                    f"izq {t.get('v_izq', 0):+.2f}  der {t.get('v_der', 0):+.2f} m/s  [{t.get('modo')}/{t.get('motivo')}]",
                    f"x {t.get('x', 0):.2f} m  y {t.get('y', 0):.2f} m  rumbo {t.get('th_deg', 0):.1f} deg",
                    f"ToF {t.get('tof_mm')} mm  luz {t.get('lux', 0):.0f} lx  US {t.get('us_cm', 0):.0f} cm  bat {t.get('bat_v', 0):.1f} V"])
        if grab is not None:
            grab.write(img)
        cv2.imshow("Control manual", img)
        k = cv2.waitKey(1) & 0xFF
        if k == ord("w"): mov = (1, 0)
        elif k == ord("s"): mov = (-1, 0)
        elif k == ord("a"): mov = (0, 1)
        elif k == ord("d"): mov = (0, -1)
        elif k == ord(" "): mov = (0, 0); robot.frena()
        elif k in (ord("+"), ord("=")): v = min(1.0, v + 0.05)
        elif k == ord("-"): v = max(0.05, v - 0.05)
        elif k == ord("f"): faros = not faros; robot.faros(faros)
        elif k == ord("r"): robot.reset_odometria()
        elif k == ord("v"):
            if grab is None:
                nombre = os.path.join(config.CARPETA_DATOS, time.strftime("manual_%Y%m%d_%H%M%S.mp4"))
                grab = cv2.VideoWriter(nombre, cv2.VideoWriter_fourcc(*"mp4v"), 20, (config.ANCHO, config.ALTO))
                print("Grabando", nombre)
            else:
                grab.release(); grab = None
        elif k == ord("q"):
            break
finally:
    robot.cerrar()
    cam.cerrar()
    if grab is not None:
        grab.release()
    cv2.destroyAllWindows()
