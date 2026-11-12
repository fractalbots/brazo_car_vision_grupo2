# -*- coding: utf-8 -*-
"""
Calibracion de cada servo. Esto es lo que hace que el brazo quede preciso.

Cada TD-8120MG es distinto: el pulso que da 0 grados en uno no da 0 en otro.
Aqui buscas a mano los dos extremos mecanicos reales de cada articulacion
y los guardas en config_servos.json.

    python3 calibrar.py

HAZLO CON EL BRAZO DESARMADO o con la articulacion libre. Si calibras con
todo armado y te pasas del tope mecanico, el servo empuja contra el plastico
y se quema.

Comandos dentro del programa:
    a / d        mueve -5 / +5 us
    A / D        mueve -25 / +25 us
    z / c        mueve -1 / +1 us (fino)
    min          guarda el pulso actual como el extremo ang_min
    max          guarda el pulso actual como el extremo ang_max
    centro       salta a 1500 us
    ver          muestra lo guardado
    ok           pasa a la siguiente articulacion
    salir        guarda el archivo y termina
"""
import json
import os

from pca9685 import PCA9685

AQUI = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(AQUI, "config_servos.json")

with open(RUTA, encoding="utf-8") as f:
    cfg = json.load(f)

pwm = PCA9685(bus=cfg.get("i2c_bus", 1),
              direccion=cfg.get("direccion", 0x40),
              frecuencia=cfg.get("frecuencia", 50))

PASOS = {"a": -5, "d": 5, "A": -25, "D": 25, "z": -1, "c": 1}


def mover(canal, us, espejo=None, ang_min=None, ang_max=None):
    us = max(400, min(2600, us))
    pwm.pulso_us(canal, us)
    return us


try:
    for art in cfg["articulaciones"]:
        nombre = art["nombre"]
        canal = art["canal"]
        print("\n" + "=" * 68)
        print("  %s   (canal %d)" % (nombre.upper(), canal))
        if art.get("descripcion"):
            print("  " + art["descripcion"])
        if art.get("canal_espejo") is not None:
            print("  OJO: par de servos. Aqui calibras SOLO el canal %d."
                  % canal)
            print("  El canal %d (gemelo) se calibra igual, por separado."
                  % art["canal_espejo"])
        print("  Rango de angulos: %.1f a %.1f grados"
              % (art["ang_min"], art["ang_max"]))
        print("=" * 68)

        us = 1500
        mover(canal, us)
        print("  arranco en 1500 us (centro mecanico aproximado)")

        while True:
            cmd = input("  [%s] %4d us > " % (nombre, us)).strip()
            if cmd in PASOS:
                us = mover(canal, us + PASOS[cmd])
            elif cmd == "centro":
                us = mover(canal, 1500)
            elif cmd == "min":
                art["pulso_min"] = int(us)
                print("    ang_min (%.1f grados) = %d us" % (art["ang_min"], us))
            elif cmd == "max":
                art["pulso_max"] = int(us)
                print("    ang_max (%.1f grados) = %d us" % (art["ang_max"], us))
            elif cmd == "ver":
                print("    pulso_min=%s  pulso_max=%s"
                      % (art["pulso_min"], art["pulso_max"]))
            elif cmd == "ok":
                break
            elif cmd == "salir":
                raise KeyboardInterrupt
            elif cmd == "":
                continue
            else:
                print("    no entiendo. a d A D z c / min max centro ver ok salir")

        if art["pulso_min"] > art["pulso_max"]:
            print("  NOTA: pulso_min > pulso_max. Esta bien: significa que ese")
            print("  servo gira al reves. El codigo lo maneja solo.")
        pwm.apagar(canal)

except KeyboardInterrupt:
    print("\ninterrumpido")
finally:
    pwm.apagar_todos()
    pwm.cerrar()
    with open(RUTA, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("\nGuardado en %s" % RUTA)
