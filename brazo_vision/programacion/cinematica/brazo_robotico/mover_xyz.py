# -*- coding: utf-8 -*-
"""
Une cinematica + servos: le pides una coordenada y el brazo va.

    python3 mover_xyz.py            # secuencia de demostracion
    python3 mover_xyz.py 120 60 200 # va a ese punto
"""
import sys
import time

from brazo import Brazo
from cinematica import Cinematica, FueraDeAlcance


class BrazoXYZ:
    """Brazo que entiende coordenadas de la mesa en milimetros."""

    def __init__(self, **kw):
        self.b = Brazo(**kw)
        self.k = Cinematica()

    def ir_a(self, x, y, z, cabeceo=180.0, duracion=None):
        base, hombro, codo, muneca = self.k.inversa(x, y, z, cabeceo)
        return self.b.mover({"base": base, "hombro": hombro,
                             "codo": codo, "muneca": muneca},
                            duracion=duracion, limitar=False)

    def recoger(self, x, z, alto_mesa=25.0, alto_libre=140.0):
        """Baja, cierra la pinza y vuelve a subir."""
        self.ir_a(x, alto_libre, z)          # encima de la pieza
        self.b.abrir_pinza()
        self.ir_a(x, alto_mesa, z, duracion=1.2)   # baja despacio
        self.b.cerrar_pinza()
        time.sleep(0.3)
        self.ir_a(x, alto_libre, z, duracion=1.2)  # levanta

    def soltar(self, x, z, alto_mesa=35.0, alto_libre=140.0):
        self.ir_a(x, alto_libre, z)
        self.ir_a(x, alto_mesa, z, duracion=1.2)
        self.b.abrir_pinza()
        time.sleep(0.3)
        self.ir_a(x, alto_libre, z, duracion=1.2)

    def __enter__(self):
        return self

    def __exit__(self, *e):
        self.b.__exit__(*e)
        return False


if __name__ == "__main__":
    if len(sys.argv) == 4:
        x, y, z = (float(v) for v in sys.argv[1:4])
        with BrazoXYZ() as r:
            r.b.home()
            try:
                r.ir_a(x, y, z)
                print("en (%.0f, %.0f, %.0f)" % (x, y, z))
                print("angulos:", {k: round(v, 1) for k, v in r.b.posicion().items()})
            except FueraDeAlcance as e:
                print("No llega:", e)
            time.sleep(1.5)
            r.b.home()
    else:
        with BrazoXYZ() as r:
            print("HOME"); r.b.home()
            print("recoger en (120, 210)"); r.recoger(x=120, z=210)
            print("soltar en (-150, 170)"); r.soltar(x=-150, z=170)
            print("HOME"); r.b.home()
