#!/bin/bash
# =====================================================================
#  Instalacion de la Raspberry Pi 5 - Robot de inspeccion vial UTI 2026B
#  Uso:  bash setup_pi.sh      (tarda 15-25 min, necesita internet)
# =====================================================================
set -e
echo "== 1/6 Actualizando el sistema =="
sudo apt update
sudo apt full-upgrade -y

echo "== 2/6 Paquetes del sistema =="
# python3-venv: entorno aislado | v4l-utils: revisar la camara
# libgl1: lo pide OpenCV | git, htop: utilidades
sudo apt install -y python3-venv python3-dev python3-pip git v4l-utils libgl1 htop

echo "== 3/6 Camara: que Linux no la ponga a dormir =="
if ! grep -q "usbcore.autosuspend=-1" /boot/firmware/cmdline.txt; then
  sudo sed -i 's/$/ usbcore.autosuspend=-1/' /boot/firmware/cmdline.txt
fi

echo "== 4/6 Permisos para el puerto serie (ESP32) y la camara =="
sudo usermod -aG dialout,video "$USER"

echo "== 5/6 Entorno de Python del robot =="
mkdir -p ~/robot
python3 -m venv ~/robot/venv
source ~/robot/venv/bin/activate
pip install --upgrade pip wheel
# ultralytics trae: torch (CPU), opencv-python, numpy, matplotlib, pandas
# ncnn: el formato mas rapido para YOLO en la Pi 5
# pyserial: hablar con el ESP32 por el cable USB
pip install ultralytics ncnn pyserial

echo "== 6/6 Comprobacion =="
python - <<'PY'
import cv2, numpy, serial, ultralytics, torch
print("OpenCV     ", cv2.__version__)
print("NumPy      ", numpy.__version__)
print("Ultralytics", ultralytics.__version__)
print("Torch      ", torch.__version__)
print("PySerial   ", serial.__version__)
print("TODO OK")
PY
echo
echo "Listo. REINICIA la Raspberry:  sudo reboot"
echo "Despues, cada vez que trabajes:  source ~/robot/venv/bin/activate"
