# -*- coding: utf-8 -*-
"""
Capa de articulaciones del brazo robotico.

Que resuelve este modulo:
  - Convierte grados a ancho de pulso usando la calibracion de cada servo.
  - Respeta los limites por articulacion (nunca manda un angulo fuera de rango).
  - Mueve varias articulaciones a la vez y hace que TODAS lleguen al mismo
    tiempo, con arranque y frenado suaves.
  - Maneja el par de servos del hombro: al segundo le manda el angulo espejado.
  - Libera los servos al salir, pase lo que pase.

Uso basico:

    from brazo import Brazo

    with Brazo() as b:
        b.home()
        b.mover({"base": 45, "hombro": 30}, duracion=1.5)
        b.abrir_pinza()
"""

import json
import os
import time
from dataclasses import dataclass
from typing import Optional, Dict

from pca9685 import PCA9685

AQUI = os.path.dirname(os.path.abspath(__file__))


@dataclass
class Articulacion:
    nombre: str
    canal: int
    pulso_min: int
    pulso_max: int
    ang_min: float
    ang_max: float
    home: float
    canal_espejo: Optional[int] = None
    vel_max: float = 90.0            # grados por segundo
    descripcion: str = ""

    def pulso(self, angulo: float) -> float:
        """Interpolacion lineal entre los dos extremos calibrados."""
        t = (angulo - self.ang_min) / (self.ang_max - self.ang_min)
        return self.pulso_min + t * (self.pulso_max - self.pulso_min)

    def espejo(self, angulo: float) -> float:
        """El servo gemelo mira al contrario: se refleja sobre el centro."""
        return (self.ang_min + self.ang_max) - angulo

    def limitar(self, angulo: float) -> float:
        return max(self.ang_min, min(self.ang_max, angulo))


class FueraDeRango(ValueError):
    pass


class Brazo:
    PASOS_POR_SEGUNDO = 50          # coincide con el refresco del PCA9685

    def __init__(self, config=None, simulado=False):
        ruta = config or os.path.join(AQUI, "config_servos.json")
        with open(ruta, encoding="utf-8") as f:
            cfg = json.load(f)

        self.art: Dict[str, Articulacion] = {}
        for a in cfg["articulaciones"]:
            a = {k: v for k, v in a.items() if not k.startswith("_")}
            art = Articulacion(**a)
            self.art[art.nombre] = art

        self.simulado = simulado
        self.pwm = None if simulado else PCA9685(
            bus=cfg.get("i2c_bus", 1),
            direccion=cfg.get("direccion", 0x40),
            frecuencia=cfg.get("frecuencia", 50))

        # arranca sin saber donde esta: se asume HOME hasta que se mueva
        self.pos = {n: a.home for n, a in self.art.items()}
        self.registro = []           # para depurar / graficar en el documento

    # ------------------------------------------------------------------
    def _escribir(self, nombre: str, angulo: float):
        a = self.art[nombre]
        if not (a.ang_min - 0.01 <= angulo <= a.ang_max + 0.01):
            raise FueraDeRango(
                "%s=%.1f fuera de [%.1f, %.1f]" % (nombre, angulo, a.ang_min, a.ang_max))
        if self.pwm:
            self.pwm.pulso_us(a.canal, a.pulso(angulo))
            if a.canal_espejo is not None:
                self.pwm.pulso_us(a.canal_espejo, a.pulso(a.espejo(angulo)))
        self.pos[nombre] = angulo

    # ------------------------------------------------------------------
    def mover(self, destino: Dict[str, float], duracion: Optional[float] = None,
              limitar: bool = True):
        """
        Mueve varias articulaciones a la vez. Todas salen y llegan juntas.

        duracion=None  -> la calcula sola con la vel_max de cada articulacion
                          (manda la mas lenta, que suele ser el hombro).
        limitar=True   -> recorta a los limites en vez de lanzar excepcion.
        """
        meta = {}
        for n, ang in destino.items():
            if n not in self.art:
                raise KeyError("No existe la articulacion '%s'. Hay: %s"
                               % (n, ", ".join(self.art)))
            meta[n] = self.art[n].limitar(ang) if limitar else ang

        if duracion is None:
            duracion = 0.0
            for n, ang in meta.items():
                recorrido = abs(ang - self.pos[n])
                duracion = max(duracion, recorrido / self.art[n].vel_max)
            duracion = max(duracion, 0.15)

        inicio = dict(self.pos)
        n_pasos = max(1, int(duracion * self.PASOS_POR_SEGUNDO))
        dt = duracion / n_pasos

        for k in range(1, n_pasos + 1):
            t = k / n_pasos
            s = t * t * (3 - 2 * t)        # suavizado: sale y llega con v=0
            for n, ang in meta.items():
                self._escribir(n, inicio[n] + (ang - inicio[n]) * s)
            self.registro.append((time.time(), dict(self.pos)))
            if not self.simulado:
                time.sleep(dt)
        return duracion

    # ------------------------------------------------------------------
    def home(self, duracion=2.5):
        """Lleva el brazo a la posicion de referencia, despacio."""
        return self.mover({n: a.home for n, a in self.art.items()}, duracion)

    def abrir_pinza(self, duracion=0.4):
        return self.mover({"pinza": self.art["pinza"].ang_max}, duracion)

    def cerrar_pinza(self, duracion=0.4):
        return self.mover({"pinza": self.art["pinza"].ang_min}, duracion)

    def liberar(self):
        """Quita la señal: los servos dejan de hacer fuerza.
        OJO: el brazo se cae por su peso. Usalo con el brazo recogido."""
        if self.pwm:
            self.pwm.apagar_todos()

    def posicion(self):
        return dict(self.pos)

    def cerrar(self):
        if self.pwm:
            self.pwm.cerrar()
            self.pwm = None

    # ------------------------------------------------------------------
    def __enter__(self):
        return self

    def __exit__(self, *e):
        try:
            self.liberar()
        finally:
            self.cerrar()
        return False
