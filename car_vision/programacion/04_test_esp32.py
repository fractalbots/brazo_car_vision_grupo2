#!/usr/bin/env python3
"""Prueba de comunicacion Raspberry <-> ESP32 (Semana 3: comunicacion bidireccional).

  python 04_test_esp32.py            ping x50 (latencia), telemetria 5 s, faros
  python 04_test_esp32.py --diag     ademas prueba cada motor y sus encoders (LEVANTA LAS RUEDAS)
  python 04_test_esp32.py --ticks    calibra los pulsos por vuelta de rueda (girando a mano)
Guarda la latencia en datos/comunicacion.csv"""
import argparse
import csv
import os
import statistics
import time

import config
from esp32_link import ESP32

ap = argparse.ArgumentParser()
ap.add_argument("--diag", action="store_true")
ap.add_argument("--ticks", action="store_true")
a = ap.parse_args()
os.makedirs(config.CARPETA_DATOS, exist_ok=True)

with ESP32() as r:
    print(f"Conectado al ESP32 en {r.puerto}\n")

    if a.ticks:
        input("Pega una cinta en cada llanta como marca y presiona Enter para empezar...")
        c0 = r.contadores()
        input("Gira ahora las dos ruedas 10 vueltas hacia adelante y presiona Enter...")
        c1 = r.contadores()
        ti, td = (c1[0] - c0[0]) / 10, (c1[1] - c0[1]) / 10
        print(f"\nPulsos por vuelta:  izquierda {ti:.1f}   derecha {td:.1f}")
        if ti < 0 or td < 0:
            print("Un valor salio NEGATIVO: en robot_esp32.ino cambia INV_ENC_ de ese lado a true.")
        print(f"Pon en robot_esp32.ino:  float TICKS_VUELTA = {(abs(ti) + abs(td)) / 2:.1f}f;  y vuelve a cargarlo.")
        raise SystemExit

    # 1) latencia ida y vuelta
    rtt = []
    for i in range(50):
        t = r.ping(i)
        if t is not None:
            rtt.append(t)
        time.sleep(0.02)
    with open(os.path.join(config.CARPETA_DATOS, "comunicacion.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["n", "rtt_ms"])
        w.writerows(enumerate(rtt))
    print(f"PING: {len(rtt)}/50 respuestas | ida y vuelta media {statistics.mean(rtt):.1f} ms, "
          f"min {min(rtt):.1f}, max {max(rtt):.1f}, desv {statistics.pstdev(rtt):.1f} ms")

    # 2) telemetria
    print("\nTelemetria del ESP32 (5 s):")
    fin = time.time() + 5
    while time.time() < fin:
        t = r.tel
        print(f"  vel izq {t['v_izq']:+.2f} der {t['v_der']:+.2f} m/s | ToF {t['tof_mm']} mm | "
              f"luz {t['lux']:.0f} lx | ultrasonico {str(round(t['us_cm'])) + ' cm' if t['us_cm'] > 0 else 'sin eco'} | IR {t['ir1']}{t['ir2']}{t['ir3']} | "
              f"bateria {t['bat_v']:.2f} V")
        time.sleep(0.5)
    if r.tel.get("tof_mm", -1) < 0:
        print("  [!] VL53L1X sin lectura: revisa J4 (SDA 21, SCL 22) y que el sensor tenga 3V3")
    if r.tel.get("lux", -1) < 0:
        print("  [!] BH1750 sin lectura: revisa J4")

    # 3) orden y respuesta: faros
    print("\nFaros: parpadeo x3")
    for _ in range(3):
        r.faros(True); time.sleep(0.3); r.faros(False); time.sleep(0.3)

    if a.diag:
        input("\nDIAG: las ruedas van a girar. Levanta el robot y presiona Enter...")
        r.eco = True
        r.enviar("DIAG")
        time.sleep(3)
print("\nComunicacion OK.")
