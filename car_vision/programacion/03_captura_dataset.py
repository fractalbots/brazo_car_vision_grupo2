#!/usr/bin/env python3
"""Captura de fotos para el dataset (minimo 300, balanceadas entre clases).
Cada foto se guarda en dataset/<clase>/ con fecha y hora en el nombre.
Teclas:
  n = superficie normal    b = bache    r = reductor
  a = modo automatico: 1 foto cada 0.5 s de la ULTIMA clase elegida (para tomar en movimiento)
  q = salir
Toma fotos con distinta luz, distancia y posicion de la anomalia: eso hace al modelo robusto."""
import os
import time
import cv2

CLASES = {ord("n"): "normal", ord("b"): "bache", ord("r"): "reductor"}
BASE = "dataset"
for c in CLASES.values():
    os.makedirs(os.path.join(BASE, c), exist_ok=True)

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

def contar():
    return {c: len(os.listdir(os.path.join(BASE, c))) for c in CLASES.values()}

def guardar(frame, clase):
    nombre = os.path.join(BASE, clase, f"{clase}_{time.strftime('%Y%m%d_%H%M%S')}_{int(time.time()*1000) % 1000:03d}.jpg")
    cv2.imwrite(nombre, frame)

clase, auto, ultimo = "normal", False, 0.0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    if auto and time.time() - ultimo >= 0.5:
        guardar(frame, clase); ultimo = time.time()
    vista = frame.copy()
    cnt = contar()
    txt = "  ".join(f"{k}:{v}" for k, v in cnt.items()) + f"  | total {sum(cnt.values())}"
    cv2.putText(vista, txt, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    cv2.putText(vista, f"clase: {clase}  auto: {'SI' if auto else 'no'}", (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)
    cv2.imshow("Captura dataset", vista)
    k = cv2.waitKey(1) & 0xFF
    if k in CLASES:
        clase = CLASES[k]; guardar(frame, clase)
    elif k == ord("a"):
        auto = not auto
    elif k == ord("q"):
        break
cap.release(); cv2.destroyAllWindows()
print("Fotos por clase:", contar())
