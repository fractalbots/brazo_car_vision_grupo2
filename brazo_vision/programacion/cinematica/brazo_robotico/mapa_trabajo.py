# -*- coding: utf-8 -*-
"""Genera el mapa de la zona de trabajo (PNG) para el documento."""
import math
from PIL import Image, ImageDraw, ImageFont
from cinematica import Cinematica

k = Cinematica()
S, W, H = 1.3, 900, 620
img = Image.new("RGB", (W, H), (250, 250, 250)); d = ImageDraw.Draw(img)
OX, OY = 110, H - 110

for u in range(0, 340, 2):
    for alt in range(0, 330, 2):
        if k.alcanzable(0, alt, u + k.dz, 180):
            px, py = OX + u * S, OY - alt * S
            d.rectangle([px, py, px + 3, py + 3], fill=(242, 120, 34))

d.line([OX - 60, OY, W - 30, OY], fill=(40, 40, 46), width=3)          # mesa
d.line([OX, OY, OX, 40], fill=(170, 170, 176), width=1)                # eje base
d.ellipse([OX - 5, OY - k.H * S - 5, OX + 5, OY - k.H * S + 5], fill=(30, 30, 36))

try:
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
except Exception:
    f = f2 = ImageFont.load_default()
d.text((30, 22), "ZONA DE TRABAJO  -  corte vertical, pinza apuntando abajo", font=f, fill=(25, 25, 30))
d.text((30, 52), "Naranja = el brazo puede llegar y agarrar.  Origen = eje de giro de la base.", font=f2, fill=(105, 105, 112))
d.text((OX + 8, OY - k.H * S - 26), "hombro  %.0f mm" % k.H, font=f2, fill=(30, 30, 36))
for u in range(0, 341, 50):
    d.line([OX + u * S, OY, OX + u * S, OY + 7], fill=(40, 40, 46), width=2)
    d.text((OX + u * S - 12, OY + 11), str(u), font=f2, fill=(70, 70, 76))
for alt in range(0, 301, 50):
    d.line([OX - 7, OY - alt * S, OX, OY - alt * S], fill=(40, 40, 46), width=2)
    d.text((OX - 48, OY - alt * S - 9), str(alt), font=f2, fill=(70, 70, 76))
d.text((W // 2 - 60, OY + 36), "distancia del centro (mm)", font=f2, fill=(70, 70, 76))
d.text((12, 150), "altura", font=f2, fill=(70, 70, 76))
d.text((12, 170), "(mm)", font=f2, fill=(70, 70, 76))
for alt, nota in ((40, None), (150, None)):
    r = k.alcance_maximo(alt)
    d.line([OX + r * S, OY - alt * S - 9, OX + r * S, OY - alt * S + 9], fill=(20, 20, 26), width=2)
    d.text((OX + r * S + 8, OY - alt * S - 9), "%.0f mm a %d mm de alto" % (r, alt), font=f2, fill=(20, 20, 26))
img.save("zona_de_trabajo.png"); print("zona_de_trabajo.png", img.size)
