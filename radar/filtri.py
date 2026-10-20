"""Applica i filtri della ricerca agli annunci letti.

Un dato che il sito non fornisce non esclude l'annuncio: meglio un avviso in
più che un'auto giusta persa.
"""

from __future__ import annotations

from .modelli import Annuncio, normalizza

PAROLE_CARBURANTE = {
    "benzina": ("benzina", "petrol", "gasoline", "benzin"),
    "diesel": ("diesel", "gasolio"),
    "ibrida": ("ibrid", "hybrid", "hybride"),
    "elettrica": ("elettric", "electric", "elektro"),
    "gpl": ("gpl", "lpg", "autogas"),
    "metano": ("metano", "cng", "erdgas", "natural power"),
}
PAROLE_CAMBIO = {
    "manuale": ("manual", "schalt"),
    "automatico": ("automat", "dsg", "cvt", "sequenziale", "robotizzato"),
}


def _contiene(testo: str, parole: tuple[str, ...]) -> bool:
    return any(p in testo for p in parole)


# Sigle dei motori, per capire l'alimentazione dal titolo quando il sito non la indica.
# L'ordine conta: "firefly hybrid" è ibrida prima che benzina.
SIGLE_MOTORE = (
    ("elettrica", ("elettric", "electric", " ev ", "e tech electric")),
    ("ibrida", ("hybrid", "ibrid", "phev", "mhev")),
    ("gpl", ("gpl", "lpg", "easypower", "bi fuel", "bifuel")),
    ("metano", ("metano", "cng", " tgi ", "natural power", "ecofuel")),
    ("diesel", ("diesel", " tdi", "multijet", " mjt", " jtd", " hdi", "bluehdi", " crdi", " dci", " cdi",
                "d4d", "ecoblue", "tdci", " cdti")),
    ("benzina", ("benzina", " tsi", " tfsi", "firefly", "twinair", " fire ", " tce", "puretech", " vti",
                 " t jet", "tjet", "ecoboost", " mpi")),
)


def carburante_da_titolo(titolo: str) -> str:
    testo = f" {normalizza(titolo)} "
    for nome, sigle in SIGLE_MOTORE:
        if any(s in testo for s in sigle):
            return nome
    return ""


def _carburante_ok(annuncio: Annuncio, voluto: str) -> bool:
    testo = normalizza(annuncio.carburante) or carburante_da_titolo(annuncio.titolo)
    if not testo:
        return True
    if voluto != "ibrida" and _contiene(testo, PAROLE_CARBURANTE["ibrida"]):
        return False
    return _contiene(testo, PAROLE_CARBURANTE.get(voluto, (voluto,)))


def _cambio_ok(annuncio: Annuncio, voluto: str) -> bool:
    testo = normalizza(annuncio.cambio)
    if not testo:
        return True
    return _contiene(testo, PAROLE_CAMBIO.get(voluto, (voluto,)))


def _nome_ok(annuncio: Annuncio, nome: str | None) -> bool:
    if not nome or not annuncio.titolo:
        return True
    titolo = normalizza(annuncio.titolo)
    nome = normalizza(nome)
    if nome == "volkswagen" and " vw " in f" {titolo} ":
        return True
    # "Classe A" deve trovare "Mercedes-Benz A 180 Classe A", "Serie 3" deve trovare "BMW 320d Serie 3"
    return f" {nome} " in f" {titolo} " or nome.replace(" ", "") in titolo.replace(" ", "")


def corrisponde(annuncio: Annuncio, r: dict) -> bool:
    p = annuncio.prezzo
    if p is not None:
        if r.get("prezzo_min") and p < r["prezzo_min"]:
            return False
        if r.get("prezzo_max") and p > r["prezzo_max"]:
            return False
    if annuncio.anno is not None:
        if r.get("anno_min") and annuncio.anno < r["anno_min"]:
            return False
        if r.get("anno_max") and annuncio.anno > r["anno_max"]:
            return False
    if annuncio.km is not None and r.get("km_max") and annuncio.km > r["km_max"]:
        return False
    if r.get("alimentazione") and not _carburante_ok(annuncio, r["alimentazione"]):
        return False
    if r.get("cambio") and not _cambio_ok(annuncio, r["cambio"]):
        return False
    # Molti privati scrivono solo il modello ("Golf 7 2.0 TDI"): se c'è il modello basta quello
    if r.get("modello"):
        return _nome_ok(annuncio, r["modello"])
    return _nome_ok(annuncio, r.get("marca"))
