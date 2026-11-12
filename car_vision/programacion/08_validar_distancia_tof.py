#!/usr/bin/env python3
"""Validacion de la distancia monocular contra el VL53L1X (Semana 5: minimo 10 posiciones).

Montaje: robot quieto. Pon la anomalia (bache o reductor) delante y, en su borde cercano,
una tablita vertical (carton de 10 x 10 cm) para que el VL53L1X tenga donde medir.
El VL53L1X debe mirar HORIZONTAL para esta prueba (TOF_INCLINACION_DEG = 0 en config.py).

ESPACIO = medir esta posicion (15 cuadros de camara + 15 lecturas del ToF, se usa la mediana)
q = terminar y calcular MAE y RMSE
Guarda datos/validacion_distancia.csv"""
import csv
import math
import os
import statistics as st
import time

import cv2

import config
from esp32_link import ESP32
from vision import Camara, Detector, Distancia, dibujar, principal, texto, tof_horizontal_m

os.makedirs(config.CARPETA_DATOS, exist_ok=True)
archivo = os.path.join(config.CARPETA_DATOS, "validacion_distancia.csv")
cam, det, dist = Camara(), Detector(), Distancia()
robot = ESP32()
if not dist.calibrada:
    print("[AVISO] Falta calib_distancia.json: corre antes 07_calibrar_distancia.py")
filas, n = [], -1


def medir():
    est, tof, conf, clase, n_ = [], [], [], None, -1
    for _ in range(15):
        n_, img, _ = cam.leer(n_)
        dets, _ = det.detectar(img)
        p = principal(dets)
        if p:
            m = dist.metros(p["y2"])
            if m:
                est.append(m); conf.append(p["conf"]); clase = p["anomalia"]
        t = tof_horizontal_m(robot.tel.get("tof_mm"))
        if t and robot.tel.get("tof_estado") == 0:
            tof.append(t)
    return est, tof, conf, clase


try:
    while True:
        n, img, _ = cam.leer(n)
        if img is None:
            continue
        dets, ms = det.detectar(img)
        p = principal(dets)
        dibujar(img, dets, dist, p)
        t = tof_horizontal_m(robot.tel.get("tof_mm"))
        texto(img, [f"posiciones medidas: {len(filas)} (minimo 10)",
                    f"camara: {dist.metros(p['y2']) * 100:.1f} cm" if p and dist.metros(p["y2"]) else "camara: sin anomalia",
                    f"ToF: {t * 100:.1f} cm" if t else "ToF: sin lectura",
                    "ESPACIO medir   q terminar"])
        cv2.imshow("Validacion distancia", img)
        k = cv2.waitKey(1) & 0xFF
        if k == ord(" "):
            est, tof, conf, clase = medir()
            if len(est) < 8 or len(tof) < 8:
                print(f"  No valida: camara {len(est)}/15, ToF {len(tof)}/15 lecturas. Acomoda y repite.")
                continue
            e, r = st.median(est), st.median(tof)
            s = input(f"  [{len(filas) + 1}] camara {e * 100:.1f} cm | ToF {r * 100:.1f} cm | "
                      f"cinta (cm, Enter = no medi): ").strip().replace(",", ".")
            cinta = float(s) / 100 if s else ""
            filas.append([time.strftime("%Y-%m-%d %H:%M:%S"), len(filas) + 1, clase, round(st.mean(conf), 3),
                          round(e, 4), round(st.pstdev(est), 4), round(r, 4), round(st.pstdev(tof), 4), cinta,
                          round(e - r, 4), robot.tel.get("lux")])
        elif k == ord("q"):
            break
finally:
    robot.cerrar(); cam.cerrar(); cv2.destroyAllWindows()

if filas:
    nuevo = not os.path.exists(archivo)
    with open(archivo, "a", newline="") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "pos", "clase", "conf_media", "d_camara_m", "desv_camara_m", "d_tof_m", "desv_tof_m",
                        "d_cinta_m", "error_m", "lux"])
        w.writerows(filas)
    err = [f[9] for f in filas]
    mae = st.mean(abs(x) for x in err)
    rmse = math.sqrt(st.mean(x * x for x in err))
    print(f"\n{len(filas)} posiciones | camara vs VL53L1X: MAE {mae * 100:.2f} cm, RMSE {rmse * 100:.2f} cm, "
          f"sesgo {st.mean(err) * 100:+.2f} cm")
    print(f"Guardado en {archivo}")
