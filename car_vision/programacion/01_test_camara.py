#!/usr/bin/env python3
"""Prueba de la Logitech C270: abre la camara a 640x480 y muestra los FPS.
Teclas:  s = guardar foto   q = salir"""
import time
import cv2

ANCHO, ALTO = 640, 480          # resolucion FIJA de toda la campana (lo exige la guia)

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO)
cap.set(cv2.CAP_PROP_FPS, 30)
if not cap.isOpened():
    raise SystemExit("No se abre la camara. Revisa el cable USB y prueba:  v4l2-ctl --list-devices")

print("Resolucion real:", int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), "x", int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
n, t0, fps = 0, time.time(), 0.0
while True:
    ok, frame = cap.read()
    if not ok:
        print("Se perdio la camara (revisa alimentacion y cable)"); break
    n += 1
    if time.time() - t0 >= 1.0:
        fps, n, t0 = n / (time.time() - t0), 0, time.time()
    cv2.putText(frame, f"{fps:.1f} FPS", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    cv2.imshow("C270", frame)
    k = cv2.waitKey(1) & 0xFF
    if k == ord("s"):
        nombre = f"foto_{int(time.time())}.jpg"; cv2.imwrite(nombre, frame); print("guardada", nombre)
    elif k == ord("q"):
        break
cap.release(); cv2.destroyAllWindows()
