#!/usr/bin/env python3
"""Calibra la distancia monocular (una vez, con la camara ya en su posicion definitiva).

1. Robot quieto en la pista. Pega tiras de cinta en el suelo, delante de la camara, a
   distancias conocidas medidas desde el punto del suelo justo DEBAJO de la camara
   (usa una plomada o una escuadra): por ejemplo 25, 35, 50, 70, 100, 130 cm.
2. Corre este programa. Haz clic sobre el borde de cada cinta (el lado cercano al robot)
   y escribe su distancia en cm en la terminal.
3. Con 5 puntos o mas, pulsa c: calcula altura e inclinacion de la camara y guarda
   calib_distancia.json, que usan los demas programas.
   u = borrar el ultimo punto     q = salir sin guardar"""
import json
import math

import cv2
import numpy as np

import config
from vision import Camara, Distancia, texto

puntos = []          # (fila_px, distancia_m)
clic = []


def raton(ev, x, y, *_):
    if ev == cv2.EVENT_LBUTTONDOWN:
        clic.append(y)


def ajustar(pts, cy):
    v = np.array([p[0] for p in pts], float)
    d = np.array([p[1] for p in pts], float)
    mejor = None
    for fy in np.arange(600, 1000, 5):
        alfa = np.arctan((v - cy) / fy)
        for tilt in np.radians(np.arange(5, 60, 0.1)):
            ang = tilt + alfa
            if np.any(ang <= 0.01):
                continue
            g = 1 / np.tan(ang)
            h = (d @ g) / (g @ g)                 # minimos cuadrados para h
            err = np.sqrt(np.mean((h * g - d) ** 2))
            if mejor is None or err < mejor[0]:
                mejor = (err, h, math.degrees(tilt), fy)
    return mejor


cam = Camara()
cv2.namedWindow("Calibracion")
cv2.setMouseCallback("Calibracion", raton)
n = -1
cy = config.ALTO / 2
while True:
    n, img, _ = cam.leer(n)
    if img is None:
        continue
    for v, d in puntos:
        cv2.line(img, (0, int(v)), (img.shape[1], int(v)), (0, 255, 0), 1)
        cv2.putText(img, f"{d * 100:.0f} cm", (img.shape[1] - 90, int(v) - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    texto(img, [f"puntos: {len(puntos)}  (clic en el borde de cada cinta)", "c = calcular y guardar   u = borrar   q = salir"])
    cv2.imshow("Calibracion", img)
    k = cv2.waitKey(1) & 0xFF
    if clic:
        v = clic.pop()
        s = input(f"Fila {v}: distancia de esa cinta en cm (Enter = cancelar): ").strip().replace(",", ".")
        if s:
            puntos.append((v, float(s) / 100))
    if k == ord("u") and puntos:
        puntos.pop()
    elif k == ord("q"):
        break
    elif k == ord("c"):
        if len(puntos) < 5:
            print("Faltan puntos: minimo 5.")
            continue
        err, h, tilt, fy = ajustar(puntos, cy)
        datos = dict(h_m=round(float(h), 4), tilt_deg=round(tilt, 2), fy_px=float(fy), cy_px=cy,
                     error_rms_cm=round(float(err) * 100, 2), puntos=[[float(v), d] for v, d in puntos])
        with open(config.CALIBRACION, "w") as f:
            json.dump(datos, f, indent=2)
        print(f"\nCamara a {h * 100:.1f} cm del suelo, inclinada {tilt:.1f} grados, fy {fy:.0f} px")
        print(f"Error de ajuste: {err * 100:.1f} cm (RMS). Guardado en {config.CALIBRACION}")
        dist = Distancia()
        for v, d in puntos:
            print(f"   cinta {d * 100:6.1f} cm -> modelo {dist.metros(v) * 100:6.1f} cm")
        break
cam.cerrar()
cv2.destroyAllWindows()
