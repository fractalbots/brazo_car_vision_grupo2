# =====================================================================
#  ENTRENAR YOLO11n EN GOOGLE COLAB (gratis, con GPU)
#  Colab: Entorno de ejecucion > Cambiar tipo > GPU T4.
#  Copia cada bloque "# %% CELDA" en una celda de Colab y ejecutalas en orden.
#
#  Antes: etiqueta las fotos de 03_captura_dataset.py en Roboflow
#    - clases: bache, reductor
#    - las fotos de superficie NORMAL se suben SIN etiquetas (son "fondo"):
#      asi el modelo aprende que ahi no hay nada. Normal = ninguna deteccion.
#    - division 70 / 20 / 10 (train / valid / test)
#    - Export > formato "YOLOv11" > descargar zip
# =====================================================================

# %% CELDA 1: instalar
# !pip -q install ultralytics

# %% CELDA 2: subir el zip de Roboflow
# from google.colab import files
# files.upload()                       # elige el zip
# !unzip -q -o *.zip -d dataset
# !cat dataset/data.yaml

# %% CELDA 3: entrenar (unos 20-40 min)
from ultralytics import YOLO

modelo = YOLO("yolo11n.pt")
modelo.train(data="dataset/data.yaml", imgsz=640, epochs=100, patience=25, batch=16,
             hsv_v=0.5,          # mas variacion de brillo: ayuda con los 3 niveles de luz
             degrees=0, flipud=0.0, fliplr=0.5)

# %% CELDA 4: evaluar en el conjunto de PRUEBA (mAP, matriz de confusion)
mejor = YOLO("runs/detect/train/weights/best.pt")
m = mejor.val(data="dataset/data.yaml", split="test", imgsz=640)
print("mAP50", m.box.map50, "mAP50-95", m.box.map, "P", m.box.mp, "R", m.box.mr)

# %% CELDA 5: descargar el modelo
# files.download("runs/detect/train/weights/best.pt")

# =====================================================================
#  EN LA RASPBERRY (con el entorno activado), en la carpeta raspberry/:
#     mkdir -p modelos && mv ~/Descargas/best.pt modelos/
#     yolo export model=modelos/best.pt format=ncnn imgsz=640
#  Eso crea modelos/best_ncnn_model, que es el que usa config.py.
# =====================================================================
