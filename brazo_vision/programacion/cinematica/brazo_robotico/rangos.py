# -*- coding: utf-8 -*-
import json, math
from cinematica import Cinematica, FueraDeAlcance

for codo_arriba in (False, True):
    c=json.load(open('config_brazo.json',encoding='utf-8')); c['codo_arriba']=codo_arriba
    json.dump(c,open('_tmp.json','w'),ensure_ascii=False)
    k=Cinematica('_tmp.json')
    rng={n:[9e9,-9e9] for n in ('base','hombro','codo','muneca')}
    n_ok=0
    # barrido de toda la mesa util: 30..280 mm del centro, 20..200 mm de alto
    for u in range(30,281,5):
        for alt in range(20,201,10):
            for ang in range(-80,81,10):
                x=u*math.sin(math.radians(ang)); z=u*math.cos(math.radians(ang))+k.dz
                try: v=k.inversa(x,alt,z,180)
                except FueraDeAlcance: continue
                n_ok+=1
                for nm,val in zip(('base','hombro','codo','muneca'),v):
                    rng[nm][0]=min(rng[nm][0],val); rng[nm][1]=max(rng[nm][1],val)
    print('\n===== codo_arriba = %s =====  (%d poses validas)'%(codo_arriba,n_ok))
    for nm,(lo,hi) in rng.items():
        print('   %-8s  %7.1f  a %7.1f   -> recorrido %5.1f grados %s'
              %(nm,lo,hi,hi-lo,'  *** MAS DE 180!'if hi-lo>180 else ''))
