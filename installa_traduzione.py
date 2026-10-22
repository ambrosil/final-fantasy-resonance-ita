#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Traduzione italiana amatoriale di FINAL FANTASY RESONANCE (Steam, PC).

Uso:
    python installa_traduzione.py                 installa (cerca il gioco da solo)
    python installa_traduzione.py --disinstalla   rimuove la traduzione
    python installa_traduzione.py --stato         dice se la traduzione e' installata
    python installa_traduzione.py "D:\\SteamLibrary\\steamapps\\common\\FINAL FANTASY RESONANCE"
                                                  indica a mano la cartella del gioco

Come funziona: il file con i testi inglesi del gioco (Game.locres) sta dentro
FFRS-Windows.pak. Lo script aggiunge in fondo al pak il file italiano e un nuovo
indice che punta a quello. I dati originali del pak non vengono toccati: per
disinstallare basta riportare il file alla sua dimensione originale.

Richiede solo Python 3.8 o successivo, nessuna libreria esterna.
"""
import argparse
import hashlib
import json
import os
import struct
import sys
import time

VERSIONE = "1.0"

# File testi italiano distribuito con lo script
LOCRES_RELATIVO = os.path.join("traduzione", "Game.locres")
LOCRES_SHA1 = "678482d418ec1ae0a880cf93316ed67b3fc84f75"

# Percorso del file da sostituire dentro il pak
BERSAGLIO = "FFRS/Content/Localization/Game/en/Game.locres"

# Versioni del gioco supportate: SHA-1 del Game.locres inglese originale, cosi'
# com'e' salvato (compresso) nel pak. Se Square Enix aggiorna i testi, cambia.
VERSIONI_SUPPORTATE = {
    "b97b18b7a6dc25585eb69a8f1ef8d03ffd88b9ac": "1.0 (uscita del 22/10/2026)",
}

NOME_GIOCO = "FINAL FANTASY RESONANCE"
PAK_RELATIVO = os.path.join("FFRS", "Content", "Paks", "FFRS-Windows.pak")
NOME_RIPRISTINO = "FFRS-Windows.pak.traduzione-ita.json"

PAK_MAGIC = 0x5A6F12E1
FOOTER = 221  # dimensione del footer di un pak versione 11


class Errore(Exception):
    pass


# --------------------------------------------------------------------------
# Lettura del pak (formato Unreal Engine 5, versione 11)
# --------------------------------------------------------------------------

class Lettore:
    def __init__(self, dati):
        self.b = dati
        self.p = 0

    def u32(self):
        v = struct.unpack_from("<I", self.b, self.p)[0]; self.p += 4; return v

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]; self.p += 4; return v

    def u64(self):
        v = struct.unpack_from("<Q", self.b, self.p)[0]; self.p += 8; return v

    def raw(self, n):
        v = self.b[self.p:self.p + n]; self.p += n; return v

    def fstr(self):
        n = self.i32()
        if n == 0:
            return ""
        if n > 0:
            return self.raw(n)[:-1].decode("utf-8", "replace")
        return self.raw(-n * 2)[:-2].decode("utf-16-le")


def scrivi_fstr(s):
    try:
        e = s.encode("ascii")
        return struct.pack("<i", len(e) + 1) + e + b"\0"
    except UnicodeEncodeError:
        e = s.encode("utf-16-le")
        return struct.pack("<i", -(len(e) // 2 + 1)) + e + b"\0\0"


def leggi_cartelle(r):
    out = []
    for _ in range(r.u32()):
        nome = r.fstr()
        out.append([nome, [[r.fstr(), r.i32()] for _ in range(r.u32())]])
    return out


def scrivi_cartelle(cartelle):
    b = struct.pack("<I", len(cartelle))
    for nome, files in cartelle:
        b += scrivi_fstr(nome) + struct.pack("<I", len(files))
        for fn, off in files:
            b += scrivi_fstr(fn) + struct.pack("<i", off)
    return b


def sha1(b):
    return hashlib.sha1(b).digest()


def leggi_pak(f, dimensione):
    """Legge l'indice del pak considerando il file lungo `dimensione` byte."""
    if dimensione < FOOTER:
        raise Errore("Il file pak e' troppo piccolo.")
    f.seek(dimensione - FOOTER)
    footer = f.read(FOOTER)
    magic, versione, ioff, isz = struct.unpack_from("<IIQQ", footer, 17)
    if magic != PAK_MAGIC:
        raise Errore("Il file non sembra un pak di Unreal Engine.")
    if versione != 11:
        raise Errore("Versione del pak non supportata (%d)." % versione)
    f.seek(ioff)
    indice = f.read(isz)
    if sha1(indice) != footer[41:61]:
        raise Errore("L'indice del pak e' danneggiato.")
    r = Lettore(indice)
    mount = r.fstr()
    conteggio = r.u32()
    seme = r.u64()
    if r.u32() != 1:
        raise Errore("Il pak non ha l'indice hash dei percorsi: formato non previsto.")
    phi_off, phi_len, phi_hash = r.u64(), r.u64(), r.raw(20)
    if r.u32() != 1:
        raise Errore("Il pak non ha l'indice delle cartelle: formato non previsto.")
    fdi_off, fdi_len, fdi_hash = r.u64(), r.u64(), r.raw(20)
    voci = r.raw(r.u32())
    if r.u32() != 0 or r.p != len(indice):
        raise Errore("Indice del pak in un formato non previsto.")
    f.seek(phi_off); phi = f.read(phi_len)
    f.seek(fdi_off); fdi = f.read(fdi_len)
    if sha1(phi) != phi_hash or sha1(fdi) != fdi_hash:
        raise Errore("Gli indici secondari del pak sono danneggiati.")
    q = Lettore(phi)
    hash_percorsi = [[q.u64(), q.u32()] for _ in range(q.u32())]
    cartelle_ridotte = leggi_cartelle(q)
    q = Lettore(fdi)
    cartelle = leggi_cartelle(q)
    return dict(footer=footer, mount=mount, conteggio=conteggio, seme=seme, voci=voci,
                hash_percorsi=hash_percorsi, cartelle_ridotte=cartelle_ridotte,
                cartelle=cartelle, dimensione=dimensione)


def dividi_percorso(pak, percorso):
    base = pak["mount"].replace("../../../", "")
    if not percorso.startswith(base):
        raise Errore("Il file cercato non sta sotto il punto di montaggio del pak.")
    rel = percorso[len(base):]
    if "/" in rel:
        cartella, nome = rel.rsplit("/", 1)
        return cartella + "/", nome
    return "/", rel


def cerca_voce(pak, percorso):
    cartella, nome = dividi_percorso(pak, percorso)
    for c, files in pak["cartelle"]:
        if c == cartella:
            for fn, off in files:
                if fn == nome:
                    return off
    raise Errore("Nel pak non c'e' %s." % percorso)


def decodifica_voce(voci, off):
    bits = struct.unpack_from("<I", voci, off)[0]; p = off + 4
    if bits & 0x3F == 0x3F:
        p += 4
    blocchi = (bits >> 6) & 0xFFFF
    cifrato = (bits >> 22) & 1
    compressione = (bits >> 23) & 0x3F
    if bits & (1 << 31):
        offset = struct.unpack_from("<I", voci, p)[0]; p += 4
    else:
        offset = struct.unpack_from("<Q", voci, p)[0]; p += 8
    if bits & (1 << 30):
        dim_orig = struct.unpack_from("<I", voci, p)[0]; p += 4
    else:
        dim_orig = struct.unpack_from("<Q", voci, p)[0]; p += 8
    dim = dim_orig
    if compressione:
        if bits & (1 << 29):
            dim = struct.unpack_from("<I", voci, p)[0]; p += 4
        else:
            dim = struct.unpack_from("<Q", voci, p)[0]; p += 8
    intestazione = 53 + (4 + 16 * blocchi if compressione and blocchi else 0)
    return dict(offset=offset, dim=dim, dim_orig=dim_orig, compressione=compressione,
                cifrato=cifrato, intestazione=intestazione)


def leggi_dati(f, voce):
    f.seek(voce["offset"] + voce["intestazione"])
    return f.read(voce["dim"])


# --------------------------------------------------------------------------
# Patch
# --------------------------------------------------------------------------

def costruisci_coda(pak, percorso, dati):
    """Restituisce i byte da aggiungere in fondo al pak."""
    vecchia = cerca_voce(pak, percorso)
    voci = pak["voci"]
    nuovo_offset = pak["dimensione"]
    intest = (struct.pack("<QQQI", 0, len(dati), len(dati), 0) + sha1(dati)
              + b"\0" + struct.pack("<I", 0))
    bits = 0x20000000
    if nuovo_offset < 2 ** 32:
        bits |= 0x80000000
    if len(dati) < 2 ** 32:
        bits |= 0x40000000
    voce = struct.pack("<I", bits)
    voce += struct.pack("<I", nuovo_offset) if nuovo_offset < 2 ** 32 else struct.pack("<Q", nuovo_offset)
    voce += struct.pack("<I", len(dati)) if len(dati) < 2 ** 32 else struct.pack("<Q", len(dati))
    nuova = len(voci)
    voci2 = voci + voce

    trovati = [e for e in pak["hash_percorsi"] if e[1] == vecchia]
    if len(trovati) != 1:
        raise Errore("Indice hash dei percorsi in un formato non previsto.")
    trovati[0][1] = nuova
    cartella, nome = dividi_percorso(pak, percorso)

    def aggiorna(cartelle):
        n = 0
        for c, files in cartelle:
            if c == cartella:
                for x in files:
                    if x[0] == nome and x[1] == vecchia:
                        x[1] = nuova; n += 1
        return n

    aggiorna(pak["cartelle_ridotte"])
    if aggiorna(pak["cartelle"]) != 1:
        raise Errore("Indice delle cartelle in un formato non previsto.")
    phi = (struct.pack("<I", len(pak["hash_percorsi"]))
           + b"".join(struct.pack("<QI", a, b) for a, b in pak["hash_percorsi"])
           + scrivi_cartelle(pak["cartelle_ridotte"]))
    fdi = scrivi_cartelle(pak["cartelle"])
    corpo = intest + dati
    ioff = nuovo_offset + len(corpo)

    def primario(phi_off, fdi_off):
        b = scrivi_fstr(pak["mount"]) + struct.pack("<IQ", pak["conteggio"], pak["seme"])
        b += struct.pack("<IQQ", 1, phi_off, len(phi)) + sha1(phi)
        b += struct.pack("<IQQ", 1, fdi_off, len(fdi)) + sha1(fdi)
        b += struct.pack("<I", len(voci2)) + voci2 + struct.pack("<I", 0)
        return b

    lung = len(primario(0, 0))
    phi_off = ioff + lung
    fdi_off = phi_off + len(phi)
    indice = primario(phi_off, fdi_off)
    ft = pak["footer"]
    footer = (ft[:17] + struct.pack("<IIQQ", PAK_MAGIC, 11, ioff, len(indice))
              + sha1(indice) + ft[61:])
    return corpo + indice + phi + fdi + footer


def esamina(percorso_pak, dimensione=None, versioni=None):
    """Dice in che stato e' il pak rispetto alla traduzione."""
    versioni = VERSIONI_SUPPORTATE if versioni is None else versioni
    with open(percorso_pak, "rb") as f:
        if dimensione is None:
            f.seek(0, 2); dimensione = f.tell()
        pak = leggi_pak(f, dimensione)
        voce = decodifica_voce(pak["voci"], cerca_voce(pak, BERSAGLIO))
        if voce["cifrato"]:
            raise Errore("Il file testi nel pak e' cifrato: versione del gioco non supportata.")
        dati = leggi_dati(f, voce)
    impronta = hashlib.sha1(dati).hexdigest()
    if voce["compressione"] == 0 and impronta == LOCRES_SHA1:
        return dict(stato="installata", dimensione=dimensione)
    if voce["compressione"] == 0:
        return dict(stato="altra_traduzione", dimensione=dimensione)
    if impronta in versioni:
        return dict(stato="originale", versione=versioni[impronta], dimensione=dimensione)
    return dict(stato="non_supportata", dimensione=dimensione)


# --------------------------------------------------------------------------
# Ricerca del gioco
# --------------------------------------------------------------------------

def librerie_steam():
    cartelle = []
    radici = []
    if sys.platform == "win32":
        try:
            import winreg
            for radice, chiave, valore in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ):
                try:
                    with winreg.OpenKey(radice, chiave) as k:
                        radici.append(winreg.QueryValueEx(k, valore)[0])
                except OSError:
                    pass
        except ImportError:
            pass
        radici += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    else:
        radici += [os.path.expanduser("~/.steam/steam"), os.path.expanduser("~/.local/share/Steam")]
    for radice in radici:
        radice = os.path.normpath(radice)
        cartelle.append(radice)
        vdf = os.path.join(radice, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf, encoding="utf-8", errors="replace") as fh:
                for riga in fh:
                    parti = riga.strip().split('"')
                    if len(parti) >= 4 and parti[1].lower() == "path":
                        cartelle.append(os.path.normpath(parti[3].replace("\\\\", "\\")))
        except OSError:
            pass
    visti, out = set(), []
    for c in cartelle:
        k = os.path.normcase(c)
        if k not in visti:
            visti.add(k); out.append(c)
    return out


def trova_pak(indicato=None):
    candidati = []
    if indicato:
        p = os.path.abspath(indicato.strip().strip('"'))
        candidati += [p, os.path.join(p, PAK_RELATIVO), os.path.join(p, "FFRS-Windows.pak")]
    else:
        qui = os.path.dirname(os.path.abspath(__file__))
        p = qui
        for _ in range(6):  # se la cartella dello script e' dentro quella del gioco
            candidati.append(os.path.join(p, PAK_RELATIVO))
            p = os.path.dirname(p)
        for lib in librerie_steam():
            candidati.append(os.path.join(lib, "steamapps", "common", NOME_GIOCO, PAK_RELATIVO))
    for c in candidati:
        if os.path.isfile(c) and os.path.basename(c).lower() == "ffrs-windows.pak":
            return c
    return None


# --------------------------------------------------------------------------
# Comandi
# --------------------------------------------------------------------------

def percorso_ripristino(pak):
    return os.path.join(os.path.dirname(pak), NOME_RIPRISTINO)


def apri_in_scrittura(pak):
    try:
        return open(pak, "r+b")
    except PermissionError:
        raise Errore("Non riesco a scrivere sul file del gioco. Chiudi il gioco e riprova.")


def installa(pak, versioni=None):
    qui = os.path.dirname(os.path.abspath(__file__))
    locres = os.path.join(qui, LOCRES_RELATIVO)
    if not os.path.isfile(locres):
        raise Errore("Manca il file %s accanto allo script." % LOCRES_RELATIVO)
    with open(locres, "rb") as fh:
        dati = fh.read()
    if hashlib.sha1(dati).hexdigest() != LOCRES_SHA1:
        raise Errore("Il file %s non e' quello previsto (scaricato male?)." % LOCRES_RELATIVO)

    st = esamina(pak, versioni=versioni)
    if st["stato"] == "installata":
        print("La traduzione e' gia' installata. Niente da fare.")
        return
    if st["stato"] in ("altra_traduzione",):
        info = leggi_ripristino(pak)
        if info is None:
            raise Errore("Il pak contiene gia' una modifica che non riconosco. "
                         "Usa 'Verifica integrita' dei file' su Steam e poi riprova.")
        print("Trovata una versione precedente della traduzione: la rimuovo prima.")
        disinstalla(pak, silenzioso=True)
        st = esamina(pak, versioni=versioni)
    if st["stato"] == "non_supportata":
        raise Errore("Questa versione del gioco ha testi diversi da quelli tradotti "
                     "(probabilmente un aggiornamento). Serve una versione aggiornata della traduzione.")
    if st["stato"] != "originale":
        raise Errore("Stato del pak inatteso: %s" % st["stato"])

    print("Gioco trovato, versione %s." % st["versione"])
    dimensione = st["dimensione"]
    with open(pak, "rb") as f:
        f.seek(dimensione - FOOTER)
        footer = f.read(FOOTER)
        coda = costruisci_coda(leggi_pak(f, dimensione), BERSAGLIO, dati)
    info = dict(programma="Traduzione italiana FINAL FANTASY RESONANCE", versione=VERSIONE,
                data=time.strftime("%Y-%m-%d %H:%M:%S"), dimensione_originale=dimensione,
                footer_originale_sha1=hashlib.sha1(footer).hexdigest(),
                dimensione_patchata=dimensione + len(coda))
    with apri_in_scrittura(pak) as f:
        with open(percorso_ripristino(pak), "w", encoding="utf-8") as fh:
            json.dump(info, fh, indent=1)
        f.seek(0, 2)
        if f.tell() != dimensione:
            raise Errore("Il file del gioco e' cambiato durante l'installazione. Riprova.")
        try:
            f.write(coda)
            f.flush()
            os.fsync(f.fileno())
        except Exception:
            f.truncate(dimensione)
            raise
    if esamina(pak, versioni=versioni)["stato"] != "installata":
        with apri_in_scrittura(pak) as f:
            f.truncate(dimensione)
        raise Errore("Verifica fallita dopo l'installazione: ho annullato la modifica.")
    print("Traduzione installata.")
    print("Avvia il gioco con la lingua impostata su English.")


def leggi_ripristino(pak):
    try:
        with open(percorso_ripristino(pak), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def disinstalla(pak, silenzioso=False):
    info = leggi_ripristino(pak)
    dim_attuale = os.path.getsize(pak)
    if info is None:
        st = esamina(pak)
        if st["stato"] in ("originale", "non_supportata"):
            print("La traduzione non e' installata.")
            return
        raise Errore("Non trovo il file %s. Usa 'Verifica integrita' dei file' su Steam "
                     "per ripristinare il gioco." % NOME_RIPRISTINO)
    originale = info["dimensione_originale"]
    if dim_attuale == originale:
        print("Il gioco e' gia' nella versione originale.")
    else:
        if dim_attuale != info["dimensione_patchata"]:
            raise Errore("Il file del gioco e' cambiato dopo l'installazione (aggiornamento?). "
                         "Usa 'Verifica integrita' dei file' su Steam.")
        with apri_in_scrittura(pak) as f:
            f.truncate(originale)
    with open(pak, "rb") as f:
        f.seek(originale - FOOTER)
        ok = hashlib.sha1(f.read(FOOTER)).hexdigest() == info["footer_originale_sha1"]
    if not ok:
        raise Errore("Il pak non corrisponde all'originale. Usa 'Verifica integrita' dei file' su Steam.")
    try:
        os.remove(percorso_ripristino(pak))
    except OSError:
        pass
    if not silenzioso:
        print("Traduzione rimossa: il gioco e' tornato in inglese.")


def mostra_stato(pak):
    st = esamina(pak)
    testi = {
        "installata": "La traduzione e' installata.",
        "originale": "Gioco originale (versione %s): traduzione non installata." % st.get("versione"),
        "non_supportata": "Gioco originale, ma versione dei testi non supportata da questa traduzione.",
        "altra_traduzione": "Il pak contiene una modifica diversa da questa versione della traduzione.",
    }
    print(testi[st["stato"]])


def main(argv=None):
    ap = argparse.ArgumentParser(description="Traduzione italiana di FINAL FANTASY RESONANCE")
    ap.add_argument("cartella", nargs="?", help="cartella del gioco (facoltativa)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--disinstalla", action="store_true", help="rimuove la traduzione")
    g.add_argument("--stato", action="store_true", help="mostra se la traduzione e' installata")
    args = ap.parse_args(argv)

    print("Traduzione italiana di %s - versione %s" % (NOME_GIOCO, VERSIONE))
    print()
    pak = trova_pak(args.cartella)
    if pak is None and not args.cartella:
        print("Non ho trovato il gioco nelle librerie di Steam.")
        try:
            risposta = input("Incolla il percorso della cartella del gioco e premi Invio:\n> ")
        except EOFError:
            risposta = ""
        pak = trova_pak(risposta) if risposta.strip() else None
    if pak is None:
        print("ERRORE: non trovo FFRS-Windows.pak. Indica la cartella del gioco, per esempio:")
        print('  python installa_traduzione.py "D:\\SteamLibrary\\steamapps\\common\\FINAL FANTASY RESONANCE"')
        return 1
    print("File del gioco: %s" % pak)
    try:
        if args.stato:
            mostra_stato(pak)
        elif args.disinstalla:
            disinstalla(pak)
        else:
            installa(pak)
    except Errore as e:
        print("ERRORE: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
