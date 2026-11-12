"""Ajustes del robot. Todo lo que se puede cambiar esta aqui."""
import os

# ---------------- Comunicacion con el ESP32 ----------------
PUERTO = os.environ.get("ROBOT_PUERTO")   # None = lo busca solo (/dev/ttyUSB0 o /dev/ttyACM0)
BAUDIOS = 115200

# ---------------- Camara (fija en toda la campana) ----------------
CAMARA = 0               # /dev/video0
ANCHO, ALTO = 640, 480

# ---------------- Modelo YOLO ----------------
# Cuando entrenes tu modelo, pon aqui la carpeta NCNN que exportaste:
MODELO = "modelos/best_ncnn_model"
MODELO_PRUEBA = "yolo11n_ncnn_model"     # modelo general, solo para probar
IMGSZ = 640
CONF_MIN = 0.50          # confianza minima para aceptar una deteccion
CUADROS_CONFIRMA = 2     # cuadros seguidos para confirmar una anomalia

# Nombre de clase del modelo -> anomalia. Acepta nombres en ingles tambien.
ALIAS_CLASES = {
    "bache": "bache", "pothole": "bache", "hueco": "bache",
    "reductor": "reductor", "speed_bump": "reductor", "speedbump": "reductor",
    "rompevelocidades": "reductor", "resalto": "reductor",
}

# ---------------- Reaccion del robot (Semana 5) ----------------
# bache -> se detiene | reductor -> baja la velocidad y sigue
ACCION = {"bache": "FRENA", "reductor": "LENTO"}
D_FRENA = 0.45           # m: frena si el bache esta a esta distancia o menos
D_LENTO = 0.80           # m: baja la velocidad si el reductor esta a esta distancia
V_LENTO = 0.12           # m/s para pasar el reductor
PASADO_REDUCTOR = 0.35   # m extra despues del reductor antes de volver a acelerar

# ---------------- Niveles de velocidad (Semana 6) ----------------
VELOCIDADES = {"baja": 0.25, "media": 0.50, "alta": 0.75}   # m/s
DISTANCIA_ENSAYO = 3.0   # m: largo de un ensayo si no frena antes

# ---------------- Niveles de iluminacion (Semana 6, medidos con el BH1750) ----------------
# Si la luz medida al empezar el ensayo cae fuera del rango de su nivel, el ensayo se descarta.
NIVELES_LUZ = {"alta": (400, 5000), "media": (120, 400), "baja": (15, 120)}   # lux

# ---------------- Distancia monocular ----------------
CALIBRACION = "calib_distancia.json"
# Valores de arranque si todavia no calibras (se reemplazan con 07_calibrar_distancia.py)
CAM_ALTURA_M = 0.20
CAM_INCLINACION_DEG = 25.0
CAM_FY_PX = 760.0        # C270 a 640x480 (aprox.)

# VL53L1X: inclinacion hacia abajo (0 si lo pones horizontal para validar)
TOF_INCLINACION_DEG = 0.0
TOF_DESFASE_M = 0.0      # si el ToF no esta en la misma vertical que la camara

# ---------------- Carpetas ----------------
CARPETA_DATOS = "datos"
