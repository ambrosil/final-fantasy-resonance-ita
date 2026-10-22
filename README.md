# FINAL FANTASY RESONANCE — Traduzione italiana

Traduzione amatoriale in italiano dei testi di **FINAL FANTASY RESONANCE** per PC (Steam).

- Testi tradotti: tutti quelli del gioco (menu, dialoghi, missioni, descrizioni, tutorial… circa 26.700 voci).
- Il doppiaggio resta quello originale.
- Versione del gioco supportata: **1.0** (uscita del 22/10/2026).

## Installazione

1. **Installa Python**, se non ce l'hai: scaricalo da [python.org](https://www.python.org/downloads/) e durante l'installazione
   spunta **"Add python.exe to PATH"**. Basta una versione qualsiasi dalla 3.8 in su.
2. **Scarica la traduzione**: in alto in questa pagina premi **Code → Download ZIP** ed estrai lo ZIP dove vuoi.
3. **Chiudi il gioco** e fai doppio clic su **`installa.bat`**.
   Lo script trova da solo il gioco nelle librerie di Steam; se non ci riesce, ti chiede di incollare il percorso della cartella
   del gioco (per esempio `D:\SteamLibrary\steamapps\common\FINAL FANTASY RESONANCE`).
4. Avvia il gioco con la lingua impostata su **English**.

La traduzione prende il posto dell'inglese: con le altre lingue il gioco resta com'era.

## Disinstallazione

Chiudi il gioco e fai doppio clic su **`disinstalla.bat`**.
In alternativa, su Steam: tasto destro sul gioco → *Proprietà* → *File installati* → **Verifica l'integrità dei file**.

## Dopo un aggiornamento del gioco

Un aggiornamento può rimettere i testi in inglese. Rilancia **`installa.bat`**:

- se i testi del gioco non sono cambiati, la traduzione si reinstalla normalmente;
- se sono cambiati, lo script lo dice e non tocca nulla: serve una versione aggiornata della traduzione (tieni d'occhio questa pagina).

## Domande frequenti

**Perché devo usare la lingua English?**
Il gioco non prevede l'italiano, quindi la traduzione sostituisce i testi inglesi.

**Cosa modifica sul mio PC?**
Solo il file `FFRS\Content\Paks\FFRS-Windows.pak` del gioco, a cui aggiunge in fondo circa 4 MB (i testi italiani e un indice
che li punta), più un piccolo file `FFRS-Windows.pak.traduzione-ita.json` accanto, che serve per la disinstallazione.
I dati originali del gioco non vengono toccati e i salvataggi nemmeno. Lo script non si collega a internet.

**Funziona su Steam Deck / Linux?**
Dovrebbe: lo script cerca il gioco anche nelle cartelle di Steam su Linux. Lancialo da terminale con
`python3 installa_traduzione.py`. Non è stato provato.

**Uso da riga di comando**

```
python installa_traduzione.py                    installa
python installa_traduzione.py --disinstalla      disinstalla
python installa_traduzione.py --stato            controlla se è installata
python installa_traduzione.py "percorso\del\gioco"  se il gioco non viene trovato
```

## Errori nella traduzione

Se trovi errori o frasi che suonano male, apri una segnalazione nella sezione **Issues**, possibilmente con uno screenshot.

Per chi vuole proporre correzioni direttamente: `strumenti/locres_csv.py` esporta i testi in un CSV modificabile e li reimporta
(istruzioni all'inizio del file).

## Come funziona

Tutto il testo del gioco sta in un file, `FFRS/Content/Localization/Game/en/Game.locres`, dentro `FFRS-Windows.pak`
(formato Unreal Engine 5). Un pak si legge partendo dalla fine, dove un piccolo footer indica la posizione dell'indice dei file.
Lo script scrive in coda al pak il `Game.locres` italiano e un indice nuovo, identico all'originale tranne la voce di quel file.
Non serve decomprimere né ricostruire il pak, e la disinstallazione consiste nel riportare il file alla sua dimensione originale.

Prima di modificare qualcosa lo script controlla che il file testi inglese nel pak sia quello della versione supportata, e dopo
l'installazione verifica il risultato (se qualcosa non torna, annulla la modifica).

## Crediti

Traduzione e strumenti: **ambrosil**.

## Note legali

Progetto amatoriale e gratuito, non affiliato né approvato da Square Enix.
FINAL FANTASY e FINAL FANTASY RESONANCE sono marchi di Square Enix; tutti i diritti sul gioco e sui testi originali appartengono
ai rispettivi proprietari. Questo repository non contiene file del gioco: serve una copia originale acquistata su Steam.

Gli script sono distribuiti con licenza MIT (vedi `LICENSE`). Il file `traduzione/Game.locres` è distribuito gratuitamente
a scopo non commerciale.
