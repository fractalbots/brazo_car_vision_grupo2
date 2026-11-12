#!/usr/bin/env python3
"""Pruebas de la plataforma movil (Semana 2 y niveles de velocidad de la Semana 6).

  python 06_pruebas_plataforma.py recto  --rep 5 --dist 1.0 --vel 0.3
  python 06_pruebas_plataforma.py giro   --rep 5 --ang 90
  python 06_pruebas_plataforma.py velocidad        (mide con encoder los 3 niveles de config.py)

En recto y giro, despues de cada repeticion escribes lo que mediste con el flexometro / transportador.
Todo queda en datos/prueba_<tipo>.csv con el error de cada repeticion y el resumen."""
import argparse
import csv
import os
import statistics as st
import time

import config
from esp32_link import ESP32

ap = argparse.ArgumentParser()
ap.add_argument("prueba", choices=["recto", "giro", "velocidad"])
ap.add_argument("--rep", type=int, default=5)
ap.add_argument("--dist", type=float, default=1.0, help="m (recto)")
ap.add_argument("--vel", type=float, default=0.30, help="m/s (recto)")
ap.add_argument("--ang", type=float, default=90.0, help="grados, + izquierda (giro)")
a = ap.parse_args()
os.makedirs(config.CARPETA_DATOS, exist_ok=True)
archivo = os.path.join(config.CARPETA_DATOS, f"prueba_{a.prueba}.csv")


def numero(msg):
    while True:
        s = input(msg).strip().replace(",", ".")
        try:
            return float(s)
        except ValueError:
            print("  escribe un numero (ej. 98.5)")


with ESP32() as r:
    filas = []
    if a.prueba == "recto":
        cab = ["rep", "dist_pedida_m", "vel_m_s", "dist_encoder_m", "rumbo_encoder_deg", "dist_real_m",
               "desvio_lateral_m", "error_dist_m", "error_dist_pct"]
        for i in range(1, a.rep + 1):
            input(f"\n[{i}/{a.rep}] Pon el robot en la marca de SALIDA, alineado, y presiona Enter...")
            r.reset_odometria()
            res = r.recto(a.dist, a.vel)
            time.sleep(0.6)
            if res is None:
                print("  No termino (obstaculo o sin respuesta). Se repite.")
                continue
            d_enc = r.tel["dist"]
            real = numero("  Distancia REAL recorrida (cm): ") / 100
            lat = numero("  Desvio lateral al final (cm, + izquierda): ") / 100
            err = real - a.dist
            filas.append([i, a.dist, a.vel, round(d_enc, 4), round(res[1], 2), real, lat, round(err, 4),
                          round(100 * err / a.dist, 2)])
            print(f"  encoder {d_enc * 100:.1f} cm | real {real * 100:.1f} cm | error {err * 100:+.1f} cm")
        if filas:
            e = [f[7] for f in filas]; l = [f[6] for f in filas]
            print(f"\nRESUMEN recto {a.dist} m a {a.vel} m/s ({len(filas)} rep.): error medio {st.mean(e) * 100:+.2f} cm "
                  f"(desv {st.pstdev(e) * 100:.2f}), |error| medio {st.mean(map(abs, e)) * 100:.2f} cm, "
                  f"desvio lateral medio {st.mean(l) * 100:+.2f} cm")

    elif a.prueba == "giro":
        cab = ["rep", "ang_pedido_deg", "ang_encoder_deg", "ang_real_deg", "error_deg", "error_pct"]
        for i in range(1, a.rep + 1):
            input(f"\n[{i}/{a.rep}] Alinea el robot con la marca de 0 grados y presiona Enter...")
            r.reset_odometria()
            ang = r.giro(a.ang)
            time.sleep(0.6)
            if ang is None:
                print("  No termino. Se repite.")
                continue
            ang = r.tel["th_deg"]
            real = numero("  Angulo REAL girado (grados): ")
            err = real - a.ang
            filas.append([i, a.ang, round(ang, 2), real, round(err, 2), round(100 * err / a.ang, 2)])
            print(f"  encoder {ang:.1f} | real {real:.1f} | error {err:+.1f} grados")
        if filas:
            e = [f[4] for f in filas]
            print(f"\nRESUMEN giro {a.ang} grados ({len(filas)} rep.): error medio {st.mean(e):+.2f} "
                  f"(desv {st.pstdev(e):.2f}), |error| medio {st.mean(map(abs, e)):.2f} grados")

    else:  # velocidad
        cab = ["nivel", "v_pedida_m_s", "v_izq_media", "v_der_media", "v_media", "desv_izq", "desv_der", "error_pct"]
        input("Las ruedas van a girar 4 s por nivel. LEVANTA el robot (ruedas al aire) o ponlo en el piso con 7 m libres, y presiona Enter...")
        r.anticolision(False)
        for nivel, v in config.VELOCIDADES.items():
            fin = time.time() + 1.5          # 1.5 s para llegar a la velocidad
            while time.time() < fin:
                r.vel(v); time.sleep(0.05)
            vi, vd, si, sd = [], [], [], []
            fin = time.time() + 2.5
            while time.time() < fin:
                r.vel(v); vi.append(r.tel["v_izq"]); vd.append(r.tel["v_der"]); time.sleep(0.05)
            r.frena(); time.sleep(1.0)
            mi, md = st.mean(vi), st.mean(vd)
            vm = (mi + md) / 2
            filas.append([nivel, v, round(mi, 4), round(md, 4), round(vm, 4), round(st.pstdev(vi), 4),
                          round(st.pstdev(vd), 4), round(100 * (vm - v) / v, 2)])
            print(f"  {nivel:6s} pedida {v:.2f} | izq {mi:.3f} der {md:.3f} | media {vm:.3f} m/s "
                  f"(desv {st.pstdev(vi):.3f}/{st.pstdev(vd):.3f})")
        r.anticolision(True)

    if filas:
        nuevo = not os.path.exists(archivo)
        with open(archivo, "a", newline="") as f:
            w = csv.writer(f)
            if nuevo:
                w.writerow(["fecha"] + cab)
            for fila in filas:
                w.writerow([time.strftime("%Y-%m-%d %H:%M:%S")] + fila)
        print(f"\nGuardado en {archivo}")
