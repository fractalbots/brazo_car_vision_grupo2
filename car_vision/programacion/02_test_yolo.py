#!/usr/bin/env python3
"""Prueba de YOLO11n en la Pi 5 con la C270.
La primera vez descarga yolo11n.pt (modelo general COCO) y lo convierte a NCNN.
No detecta baches todavia: sirve para comprobar que todo funciona y medir la velocidad.
Cuando tengas tu modelo entrenado, cambia MODELO por la carpeta de tu modelo NCNN."""
import os
import time
import cv2
from ultralytics import YOLO

MODELO = "yolo11n_ncnn_model"
IMGSZ = 640

if not os.path.isdir(MODELO):
    print("Convirtiendo yolo11n a NCNN (solo la primera vez, ~1 min)...")
    YOLO("yolo11n.pt").export(format="ncnn", imgsz=IMGSZ)
model = YOLO(MODELO, task="detect")

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

tiempos = []
while True:
    ok, frame = cap.read()
    if not ok:
        break
    t = time.perf_counter()
    res = model(frame, imgsz=IMGSZ, verbose=False)[0]
    ms = (time.perf_counter() - t) * 1000
    tiempos = (tiempos + [ms])[-30:]
    vista = res.plot()
    prom = sum(tiempos) / len(tiempos)
    cv2.putText(vista, f"inferencia {prom:.0f} ms  ({1000 / prom:.1f} FPS)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("YOLO11n NCNN", vista)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
cap.release(); cv2.destroyAllWindows()
print(f"Promedio ultimos 30 cuadros: {sum(tiempos) / len(tiempos):.1f} ms")
