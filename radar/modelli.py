"""Strutture dati condivise."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field


def normalizza(testo: str | None) -> str:
    """Minuscolo, senza accenti e con un solo spazio tra le parole."""
    if not testo:
        return ""
    testo = unicodedata.normalize("NFD", str(testo))
    testo = "".join(c for c in testo if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", testo.lower()).strip()


def slug(testo: str | None) -> str:
    return normalizza(testo).replace(" ", "-")


@dataclass
class Annuncio:
    fonte: str
    url: str
    titolo: str = ""
    prezzo: int | None = None
    anno: int | None = None
    km: int | None = None
    carburante: str = ""
    cambio: str = ""
    luogo: str = ""
    immagine: str = ""
    extra: dict = field(default_factory=dict)

    def chiave_auto(self) -> str:
        """Impronta per riconoscere la stessa auto pubblicata su siti diversi.

        Serve titolo, prezzo e km: senza questi dati non si rischia di unire
        due auto diverse e si usa solo l'indirizzo dell'annuncio.
        """
        if not (self.titolo and self.prezzo and self.km is not None):
            return ""
        parole = normalizza(self.titolo).split()[:2]
        return "|".join([
            " ".join(parole),
            str(self.anno or ""),
            str(round(self.km / 1000)),
            str(round(self.prezzo / 100)),
        ])

    def to_dict(self) -> dict:
        return asdict(self)
