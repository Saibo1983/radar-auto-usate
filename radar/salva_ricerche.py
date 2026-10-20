"""Salva in config/ricerche.json le ricerche inviate dall'app.

L'app avvia il workflow salva-ricerche.yml con l'elenco completo delle ricerche.
Si tengono solo i campi noti; orario e notifiche del file restano come sono.

Uso: RICERCHE='[{"id": "r1", "attiva": true, "marca": "Fiat", "modello": "Panda"}]' python -m radar.salva_ricerche
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from .__main__ import RADICE
from .adesso import pulisci

MAX_RICERCHE = 30


def aggiorna(percorso: Path, grezze: list) -> list[dict]:
    ricerche = []
    for i, g in enumerate(x for x in grezze if isinstance(x, dict)):
        if len(ricerche) == MAX_RICERCHE:
            break
        id_r = g.get("id") if isinstance(g.get("id"), str) and re.fullmatch(r"[A-Za-z0-9_-]{1,30}", g["id"]) else f"r{i + 1}"
        ricerche.append({"id": id_r, "attiva": g.get("attiva") is not False, **pulisci(g)})
    cfg = json.loads(percorso.read_text(encoding="utf-8"))
    cfg["ricerche"] = ricerche
    percorso.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ricerche


def main() -> int:
    grezze = json.loads(os.environ.get("RICERCHE") or "null")
    if not isinstance(grezze, list):
        print("RICERCHE deve essere un elenco")
        return 1
    ricerche = aggiorna(RADICE / "config" / "ricerche.json", grezze)
    attive = sum(r["attiva"] for r in ricerche)
    print(f"Salvate {len(ricerche)} ricerche, {attive} attive")
    return 0


if __name__ == "__main__":
    sys.exit(main())
