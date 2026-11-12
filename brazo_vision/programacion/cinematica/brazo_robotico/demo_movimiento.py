# -*- coding: utf-8 -*-
"""
Demostracion: secuencia tipica de recoger y soltar.
Sirve para el video de funcionamiento que pide el documento.

    python3 demo_movimiento.py
"""
import time
from brazo import Brazo

with Brazo() as b:
    print("HOME")
    b.home()
    time.sleep(0.5)

    print("girar hacia la pieza")
    b.mover({"base": 35}, duracion=1.5)

    print("bajar y abrir")
    b.mover({"hombro": 55, "codo": -75, "muneca": 20}, duracion=2.0)
    b.abrir_pinza()
    time.sleep(0.3)

    print("cerrar sobre la pieza")
    b.cerrar_pinza()
    time.sleep(0.5)

    print("levantar")
    b.mover({"hombro": 20, "codo": -40}, duracion=1.5)

    print("girar al deposito")
    b.mover({"base": -45}, duracion=2.0)

    print("bajar y soltar")
    b.mover({"hombro": 50, "codo": -70}, duracion=1.5)
    b.abrir_pinza()
    time.sleep(0.4)

    print("volver a HOME")
    b.home()
    print("\nlisto")
