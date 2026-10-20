"""Diagnosi: scarica alcune pagine come le vede il radar e le salva per analizzarle.

Uso: python strumenti/scarica_pagine.py CARTELLA URL [URL ...]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from radar.rete import ErroreRete, pausa, scarica  # noqa: E402

cartella = Path(sys.argv[1])
cartella.mkdir(parents=True, exist_ok=True)
indice = []
for i, url in enumerate(sys.argv[2:], 1):
    try:
        html = scarica(url, tentativi=1)
        (cartella / f"{i:02d}.html").write_text(html, encoding="utf-8")
        indice.append(f"{i:02d}.html  {len(html):>8}  {url}")
    except ErroreRete as e:
        indice.append(f"{i:02d}       ERRORE {e}  {url}")
    pausa()
(cartella / "indice.txt").write_text("\n".join(indice) + "\n", encoding="utf-8")
print("\n".join(indice))
