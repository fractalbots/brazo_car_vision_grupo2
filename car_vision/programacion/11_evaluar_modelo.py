#!/usr/bin/env python3
"""mAP, Precision, Recall y matriz de confusion del modelo sobre el conjunto de PRUEBA.

  python 11_evaluar_modelo.py --datos dataset_yolo/data.yaml
  python 11_evaluar_modelo.py --datos dataset_yolo/data.yaml --modelo modelos/best_ncnn_model

data.yaml es el que exporta Roboflow (formato YOLOv11) con train/valid/test.
Los resultados (matriz de confusion, curvas PR) quedan en runs/detect/val*/"""
import argparse

from ultralytics import YOLO

import config

ap = argparse.ArgumentParser()
ap.add_argument("--datos", required=True)
ap.add_argument("--modelo", default=config.MODELO)
ap.add_argument("--split", default="test")
a = ap.parse_args()

m = YOLO(a.modelo, task="detect").val(data=a.datos, split=a.split, imgsz=config.IMGSZ, batch=1, plots=True)
print("\n=== RESULTADOS en", a.split, "===")
print(f"mAP50     {m.box.map50:.3f}")
print(f"mAP50-95  {m.box.map:.3f}")
print(f"Precision {m.box.mp:.3f}")
print(f"Recall    {m.box.mr:.3f}")
for i, c in enumerate(m.box.ap_class_index):
    print(f"  {m.names[c]:10s} AP50 {m.box.ap50[i]:.3f}  P {m.box.p[i]:.3f}  R {m.box.r[i]:.3f}")
print(f"Velocidad: {m.speed}")
print(f"Graficas y matriz de confusion en: {m.save_dir}")
