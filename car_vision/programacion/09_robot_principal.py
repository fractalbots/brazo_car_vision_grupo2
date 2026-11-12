#!/usr/bin/env python3
"""PROGRAMA PRINCIPAL: el robot avanza, detecta baches y reductores, estima la distancia y reacciona.
  bache    -> FRENA cuando esta a D_FRENA o menos
  reductor -> baja a V_LENTO cuando esta a D_LENTO o menos, lo pasa y vuelve a su velocidad
  (las distancias y velocidades se cambian en config.py)

Ensayos de la Semana 6 (un comando por ensayo):
  python 09_robot_principal.py --vel media --luz alta --anomalia bache
  python 09_robot_principal.py --vel alta  --luz baja --anomalia normal
Demostracion (sin registrar como ensayo):
  python 09_robot_principal.py --vel baja
Otras opciones:
  --sin-ventana     sin mostrar video (mas FPS; Ctrl+C para parar)
  --grabar          guarda el video anotado del ensayo
  --accion registrar  solo registra las detecciones, no frena ni baja la velocidad
  --sin-motores     el robot no se mueve (para probar la vision empujandolo a mano)
  --video archivo.mp4 --sin-esp32   probar con un video grabado, sin robot

Archivos: datos/ensayos.csv (una fila por ensayo, con TP/FP/FN/TN, latencia, FPS, distancias)
          datos/ensayos/ensayo_NNN.csv (una fila por cuadro)"""
import argparse
import csv
import os
import statistics as st
import time

import cv2

import config
from vision import Camara, Detector, Distancia, dibujar, principal, texto, tof_horizontal_m

ap = argparse.ArgumentParser()
ap.add_argument("--vel", default="baja", help="baja | media | alta | numero en m/s")
ap.add_argument("--luz", default="", choices=["", "alta", "media", "baja"], help="nivel de iluminacion del ensayo")
ap.add_argument("--anomalia", choices=["bache", "reductor", "normal"], help="lo que hay en la pista (verdad)")
ap.add_argument("--ensayo", type=int, help="numero de ensayo (si no, el siguiente)")
ap.add_argument("--dist", type=float, default=config.DISTANCIA_ENSAYO, help="m maximos a recorrer")
ap.add_argument("--accion", choices=["reaccionar", "registrar"], default="reaccionar")
ap.add_argument("--sin-ventana", action="store_true")
ap.add_argument("--grabar", action="store_true")
ap.add_argument("--sin-motores", action="store_true")
ap.add_argument("--sin-esp32", action="store_true")
ap.add_argument("--video", help="usar un video en vez de la camara")
ap.add_argument("--modelo", help="carpeta del modelo NCNN (por defecto el de config.py)")
a = ap.parse_args()

v_set = config.VELOCIDADES.get(a.vel) if a.vel in config.VELOCIDADES else float(a.vel)
nivel_vel = a.vel if a.vel in config.VELOCIDADES else "manual"
es_ensayo = a.anomalia is not None
os.makedirs(os.path.join(config.CARPETA_DATOS, "ensayos"), exist_ok=True)
resumen_csv = os.path.join(config.CARPETA_DATOS, "ensayos.csv")
if a.ensayo is None:
    a.ensayo = 1
    if os.path.exists(resumen_csv):
        with open(resumen_csv) as f:
            a.ensayo = sum(1 for _ in f)          # cabecera + n filas -> n + 1
nombre = f"ensayo_{a.ensayo:03d}" if es_ensayo else time.strftime("demo_%Y%m%d_%H%M%S")
base = os.path.join(config.CARPETA_DATOS, "ensayos", nombre)

# ------------------------------------------------------------------ arranque
cam = Camara(a.video)
det = Detector(a.modelo)
dist = Distancia()
robot = None
if not a.sin_esp32:
    from esp32_link import ESP32
    robot = ESP32()
print(f"Modelo: {det.ruta} | clases: {list(det.nombres.values())}")
if not dist.calibrada:
    print("[AVISO] Distancia SIN calibrar (corre 07_calibrar_distancia.py)")


def tel(k, defecto=None):
    return robot.tel.get(k, defecto) if robot else defecto


lux_ini = None
if robot:
    lx = []
    for _ in range(20):
        if tel("lux", -1) >= 0:
            lx.append(tel("lux"))
        time.sleep(0.05)
    lux_ini = round(st.median(lx), 1) if lx else None
    bat = tel("bat_v", 0)
    print(f"Luz medida: {lux_ini} lx | bateria {bat:.2f} V")
    rango = config.NIVELES_LUZ.get(a.luz)
    if rango and lux_ini is not None and not (rango[0] <= lux_ini <= rango[1]):
        print(f"[AVISO] La luz ({lux_ini} lx) NO esta en el nivel '{a.luz}' {rango}: este ensayo se va a descartar.")
    if 5 < bat < 10.0:
        print("[AVISO] Bateria baja: carga antes de seguir con los ensayos")
    robot.anticolision(a.anomalia != "reductor")   # el reductor puede dar eco al ultrasonico
    if not a.sin_motores:
        for i in (3, 2, 1):
            print(f"  arranca en {i}...")
            time.sleep(1)
    robot.reset_odometria()

grab = None
if a.grabar:
    grab = cv2.VideoWriter(base + ".mp4", cv2.VideoWriter_fourcc(*"mp4v"), 15, (config.ANCHO, config.ALTO))

cuadros_f = open(base + ".csv", "w", newline="")
cw = csv.writer(cuadros_f)
cw.writerow(["t_s", "cuadro", "inferencia_ms", "fps", "estado", "clase", "conf", "x1", "y1", "x2", "y2", "d_est_m",
             "d_tof_m", "lux", "v_izq", "v_der", "v_pedida", "x_odo_m", "us_cm"])

# ------------------------------------------------------------------ bucle
estado = "CRUCERO"            # CRUCERO -> LENTO -> CRUCERO ...  o  CRUCERO -> FRENADO
seguidos = {"bache": 0, "reductor": 0}
primera = {}                  # anomalia -> (t, d_est, x_odo) primer cuadro que la vio
confirmada = {}               # anomalia -> (t, d_est, x_odo) al confirmarla
accion = None                 # dict con lo que hizo el robot
x_fin_lento, t_frenado = 0.0, None
inf_ms, periodos, v_crucero = [], [], []
conf_max = 0.0
motivo_fin, n, t0, t_prev = "", -1, time.time(), None

try:
    while True:
        n, img, t_img = cam.leer(n)
        if img is None:
            if not cam.activa:
                motivo_fin = "fin del video"
                break
            continue
        ahora = time.time()
        if t_prev:
            periodos.append(ahora - t_prev)
        t_prev = ahora
        dets, ms = det.detectar(img)
        inf_ms.append(ms)
        p = principal(dets)
        d_est = dist.metros(p["y2"]) if p else None
        x = tel("dist", 0.0)

        # --- confirmar (CUADROS_CONFIRMA seguidos de la misma anomalia)
        for c in seguidos:
            seguidos[c] = seguidos[c] + 1 if p and p["anomalia"] == c else 0
        if p:
            conf_max = max(conf_max, p["conf"])
            primera.setdefault(p["anomalia"], (ahora, d_est, x))
            if seguidos[p["anomalia"]] >= config.CUADROS_CONFIRMA:
                confirmada.setdefault(p["anomalia"], (ahora, d_est, x))

        # --- decidir
        if (estado == "CRUCERO" and a.accion == "reaccionar" and p and p["anomalia"] in confirmada
                and d_est is not None):
            tipo = config.ACCION.get(p["anomalia"])
            if tipo == "FRENA" and d_est <= config.D_FRENA:
                estado, t_frenado = "FRENADO", ahora
                if robot and not a.sin_motores:
                    robot.frena()
            elif tipo == "LENTO" and d_est <= config.D_LENTO:
                estado, x_fin_lento = "LENTO", x + d_est + config.PASADO_REDUCTOR
            if estado != "CRUCERO" and accion is None:
                t_cmd = time.time()
                accion = dict(tipo=tipo, clase=p["anomalia"], d_est=d_est, conf=p["conf"],
                              d_tof=tof_horizontal_m(tel("tof_mm")), x=x,
                              latencia_ms=(t_cmd - t_img) * 1000,
                              desde_primera_s=t_cmd - primera[p["anomalia"]][0])
                print(f"  >> {tipo}: {p['anomalia']} a {d_est * 100:.0f} cm (conf {p['conf']:.2f}, "
                      f"latencia {accion['latencia_ms']:.0f} ms)")
        if estado == "LENTO" and x >= x_fin_lento:
            estado = "CRUCERO"

        v_cmd = {"CRUCERO": v_set, "LENTO": min(v_set, config.V_LENTO), "FRENADO": 0.0}[estado]
        if robot and not a.sin_motores:
            if estado == "FRENADO":
                robot.frena()
            else:
                robot.vel(v_cmd)
        if estado == "CRUCERO" and x > 0.4 and tel("v_izq") is not None:
            v_crucero.append((tel("v_izq") + tel("v_der")) / 2)

        # --- registrar cuadro
        fps = 1 / st.mean(periodos[-15:]) if periodos else 0
        cw.writerow([round(ahora - t0, 3), n, round(ms, 1), round(fps, 1), estado,
                     p["anomalia"] if p else "normal", round(p["conf"], 3) if p else "",
                     *([round(p[k]) for k in ("x1", "y1", "x2", "y2")] if p else ["", "", "", ""]),
                     round(d_est, 4) if d_est else "", round(tof_horizontal_m(tel("tof_mm")) or 0, 4) or "",
                     tel("lux", ""), tel("v_izq", ""), tel("v_der", ""), v_cmd, round(x, 4), tel("us_cm", "")])

        # --- pantalla
        if not a.sin_ventana or grab:
            dibujar(img, dets, dist, p)
            texto(img, [f"{estado}  v {v_cmd:.2f} m/s  medida {((tel('v_izq', 0) + tel('v_der', 0)) / 2):.2f}",
                        f"inferencia {ms:.0f} ms  {fps:.1f} FPS",
                        f"recorrido {x:.2f} m  luz {tel('lux', 0):.0f} lx",
                        f"{p['anomalia']} {d_est * 100:.0f} cm" if p and d_est else "superficie normal"],
                  color=(0, 0, 255) if estado == "FRENADO" else (0, 255, 0))
            if grab:
                grab.write(img)
            if not a.sin_ventana:
                cv2.imshow("Robot de inspeccion vial", img)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    motivo_fin = "abortado (q)"
                    break

        # --- terminar
        if estado == "FRENADO" and ahora - t_frenado > 1.5:
            motivo_fin = "frenado ante bache"
            break
        if robot and not a.sin_motores and x >= a.dist:
            motivo_fin = f"recorrio {a.dist} m"
            break
        if robot and tel("motivo") in ("OBST", "WDOG"):
            motivo_fin = "paro de seguridad " + tel("motivo")
            break
except KeyboardInterrupt:
    motivo_fin = "abortado (Ctrl+C)"
finally:
    if robot:
        robot.frena()
    time.sleep(0.3)
    x_final = tel("dist", 0.0)
    cuadros_f.close()
    if grab:
        grab.release()
    cam.cerrar()
    if not a.sin_ventana:
        cv2.destroyAllWindows()

# ------------------------------------------------------------------ resultado del ensayo
print(f"\nFin: {motivo_fin} | {n} cuadros | inferencia media {st.mean(inf_ms):.1f} ms | "
      f"{1 / st.mean(periodos):.1f} FPS" if periodos else f"\nFin: {motivo_fin}")
if confirmada:
    for c, (t, d, _) in confirmada.items():
        print(f"  detectado {c} (confirmado a {d * 100:.0f} cm)" if d else f"  detectado {c}")
else:
    print("  sin detecciones confirmadas (superficie normal)")

if es_ensayo and robot:
    det_set = set(confirmada)
    real = a.anomalia
    tp = int(real in det_set) if real != "normal" else 0
    fn = int(real not in det_set) if real != "normal" else 0
    fp = len(det_set - {real})
    tn = int(real == "normal" and not det_set)
    d_real = ""
    if accion and accion["tipo"] == "FRENA" and not a.sin_ventana:
        s = input("Distancia REAL de la camara al borde del bache (cm, Enter = no medi): ").strip().replace(",", ".")
        d_real = float(s) / 100 if s else ""
    descarte = ""
    if motivo_fin.startswith(("abortado", "paro")):
        descarte = motivo_fin
    rango = config.NIVELES_LUZ.get(a.luz)
    if rango and lux_ini is not None and not (rango[0] <= lux_ini <= rango[1]):
        descarte = f"luz {lux_ini} lx fuera del nivel {a.luz} ({rango[0]}-{rango[1]} lx)"
    pr = primera.get(real, (None, None, None))
    cf = confirmada.get(real, (None, None, None))
    fila = dict(
        fecha=time.strftime("%Y-%m-%d %H:%M:%S"), ensayo=a.ensayo, nivel_vel=nivel_vel, v_pedida=v_set,
        v_medida=round(st.mean(v_crucero), 3) if v_crucero else "", nivel_luz=a.luz, lux=lux_ini,
        anomalia_real=real, detectadas="+".join(sorted(det_set)) or "ninguna", TP=tp, FP=fp, FN=fn, TN=tn,
        conf_max=round(conf_max, 3), d_primera_m=round(pr[1], 4) if pr[1] else "",
        d_confirmacion_m=round(cf[1], 4) if cf[1] else "",
        accion=accion["tipo"] if accion else "", d_est_accion_m=round(accion["d_est"], 4) if accion else "",
        d_tof_accion_m=round(accion["d_tof"], 4) if accion and accion["d_tof"] else "", d_real_accion_m=d_real,
        latencia_ms=round(accion["latencia_ms"], 1) if accion else "",
        t_det_accion_s=round(accion["desde_primera_s"], 3) if accion else "",
        inferencia_ms=round(st.mean(inf_ms), 1) if inf_ms else "",
        inferencia_p95_ms=round(sorted(inf_ms)[int(0.95 * (len(inf_ms) - 1))], 1) if inf_ms else "",
        fps=round(1 / st.mean(periodos), 2) if periodos else "", cuadros=n, recorrido_m=round(x_final, 3),
        valido=0 if descarte else 1, motivo_descarte=descarte, archivo=os.path.basename(base) + ".csv")
    nuevo = not os.path.exists(resumen_csv)
    with open(resumen_csv, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(fila))
        if nuevo:
            w.writeheader()
        w.writerow(fila)
    print(f"Ensayo {a.ensayo}: TP {tp} FP {fp} FN {fn} TN {tn} {'(DESCARTADO: ' + descarte + ')' if descarte else ''}")
    print(f"Guardado en {resumen_csv}")
if robot:
    robot.cerrar()
