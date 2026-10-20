"""Memoria degli annunci già segnalati, salvata in data/stato.json."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from .modelli import Annuncio

GIORNI_MEMORIA = 120


class Stato:
    def __init__(self, percorso: Path):
        self.percorso = percorso
        try:
            self.dati = json.loads(percorso.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            self.dati = {}
        self.dati.setdefault("ultima_esecuzione", None)
        self.dati.setdefault("visti", {})

    @property
    def ultima_esecuzione(self) -> str | None:
        return self.dati["ultima_esecuzione"]

    def _visti(self, id_ricerca: str) -> dict:
        return self.dati["visti"].setdefault(id_ricerca, {"url": {}, "auto": {}})

    @staticmethod
    def togli_doppioni(annunci: list[Annuncio]) -> list[Annuncio]:
        """La stessa auto pubblicata su più siti compare una volta sola."""
        return _filtra(annunci, {"url": {}, "auto": {}})

    def nuovi(self, id_ricerca: str, annunci: list[Annuncio], ignora_visti: bool = False) -> list[Annuncio]:
        """Annunci mai visti prima per questa ricerca, senza doppioni tra siti.

        Con ignora_visti toglie solo i doppioni e restituisce anche gli annunci già segnalati.
        """
        if ignora_visti:
            return self.togli_doppioni(annunci)
        return _filtra(annunci, self._visti(id_ricerca))

    def ricorda(self, id_ricerca: str, annunci: list[Annuncio], oggi: date) -> None:
        visti = self._visti(id_ricerca)
        g = oggi.isoformat()
        for a in annunci:
            visti["url"].setdefault(a.url, g)
            chiave = a.chiave_auto()
            if chiave:
                visti["auto"].setdefault(chiave, g)

    def pulisci(self, oggi: date, ricerche_attive: set[str]) -> None:
        limite = (oggi - timedelta(days=GIORNI_MEMORIA)).isoformat()
        for id_ricerca in list(self.dati["visti"]):
            if id_ricerca not in ricerche_attive:
                del self.dati["visti"][id_ricerca]
                continue
            for gruppo in self.dati["visti"][id_ricerca].values():
                for k in [k for k, g in gruppo.items() if g < limite]:
                    del gruppo[k]

    def salva(self, oggi: date) -> None:
        self.dati["ultima_esecuzione"] = oggi.isoformat()
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        self.percorso.write_text(json.dumps(self.dati, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
                                 encoding="utf-8")


def _filtra(annunci: list[Annuncio], visti: dict) -> list[Annuncio]:
    out, chiavi_oggi = [], set()
    for a in annunci:
        chiave = a.chiave_auto()
        if a.url in visti["url"] or (chiave and (chiave in visti["auto"] or chiave in chiavi_oggi)):
            continue
        if chiave:
            chiavi_oggi.add(chiave)
        out.append(a)
    return out
