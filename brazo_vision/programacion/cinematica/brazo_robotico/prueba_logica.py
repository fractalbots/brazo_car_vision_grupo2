# -*- coding: utf-8 -*-
"""Verifica la matematica sin tocar hardware (simulado=True)."""
from brazo import Brazo, FueraDeRango

b = Brazo(simulado=True)
a = b.art["hombro"]
print("--- conversion angulo -> pulso (hombro: %.0f a %.0f grados) ---"
      % (a.ang_min, a.ang_max))
for ang in (a.ang_min, 0.0, a.ang_max):
    print("   %7.1f grados -> %7.1f us   (gemelo: %7.1f us)"
          % (ang, a.pulso(ang), a.pulso(a.espejo(ang))))

print("\n--- el gemelo siempre debe ir al contrario ---")
ok = all(abs((a.pulso(x) - a.pulso_min) + (a.pulso(a.espejo(x)) - a.pulso_min)
             - (a.pulso_max - a.pulso_min)) < 1e-6
         for x in (-10, 0, 40, 95))
print("   simetria correcta:", ok)

print("\n--- limites ---")
try:
    b._escribir("hombro", 200.0)
    print("   FALLO: acepto 200 grados")
except FueraDeRango as e:
    print("   rechaza fuera de rango:", e)
b.mover({"hombro": 500}, duracion=0.1)
print("   mover() recorta a:", round(b.pos["hombro"], 1), "grados")

print("\n--- movimiento coordinado: todas llegan juntas ---")
b.home(0.1)
b.registro.clear()
b.mover({"base": 60, "codo": -90, "muneca": 45}, duracion=1.0)
ini, fin = b.registro[0][1], b.registro[-1][1]
print("   pasos:", len(b.registro))
for n in ("base", "codo", "muneca"):
    print("   %-8s %7.2f -> %7.2f" % (n, ini[n], fin[n]))

print("\n--- suavizado: velocidad al inicio y al final ---")
vs = [abs(b.registro[i][1]["base"] - b.registro[i-1][1]["base"])
      for i in range(1, len(b.registro))]
print("   primer paso %.3f  |  paso central %.3f  |  ultimo paso %.3f"
      % (vs[0], vs[len(vs)//2], vs[-1]))
print("   arranca y frena suave:", vs[0] < vs[len(vs)//2] and vs[-1] < vs[len(vs)//2])

print("\n--- duracion automatica segun vel_max ---")
b.home(0.1)
d = b.mover({"hombro": 90})
print("   hombro 0->90 grados a %.0f grados/s  ->  %.2f s" % (b.art["hombro"].vel_max, d))
