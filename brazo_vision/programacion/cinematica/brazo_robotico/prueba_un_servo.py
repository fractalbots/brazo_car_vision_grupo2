# -*- coding: utf-8 -*-
"""
PRIMER CONTACTO. Correr esto ANTES de conectar los 9 servos.

Mueve un solo servo entre tres pulsos seguros, despacio.
Hazlo con el servo SUELTO, fuera del brazo y SIN el disco puesto.

    python3 prueba_un_servo.py 0
"""
import sys
import time
from pca9685 import PCA9685

canal = int(sys.argv[1]) if len(sys.argv) > 1 else 0

print("Canal %d. Ctrl+C para cortar." % canal)
print("Si el servo zumba fuerte o se calienta, CORTA la fuente ya.\n")

pwm = PCA9685()
try:
    for us in (1500, 1000, 1500, 2000, 1500):
        print("  pulso %4d us" % us)
        pwm.pulso_us(canal, us)
        time.sleep(1.2)
    print("\nOK. El servo responde.")
except KeyboardInterrupt:
    print("\ncortado")
finally:
    pwm.apagar_todos()
    pwm.cerrar()
    print("servos liberados")
