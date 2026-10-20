"""Ricerca immediata avviata dal pulsante "Cerca adesso" dell'app.

Esegue una sola ricerca, senza avvisi e senza toccare gli annunci già visti,
e scrive i risultati in data/ricerca-adesso.json per l'app.

Uso: RICERCA='{"marca": "Fiat", "modello": "Ducato", "tipo": "furgone"}' python -m radar.adesso ID
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .__main__ import RADICE, cerca, dati_risultati, scrivi_json
from .siti import SITI
from .stato import Stato

CAMPI_TESTO = ("nome", "marca", "modello", "carrozzeria", "alimentazione", "cambio", "cap", "regione", "venditore",
               "tipo")
CAMPI_NUMERO = ("prezzo_min", "prezzo_max", "anno_min", "anno_max", "km_max", "potenza_min_cv", "raggio_km")


def pulisci(grezza: dict) -> dict:
    """Tiene solo i campi noti, con il tipo giusto: l'input arriva da fuori."""
    r = {}
    for k in CAMPI_TESTO:
        v = grezza.get(k)
        if isinstance(v, str) and v.strip():
            r[k] = v.strip()[:60]
    for k in CAMPI_NUMERO:
        v = grezza.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
            r[k] = int(v)
    fonti = grezza.get("fonti")
    if isinstance(fonti, list):
        r["fonti"] = [f for f in fonti if f in SITI]
    if r.get("tipo") not in ("auto", "furgone"):
        r["tipo"] = "auto"
    r.setdefault("nome", " ".join(x for x in (r.get("marca"), r.get("modello")) if x) or "Ricerca")
    return r


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    richiesta = argv[0] if argv else ""
    ricerca = {**pulisci(json.loads(os.environ.get("RICERCA") or "{}")), "id": "adesso"}
    adesso = datetime.now(ZoneInfo("Europe/Rome"))
    print(f"Ricerca immediata: {ricerca}")

    tutti, problemi, _ = cerca({"ricerche": [ricerca]}, None)
    elenco = [(r, sorted(Stato.togli_doppioni(annunci), key=lambda a: a.prezzo or 0)) for r, annunci in tutti]
    dati = dati_risultati(adesso, cerca.righe, elenco, set(), problemi)
    dati["richiesta"] = richiesta
    scrivi_json(RADICE / "data" / "ricerca-adesso.json", dati)
    print(f"Trovati {sum(len(a) for _, a in elenco)} annunci")
    return 0


if __name__ == "__main__":
    sys.exit(main())
