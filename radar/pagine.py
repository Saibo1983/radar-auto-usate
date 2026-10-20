"""Lettori dedicati per i siti che non mettono gli annunci in dati strutturati.

Ognuno riceve l'HTML della pagina dei risultati e restituisce gli annunci,
oppure None se non riconosce la pagina (il sito potrebbe essere cambiato).
Se un sito cambia l'aspetto delle pagine, è qui che va aggiornato.
"""

from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import urljoin

from .modelli import Annuncio

RE_TAG = re.compile(r"<[^>]+>")
RE_ANNO = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")


def _pulisci(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(RE_TAG.sub(" ", html))).strip()


def _cifre(testo: str | None) -> int | None:
    if not testo:
        return None
    cifre = re.sub(r"\D", "", testo.split(",")[0])
    return int(cifre) if cifre else None


def _primo(regex: str, testo: str, flags: int = re.S) -> str:
    m = re.search(regex, testo, flags)
    return m.group(1) if m else ""


def automoto(html: str, base: str) -> list[Annuncio] | None:
    if "mcard-body" not in html:
        return None
    out = []
    for blocco in html.split('<div class="mcard-body">')[1:]:
        blocco = blocco.split("</li>")[0]
        url = _primo(r'<a class="app-add-search"[^>]*?\shref="([^"]+)"', blocco)
        titolo = _primo(r'<a class="app-add-search"[^>]*?\stitle="([^"]+)"', blocco)
        if not url:
            continue
        griglia = [_pulisci(x) for x in re.findall(r'<div class="mcard-grid-item[^"]*">(.*?)</div>', blocco, re.S)]
        km = next((_cifre(x) for x in griglia if x.lower().endswith("km")), None)
        anno = next((int(x) for x in griglia if RE_ANNO.fullmatch(x)), None)
        out.append(Annuncio(
            fonte="automoto",
            url=urljoin(base, url),
            # "Volkswagen Golf 2.0 tsi GTI del 2023 usata a Boves" -> senza la parte finale
            titolo=re.sub(r" del \d{4} usat[ao] a .*$", "", unescape(titolo)),
            prezzo=_cifre(_pulisci(_primo(r'<div class="mcard-price-value">(.*?)</div>', blocco))),
            anno=anno,
            km=km,
            luogo=_pulisci(_primo(r'<span class="mcard-grid-city"[^>]*>(.*?)</span>', blocco)),
        ))
    return out


def quattroruote(html: str, base: str) -> list[Annuncio] | None:
    if "ad-teaser-wrapper" not in html:
        return None
    out = []
    for blocco in html.split("ad-teaser-wrapper")[1:]:
        url = _primo(r'href="(https://www\.quattroruote\.it/auto-usate/annuncio/[^"?]+)"', blocco)
        if not url:
            continue
        dati = [_pulisci(x) for x in re.findall(r'<span class="data">(.*?)</span>', blocco, re.S)]
        km = _cifre(_primo(r'<span class="km">.*?<span class="data">(.*?)</span>', blocco))
        resto = [d for d in dati if _cifre(d) != km]
        anno = next((int(d) for d in resto if RE_ANNO.fullmatch(d)), None)
        testi = [d for d in resto if not d.isdigit()]
        out.append(Annuncio(
            fonte="quattroruote",
            url=url,
            # ad-marmod = "VOLKSWAGEN Golf 7ª serie": la marca davanti alla versione
            titolo=" ".join(x for x in (_primo(r'ad-marmod="(\S+)', blocco).title(),
                                        _pulisci(_primo(r'<h6 class="[^"]*car-subtitle">(.*?)</h6>', blocco))) if x),
            prezzo=_cifre(_primo(r':ad-price="(\d+)"', blocco)),
            anno=anno,
            km=km,
            carburante=testi[0] if testi else "",
            cambio=testi[1] if len(testi) > 1 else "",
            # "Via Nizza, 147/E 10126 Torino (TO)" -> "Torino (TO)"
            luogo=re.sub(r"^.*\b\d{5}\s+", "", _pulisci(_primo(r'<span class="geo">(.*?)</span>', blocco))),
        ))
    return out


def spoticar(html: str, base: str) -> list[Annuncio] | None:
    if 'id="search-list"' not in html:
        return None
    out = []
    for blocco in html.split('<div class="vehicle-card ')[1:]:
        url = _primo(r'<a[^>]*href="(/trova-veicoli-usati/[^"]+-\d{8,})"[^>]*class="vehicle-card-link"', blocco) \
            or _primo(r'href="(/trova-veicoli-usati/[^"]+-\d{8,})"', blocco)
        if not url:
            continue
        tag = [_pulisci(x) for x in re.findall(r'<span class="tag">(.*?)</span>', blocco, re.S)]
        km = next((_cifre(t) for t in tag if t.lower().endswith("km")), None)
        anno = next((int(RE_ANNO.search(t).group(1)) for t in tag if re.fullmatch(r"\d{2}-\d{4}", t)), None)
        altri = [t for t in tag if not t.lower().endswith("km") and not re.fullmatch(r"\d{2}-\d{4}", t)]
        out.append(Annuncio(
            fonte="spoticar",
            url=urljoin(base, url),
            titolo=_pulisci(_primo(r'<div class="vehicle-card-title">(.*?)</div>', blocco)),
            prezzo=_cifre(_pulisci(_primo(r'<span class="price-value">(.*?)</span>', blocco))),
            anno=anno,
            km=km,
            carburante=altri[0] if altri else "",
            cambio=altri[1] if len(altri) > 1 else "",
            immagine=_primo(r'data-src="([^"]+)"', blocco),
        ))
    return out


# Codici di Autohero, ricavati dalle pagine: le Yaris ibride hanno tutte 1139, le Panda 1138
AUTOHERO_CAMBIO = {1138: "Manuale", 1139: "Automatico"}
AUTOHERO_CARBURANTE = {1039: "Benzina", 1040: "Diesel", 1046: "Ibrida"}


def autohero(html: str, base: str) -> list[Annuncio] | None:
    # Lo stato dell'app è una stringa JSON che contiene a sua volta JSON
    m = re.search(r'window\.__APOLLO_STATE__\s*=\s*("(?:[^"\\]|\\.)*")', html, re.S)
    if not m:
        return None
    radice = json.loads(json.loads(m.group(1))).get("ROOT_QUERY", {})
    out = []
    for chiave, valore in radice.items():
        if not chiave.startswith("searchAd") or not isinstance(valore, dict):
            continue
        for ad in valore.get("data") or []:
            marca, modello = ad.get("manufacturer") or "", ad.get("model") or ""
            prezzo = (ad.get("offerPrice") or {}).get("amountMinorUnits")
            percorso = re.sub(r"[^a-z0-9]+", "-", f"{marca} {modello}".lower()).strip("-")
            out.append(Annuncio(
                fonte="autohero",
                url=f"https://www.autohero.com/it/{percorso}/id/{ad['id']}/",
                titolo=" ".join(x for x in (marca, modello, ad.get("subType"), ad.get("subTypeExtra")) if x),
                prezzo=round(prezzo / 100) if prezzo else None,
                anno=ad.get("firstRegistrationYear") or ad.get("builtYear"),
                km=(ad.get("mileage") or {}).get("distance"),
                carburante=AUTOHERO_CARBURANTE.get(ad.get("fuelType"), ""),
                cambio=AUTOHERO_CAMBIO.get(ad.get("gearType"), ""),
            ))
    return out


LETTORI = {
    "automoto": automoto,
    "quattroruote": quattroruote,
    "spoticar": spoticar,
    "autohero": autohero,
}
