#!/usr/bin/env python3
"""Calcula las metricas del informe a partir de los ensayos (Semana 6 y final).

  python 10_resumen_metricas.py

Lee datos/ensayos.csv (solo ensayos validos) y datos/validacion_distancia.csv.
Escribe datos/resumen_metricas.csv y graficas en datos/graficas/:
  - Precision, Recall, F1 por velocidad x iluminacion, por velocidad y por iluminacion
  - latencia de inferencia, FPS, tiempo de respuesta, velocidad medida, lux medidos
  - MAE y RMSE de la distancia (camara vs VL53L1X y camara vs cinta)
El mAP sale de 11_evaluar_modelo.py (necesita las imagenes etiquetadas)."""
import csv
import math
import os
import statistics as st

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config

D = config.CARPETA_DATOS
ORDEN_VEL = list(config.VELOCIDADES) + ["manual"]
ORDEN_LUZ = ["alta", "media", "baja", ""]


def leer(nombre):
    p = os.path.join(D, nombre)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return list(csv.DictReader(f))


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def media(vals):
    v = [x for x in map(num, vals) if x is not None]
    return round(st.mean(v), 3) if v else ""


def metricas(filas):
    tp = sum(int(f["TP"]) for f in filas); fp = sum(int(f["FP"]) for f in filas)
    fn = sum(int(f["FN"]) for f in filas); tn = sum(int(f["TN"]) for f in filas)
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * pr * rc / (pr + rc) if pr + rc else 0.0
    err = [num(f["d_est_accion_m"]) - num(f["d_tof_accion_m"]) for f in filas
           if num(f["d_est_accion_m"]) is not None and num(f["d_tof_accion_m"]) is not None]
    return dict(n=len(filas), TP=tp, FP=fp, FN=fn, TN=tn, precision=round(pr, 3), recall=round(rc, 3), F1=round(f1, 3),
                exactitud=round((tp + tn) / max(1, tp + tn + fp + fn), 3),
                inferencia_ms=media(f["inferencia_ms"] for f in filas), fps=media(f["fps"] for f in filas),
                respuesta_ms=media(f["latencia_ms"] for f in filas),
                v_medida=media(f["v_medida"] for f in filas), lux=media(f["lux"] for f in filas),
                d_primera_m=media(f["d_primera_m"] for f in filas),
                MAE_tof_m=round(st.mean(abs(e) for e in err), 4) if err else "",
                RMSE_tof_m=round(math.sqrt(st.mean(e * e for e in err)), 4) if err else "")


ens = [f for f in leer("ensayos.csv") if f.get("valido") == "1"]
todos = leer("ensayos.csv")
print(f"Ensayos: {len(todos)} registrados, {len(ens)} validos, {len(todos) - len(ens)} descartados\n")
salida = []
if ens:
    grupos = [("TOTAL", "", "", ens)]
    for v in ORDEN_VEL:
        for l in ORDEN_LUZ:
            g = [f for f in ens if f["nivel_vel"] == v and f["nivel_luz"] == l]
            if g:
                grupos.append(("vel x luz", v, l, g))
    for v in ORDEN_VEL:
        g = [f for f in ens if f["nivel_vel"] == v]
        if g:
            grupos.append(("por velocidad", v, "", g))
    for l in ORDEN_LUZ:
        g = [f for f in ens if f["nivel_luz"] == l]
        if g and l:
            grupos.append(("por luz", "", l, g))
    print(f"{'grupo':14s} {'vel':6s} {'luz':6s} {'n':>3s} {'Prec':>5s} {'Rec':>5s} {'F1':>5s} {'inf ms':>7s} "
          f"{'FPS':>5s} {'resp ms':>8s} {'v m/s':>6s} {'lux':>6s}")
    for tipo, v, l, g in grupos:
        m = metricas(g)
        salida.append(dict(grupo=tipo, velocidad=v, luz=l, **m))
        print(f"{tipo:14s} {v:6s} {l:6s} {m['n']:3d} {m['precision']:5.2f} {m['recall']:5.2f} {m['F1']:5.2f} "
              f"{str(m['inferencia_ms']):>7s} {str(m['fps']):>5s} {str(m['respuesta_ms']):>8s} "
              f"{str(m['v_medida']):>6s} {str(m['lux']):>6s}")
    faltan = [(v, l) for v in config.VELOCIDADES for l in ("alta", "media", "baja")
              if sum(1 for f in ens if f["nivel_vel"] == v and f["nivel_luz"] == l) < 10]
    if faltan:
        print("\n[!] Combinaciones con menos de 10 ensayos validos:", ", ".join(f"{v}/{l}" for v, l in faltan))

# ---- distancia: prueba estatica de 10+ posiciones
val = leer("validacion_distancia.csv")
if val:
    e_tof = [num(f["error_m"]) for f in val if num(f["error_m"]) is not None]
    e_cin = [num(f["d_camara_m"]) - num(f["d_cinta_m"]) for f in val if num(f["d_cinta_m"]) is not None]
    fila = dict(grupo="distancia estatica", velocidad="", luz="", n=len(val))
    print(f"\nDistancia (prueba estatica, {len(val)} posiciones):")
    if e_tof:
        fila.update(MAE_tof_m=round(st.mean(map(abs, e_tof)), 4), RMSE_tof_m=round(math.sqrt(st.mean(e * e for e in e_tof)), 4))
        print(f"  camara vs VL53L1X: MAE {fila['MAE_tof_m'] * 100:.2f} cm | RMSE {fila['RMSE_tof_m'] * 100:.2f} cm")
    if e_cin:
        fila.update(MAE_cinta_m=round(st.mean(map(abs, e_cin)), 4), RMSE_cinta_m=round(math.sqrt(st.mean(e * e for e in e_cin)), 4))
        print(f"  camara vs cinta:   MAE {fila['MAE_cinta_m'] * 100:.2f} cm | RMSE {fila['RMSE_cinta_m'] * 100:.2f} cm")
    salida.append(fila)

if salida:
    campos = []
    for s in salida:
        campos += [k for k in s if k not in campos]
    with open(os.path.join(D, "resumen_metricas.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader(); w.writerows(salida)
    print(f"\nGuardado en {os.path.join(D, 'resumen_metricas.csv')}")

# ---- graficas
if ens:
    os.makedirs(os.path.join(D, "graficas"), exist_ok=True)
    vels = [v for v in config.VELOCIDADES if any(f["nivel_vel"] == v for f in ens)]
    luces = [l for l in ("alta", "media", "baja") if any(f["nivel_luz"] == l for f in ens)]
    for metrica, titulo in (("recall", "Recall"), ("F1", "F1"), ("inferencia_ms", "Inferencia (ms)"),
                            ("respuesta_ms", "Tiempo de respuesta (ms)")):
        fig, ax = plt.subplots(figsize=(5.5, 3.6), dpi=150)
        for l in luces:
            ys = []
            for v in vels:
                g = [f for f in ens if f["nivel_vel"] == v and f["nivel_luz"] == l]
                ys.append(num(metricas(g)[metrica]) if g else None)
            xs = [config.VELOCIDADES[v] for v in vels]
            ax.plot(xs, [y if y is not None else float("nan") for y in ys], "o-", label=f"luz {l}")
        ax.set_xlabel("Velocidad (m/s)"); ax.set_ylabel(titulo); ax.grid(alpha=0.3); ax.legend()
        ax.set_title(f"{titulo} por velocidad e iluminacion")
        fig.tight_layout()
        fig.savefig(os.path.join(D, "graficas", f"{metrica}_vs_velocidad.png"))
        plt.close(fig)
    print(f"Graficas en {os.path.join(D, 'graficas')}")
