# -*- coding: utf-8 -*-
"""
Cinematica directa e inversa del brazo robotico.

CONVENCION DE ANGULOS  (todos en grados, 0 = brazo recto hacia arriba)

    base    giro sobre el eje vertical. 0 = mirando al frente (+Z).
                                        positivo = hacia +X (derecha).
    hombro  inclinacion desde la vertical. 0 = arriba, positivo = al frente.
    codo    RELATIVO al brazo. 0 = antebrazo sigue derecho al brazo.
    muneca  RELATIVA al antebrazo. 0 = sigue derecho.

Con las cuatro en 0 el brazo queda vertical y la punta a 502 mm. Igualito
a como salio del CAD, asi que es facil verificar a ojo.

SISTEMA DE COORDENADAS DE LA MESA

    origen  = el eje vertical de giro de la base, al nivel de la mesa
    +Z      = hacia adelante (al frente del brazo)
    +X      = a la derecha
    +Y      = hacia arriba

El angulo 'cabeceo' es la direccion a la que apunta la pinza, medida desde
la vertical:
      0   = apuntando hacia arriba
     90   = horizontal, hacia adelante
    180   = apuntando hacia abajo  <-- el que usas para recoger de la mesa
"""

import json
import math
import os

AQUI = os.path.dirname(os.path.abspath(__file__))


class FueraDeAlcance(ValueError):
    pass


class Cinematica:
    def __init__(self, config=None):
        ruta = config or os.path.join(AQUI, "config_brazo.json")
        with open(ruta, encoding="utf-8") as f:
            c = json.load(f)
        self.H = c["altura_hombro"]
        self.L1 = c["L1"]
        self.L2 = c["L2"]
        self.L3 = c["L3"]
        self.dz = c.get("offset_base_z", 0.0)
        self.codo_arriba = c.get("codo_arriba", False)

    # ================= CINEMATICA DIRECTA =================
    def directa(self, base, hombro, codo, muneca):
        """Angulos -> coordenada (x, y, z) de la punta y cabeceo."""
        a2 = math.radians(hombro)
        a3 = a2 + math.radians(codo)
        a4 = a3 + math.radians(muneca)

        # en el plano vertical del brazo: u = distancia horizontal, v = altura
        u = self.L1 * math.sin(a2) + self.L2 * math.sin(a3) + self.L3 * math.sin(a4)
        v = self.H + self.L1 * math.cos(a2) + self.L2 * math.cos(a3) + self.L3 * math.cos(a4)

        t = math.radians(base)
        x = u * math.sin(t)
        z = u * math.cos(t) + self.dz
        return x, v, z, math.degrees(a4)

    # ================= CINEMATICA INVERSA =================
    def inversa(self, x, y, z, cabeceo=180.0):
        """
        (x, y, z) en mm + cabeceo en grados -> (base, hombro, codo, muneca).
        Lanza FueraDeAlcance si el punto no se puede alcanzar.
        """
        zz = z - self.dz
        base = math.degrees(math.atan2(x, zz))
        u = math.hypot(x, zz)                 # distancia horizontal
        v = y                                 # altura sobre la mesa

        psi = math.radians(cabeceo)
        # centro de la muneca: se retrocede L3 en la direccion del cabeceo
        uw = u - self.L3 * math.sin(psi)
        vw = v - self.L3 * math.cos(psi) - self.H

        D = math.hypot(uw, vw)
        if D > self.L1 + self.L2:
            raise FueraDeAlcance(
                "Punto muy lejos: la muneca quedaria a %.1f mm y el maximo es %.1f mm"
                % (D, self.L1 + self.L2))
        if D < abs(self.L1 - self.L2):
            raise FueraDeAlcance(
                "Punto muy cerca: la muneca quedaria a %.1f mm y el minimo es %.1f mm"
                % (D, abs(self.L1 - self.L2)))

        cos3 = (D * D - self.L1 ** 2 - self.L2 ** 2) / (2 * self.L1 * self.L2)
        cos3 = max(-1.0, min(1.0, cos3))
        a3 = math.acos(cos3)
        if not self.codo_arriba:
            a3 = -a3

        beta = math.atan2(uw, vw)
        gama = math.atan2(self.L2 * math.sin(a3), self.L1 + self.L2 * math.cos(a3))
        a2 = beta - gama
        a4 = psi - a2 - a3

        return (base,
                math.degrees(a2),
                math.degrees(a3),
                math.degrees(a4))

    # ================= AYUDAS =================
    def alcanzable(self, x, y, z, cabeceo=180.0):
        try:
            self.inversa(x, y, z, cabeceo)
            return True
        except FueraDeAlcance:
            return False

    def alcance_maximo(self, altura, cabeceo=180.0):
        """Distancia horizontal maxima a la que llega a una altura dada."""
        mejor = 0.0
        u = 0.0
        while u < self.L1 + self.L2 + self.L3 + 50:
            if self.alcanzable(0.0, altura, u + self.dz, cabeceo):
                mejor = u
            u += 0.5
        return mejor
