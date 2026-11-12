# -*- coding: utf-8 -*-
"""Verifica la cinematica sin hardware: ida y vuelta + mapa de alcance."""
import math
from cinematica import Cinematica, FueraDeAlcance

k = Cinematica()
print("L1=%.1f  L2=%.1f  L3=%.1f  altura del hombro=%.1f mm"
      % (k.L1, k.L2, k.L3, k.H))

print("\n--- 1. Posicion HOME (todo en 0) debe dar 502 mm ---")
x, y, z, cab = k.directa(0, 0, 0, 0)
print("   punta en x=%.1f  y=%.1f  z=%.1f   -> altura %.1f mm" % (x, y, z, y))
print("   correcto:", abs(y - 502.0) < 0.1)

print("\n--- 2. Ida y vuelta: inversa -> directa debe devolver el mismo punto ---")
casos = [(0,60,250),(120,60,200),(-120,60,200),(0,150,300),(80,40,280),
         (-150,80,150),(200,60,150),(0,60,330)]
peor = 0.0
for (tx, ty, tz) in casos:
    try:
        b, h, c, m = k.inversa(tx, ty, tz, 180)
    except FueraDeAlcance as e:
        print("   (%4d,%4d,%4d)  fuera de alcance: %s" % (tx,ty,tz,e)); continue
    rx, ry, rz, rc = k.directa(b, h, c, m)
    err = math.dist((tx,ty,tz),(rx,ry,rz)); peor = max(peor, err)
    print("   (%4d,%4d,%4d) -> base %6.1f  hombro %6.1f  codo %7.1f  muneca %7.1f"
          "   | error %.4f mm" % (tx,ty,tz,b,h,c,m,err))
print("   peor error: %.6f mm" % peor)
print("   la inversa es exacta:", peor < 1e-6)

print("\n--- 3. Alcance horizontal con la pinza apuntando abajo ---")
for alt in (40, 60, 100, 150, 200):
    print("   a %3d mm de altura  ->  llega hasta %.0f mm del centro"
          % (alt, k.alcance_maximo(alt)))

print("\n--- 4. Mapa de la zona de trabajo (corte vertical, pinza hacia abajo) ---")
print("    # = alcanzable      . = no      (cada celda 20 mm)")
alturas = list(range(300, -1, -20))
print("         " + "".join("%-2d"%(d//20%10) for d in range(0, 420, 20)))
for alt in alturas:
    fila = "".join("#" if k.alcanzable(0, alt, u + k.dz, 180) else "."
                   for u in range(0, 420, 20))
    print("   %3d mm %s" % (alt, fila))
print("         0        100       200       300       400  mm del centro")

print("\n--- 5. Limites de los servos ---")
import json
cfg = json.load(open("config_servos.json", encoding="utf-8"))
lim = {a["nombre"]:(a["ang_min"],a["ang_max"]) for a in cfg["articulaciones"]}
malos = 0
for (tx,ty,tz) in casos:
    try: b,h,c,m = k.inversa(tx,ty,tz,180)
    except FueraDeAlcance: continue
    for nom,val in (("base",b),("hombro",h),("codo",c),("muneca",m)):
        lo,hi = lim[nom]
        if not (lo <= val <= hi):
            print("   (%4d,%4d,%4d): %s=%.1f fuera de [%.0f,%.0f]"%(tx,ty,tz,nom,val,lo,hi))
            malos += 1
print("   puntos con algun angulo fuera de los limites actuales:", malos)
