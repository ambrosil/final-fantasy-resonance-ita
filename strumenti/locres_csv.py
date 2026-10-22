#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Per chi vuole correggere la traduzione.

    python strumenti/locres_csv.py esporta traduzione/Game.locres testi.csv
    (modifica la colonna "testo" di testi.csv con un editor o con Excel/LibreOffice, salvando in UTF-8)
    python strumenti/locres_csv.py importa traduzione/Game.locres testi.csv traduzione/Game.locres

Dopo aver cambiato Game.locres va aggiornato LOCRES_SHA1 in installa_traduzione.py
(il comando "importa" stampa il valore nuovo).
"""
import csv, hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import locres


def esporta(src, out):
    L = locres.to_values(locres.parse(open(src, "rb").read()))
    with open(out, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["chiave", "testo"])
        for _, ns, keys in L["ns"]:
            for k in keys:
                w.writerow([ns + "/" + k[1], k[3]])
    print("esportate le voci in", out)


def importa(src, csv_path, out):
    L = locres.to_values(locres.parse(open(src, "rb").read()))
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        nuovi = {r["chiave"]: r["testo"] for r in csv.DictReader(fh)}
    cambiate = 0
    for _, ns, keys in L["ns"]:
        for k in keys:
            t = nuovi.get(ns + "/" + k[1])
            if t is not None and t != k[3]:
                k[3] = t; cambiate += 1
    dati = locres.build(L)
    open(out, "wb").write(dati)
    print("voci cambiate:", cambiate)
    print("LOCRES_SHA1 =", hashlib.sha1(dati).hexdigest())


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "esporta":
        esporta(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 5 and sys.argv[1] == "importa":
        importa(*sys.argv[2:5])
    else:
        print(__doc__)
