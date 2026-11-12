# Cinemática inversa

Le das una coordenada de la mesa en milímetros y te devuelve los ángulos de
cada articulación. Es lo que conecta la visión artificial con los servos.

---

## Sistema de coordenadas

```
        +Y  arriba
         |
         |        +Z  hacia adelante (al frente del brazo)
         |       /
         |      /
         +-----------  +X  a la derecha

   origen = el eje vertical de giro de la base, al nivel de la mesa
```

El **cabeceo** es hacia dónde apunta la pinza, medido desde la vertical:

| Cabeceo | Apunta |
|---|---|
| 0° | arriba |
| 90° | horizontal, al frente |
| **180°** | **abajo** — el que usas para recoger de la mesa |

## Ángulos de las articulaciones

Con las cuatro en **0 el brazo queda vertical**, igual que salió del CAD. Así
verificas a ojo que no te equivocaste de signo.

| Articulación | 0 grados es | Positivo |
|---|---|---|
| `base` | mirando al frente (+Z) | hacia la derecha |
| `hombro` | brazo vertical | se inclina al frente |
| `codo` | antebrazo sigue recto al brazo | se dobla |
| `muneca` | sigue recta al antebrazo | se dobla |

Codo y muñeca son **relativos** al eslabón anterior, no absolutos. Es la
convención normal en robótica y es la que hace que la suma de ángulos te dé
directo la orientación de la pinza.

---

## Medidas

Sacadas de los ejes de giro del modelo CAD, no de los bounding boxes:

| | Altura del eje | Eslabón |
|---|---|---|
| Hombro | 102,0 mm | |
| Codo | 238,4 mm | **L1 = 136,4** |
| Muñeca | 377,9 mm | **L2 = 139,5** |
| Punta de la pinza | 487,0 mm | **L3 = 109,1** |

Con el pedestal de 15 mm, el hombro queda a **117 mm** de la mesa.
Comprobación: 102 + 136,4 + 139,5 + 109,1 = 487,0 ✓

**Estas medidas son un punto de partida.** Ver la calibración abajo.

---

## Zona de trabajo real

Ver `zona_de_trabajo.png`.

| Altura sobre la mesa | Llega hasta |
|---|---|
| 40 mm (agarrando un cubo) | **274 mm** del centro |
| 100 mm | 260 mm |
| 150 mm | 236 mm |
| 200 mm | 198 mm |

**Pon la zona de los cubos entre 100 y 250 mm del eje de la base.** Más cerca
la matemática dice que llega, pero el brazo real se choca consigo mismo. Más
lejos no alcanza.

---

## Uso

```python
from mover_xyz import BrazoXYZ

with BrazoXYZ() as r:
    r.b.home()
    r.ir_a(x=120, y=60, z=200)        # punta ahí, pinza apuntando abajo
    r.recoger(x=120, z=210)           # baja, cierra, sube
    r.soltar(x=-150, z=170)           # baja, abre, sube
```

Solo la matemática, sin hardware:

```python
from cinematica import Cinematica
k = Cinematica()
base, hombro, codo, muneca = k.inversa(120, 60, 200, cabeceo=180)
x, y, z, cab = k.directa(base, hombro, codo, muneca)   # comprobar
```

---

## Calibración contra el brazo real — no te la saltes

Los números del CAD son exactos, pero el brazo armado no lo es. Lo que
desplaza la realidad:

- Las estrías del disco del servo son de 25 dientes: solo puedes montarlo
  cada **14,4°**. El cero nunca te queda perfecto.
- Tolerancias de impresión y juego en los pivotes.
- El pedestal de 15 mm que imprimas puede no salir exacto.

### Procedimiento

**1. Mide la altura real del hombro.** Con el brazo armado y vertical, mide
con calibrador del plano de la mesa al centro del eje del hombro. Pon ese
número en `altura_hombro` de `config_brazo.json`.

**2. Mide la altura total.** Con todas las articulaciones en 0 el brazo debe
quedar vertical y la punta a 502 mm. Si te da 497, **no cambies L1 L2 L3**:
casi seguro el cero de algún servo está corrido. Vuelve a `calibrar.py`.

**3. Prueba de los tres puntos.** Marca tres cruces en la mesa con posiciones
conocidas, por ejemplo (0, 200), (150, 180) y (−150, 180). Manda el brazo a
cada una con una punta fina en la pinza y mide cuánto se desvía.

- Error parejo en todas → corrige `altura_hombro`.
- Error que crece con la distancia → corrige `L1` y `L2` proporcionalmente.
- Error solo girando → el cero del servo de la base está corrido.

**4. Repite hasta bajar de 3 mm.** Con eso agarras cubos de 25 mm sin
problema, y es un número honesto para poner en "pruebas de funcionamiento".

---

## Verificación

```bash
python3 prueba_cinematica.py
```

Comprueba que HOME da 502 mm, hace ida y vuelta inversa→directa (debe dar
error 0,000000 mm), lista el alcance por altura, dibuja el mapa en texto y
avisa si algún punto se sale de los límites de los servos.

```bash
python3 mapa_trabajo.py      # regenera zona_de_trabajo.png
```

---

## Dos detalles de diseño

**Codo arriba.** Hay dos soluciones matemáticas para llegar a cada punto. Se
usa la de codo arriba (`codo_arriba: true`) porque la muñeca solo recorre
100° en vez de 135°, y eso te deja margen dentro de los 180° del servo.

**Los límites de `config_servos.json` salieron del barrido**, no son
inventados: se recorrió toda la mesa útil y se midió cuánto necesita cada
articulación. Pero son **límites de software**. Los topes mecánicos reales
los encuentras tú con `calibrar.py`, y esos mandan: si el plástico topa antes,
baja el límite en el JSON.

---

## Lo que sigue

La visión artificial: detectar los cubos por color, pasar de píxeles a
milímetros sobre la mesa (homografía con 4 puntos de referencia), y meter esa
coordenada en `r.recoger(x, z)`.
