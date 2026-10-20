"""Estrazione degli annunci dalle pagine dei siti.

Quasi tutti i siti di auto inseriscono i risultati nella pagina anche come dati
strutturati: JSON-LD (schema.org) oppure il blocco __NEXT_DATA__ delle app Next.js.
Invece di leggere l'HTML visibile, che cambia spesso, si cercano in quei dati gli
oggetti che hanno l'aspetto di un annuncio: un indirizzo e un prezzo.
"""

from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Iterator
from urllib.parse import urljoin

from .modelli import Annuncio

CHIAVI_URL = ("url", "link", "href", "detailUrl", "detailPageUrl", "permalink", "canonicalUrl", "default")
CHIAVI_PREZZO = ("price", "prezzo", "priceRaw", "priceValue", "formattedPrice", "amount", "rawPrice", "grossPrice",
                 "/price")
CHIAVI_TITOLO = ("title", "titolo", "subject", "name", "headline")
CHIAVI_ANNO = ("firstRegistrationYear", "firstRegistration", "firstRegistrationDate", "registrationDate", "registration",
               "year", "anno", "vehicleModelDate", "productionDate", "dateVehicleFirstRegistered", "/year")
CHIAVI_KM = ("mileage", "mileageInKm", "formattedKm", "distance", "mileageFromOdometer", "km", "kilometri", "chilometraggio",
             "/mileage_scalar", "/mileage", "odometer")
CHIAVI_CARBURANTE = ("fuel", "fuelEmissions", "fuelType", "fuelCategory", "carburante", "alimentazione", "/fuel")
CHIAVI_CAMBIO = ("gear", "shift", "gearbox", "gearType", "transmission", "vehicleTransmission", "cambio", "/gearbox")
CHIAVI_LUOGO = ("city", "town", "location", "addressLocality", "citta", "geo", "town_name")
CHIAVI_IMMAGINE = ("image", "images", "thumbnail", "imageUrl", "picture")
CHIAVI_MARCA = ("make", "brand", "marca", "manufacturer")
CHIAVI_MODELLO = ("model", "modello")

RE_SCRIPT = re.compile(r"<script([^>]*)>(.*?)</script>", re.S | re.I)
RE_ANNO = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")


def blocchi_json(html: str) -> Iterator[Any]:
    """Restituisce i blocchi JSON incorporati nella pagina."""
    for attributi, corpo in RE_SCRIPT.findall(html):
        attr = attributi.lower()
        corpo = corpo.strip()
        if not corpo:
            continue
        if "application/ld+json" in attr or "__next_data__" in attr or "application/json" in attr:
            try:
                yield json.loads(unescape(corpo) if corpo.startswith("&") else corpo)
            except ValueError:
                continue
        elif "window.__" in corpo:
            # es. window.__INITIAL_STATE__ = {...};
            m = re.search(r"window\.__[A-Z_]+__\s*=\s*(\{.*\})\s*;?\s*$", corpo, re.S)
            if m:
                try:
                    yield json.loads(m.group(1))
                except ValueError:
                    continue


def _appiattisci_features(obj: dict) -> dict:
    """Subito descrive l'annuncio con features {"/price": {"values": [{"key": "6500"}]}}."""
    feats = obj.get("features")
    if isinstance(feats, dict):
        voci = [dict(v, uri=v.get("uri", k)) for k, v in feats.items() if isinstance(v, dict)]
    elif isinstance(feats, list):
        voci = [v for v in feats if isinstance(v, dict)]
    else:
        return obj
    out = dict(obj)
    for f in voci:
        valori = f.get("values") or []
        if isinstance(f.get("uri"), str) and valori and isinstance(valori[0], dict):
            out.setdefault(f["uri"], valori[0].get("value") or valori[0].get("key"))
    return out


def _cerca(obj: Any, chiavi: tuple[str, ...], profondita: int = 3) -> Any:
    """Primo valore non vuoto per una delle chiavi, scendendo solo nei dizionari."""
    if not isinstance(obj, dict) or profondita < 0:
        return None
    for k in chiavi:
        if k in obj and obj[k] not in (None, "", [], {}):
            return obj[k]
    for v in obj.values():
        if isinstance(v, dict):
            trovato = _cerca(v, chiavi, profondita - 1)
            if trovato not in (None, "", [], {}):
                return trovato
    return None


def numero(valore: Any) -> int | None:
    """Converte "€ 12.900,-", "120.000 km", 12900.0 o {"value": 12900} in intero."""
    if isinstance(valore, bool) or valore is None:
        return None
    if isinstance(valore, (int, float)):
        return int(valore)
    if isinstance(valore, dict):
        return numero(_cerca(valore, ("value", "amount", "raw", "price", "priceRaw", "priceFormatted", "formatted", "key"), 1))
    if isinstance(valore, list):
        return numero(valore[0]) if valore else None
    testo = str(valore).split(",")[0]
    cifre = re.sub(r"[^\d]", "", testo)
    return int(cifre) if cifre else None


def _anno(valore: Any) -> int | None:
    if isinstance(valore, (int, float)) and 1950 <= valore <= 2049:
        return int(valore)
    if isinstance(valore, dict):
        valore = _cerca(valore, ("value", "year", "key"), 1)
    m = RE_ANNO.search(str(valore or ""))
    return int(m.group(1)) if m else None


def _testo(valore: Any, profondita: int = 3) -> str:
    if profondita < 0:
        return ""
    if isinstance(valore, dict):
        # "town" prima di "label": Subito ha geo = {"label": "Comune", "town": {"value": "Firenze"}}
        valore = _cerca(valore, ("name", "value", "formatted", "town", "city", "addressLocality", "label", "key"), 0)
        return _testo(valore, profondita - 1)
    if isinstance(valore, list):
        return _testo(valore[0], profondita - 1) if valore else ""
    return str(valore).strip() if valore not in (None, "") else ""


def _url(obj: dict, base: str) -> str:
    valore = _cerca(obj, CHIAVI_URL, 2)
    if isinstance(valore, dict):
        valore = _cerca(valore, CHIAVI_URL, 1)
    if not isinstance(valore, str):
        return ""
    valore = valore.strip()
    if not valore or valore.startswith(("#", "javascript:", "data:")):
        return ""
    if not (valore.startswith("/") or valore.startswith("http")):
        return ""
    return urljoin(base, valore)


TIPI_PAGINA = {"WebPage", "WebSite", "CollectionPage", "SearchResultsPage", "ItemList", "BreadcrumbList",
               "Organization", "AutoDealer", "AggregateOffer"}


def a_annuncio(obj: dict, fonte: str, base: str) -> Annuncio | None:
    """Trasforma un oggetto JSON in Annuncio se ne ha l'aspetto."""
    tipo = obj.get("@type")
    if tipo in TIPI_PAGINA or (isinstance(obj.get("offers"), dict) and obj["offers"].get("@type") == "AggregateOffer"):
        return None
    obj = _appiattisci_features(obj)
    url = _url(obj, base)
    if not url or url.rstrip("/") == base.rstrip("/"):
        return None
    prezzo = numero(_cerca(obj, CHIAVI_PREZZO) or _cerca(obj, ("offers",)))
    if prezzo is None or not 300 <= prezzo <= 2_000_000:
        return None

    titolo = _testo(_cerca(obj, CHIAVI_TITOLO, 1))
    marca = _testo(_cerca(obj, CHIAVI_MARCA, 2))
    modello = _testo(_cerca(obj, CHIAVI_MODELLO, 2))
    if marca and modello and modello.lower() not in titolo.lower():
        titolo = f"{marca} {modello} {titolo}".strip()

    km = numero(_cerca(obj, CHIAVI_KM))
    if km is not None and km > 2_000_000:
        km = None

    immagine = _cerca(obj, CHIAVI_IMMAGINE, 1)
    if isinstance(immagine, list):
        immagine = immagine[0] if immagine else ""
    if isinstance(immagine, dict):
        immagine = _cerca(immagine, ("url", "src", "contentUrl", "base"), 1) or ""

    return Annuncio(
        fonte=fonte,
        url=url,
        titolo=titolo,
        prezzo=prezzo,
        anno=_anno(_cerca(obj, CHIAVI_ANNO)),
        km=km,
        carburante=_testo(_cerca(obj, CHIAVI_CARBURANTE)),
        cambio=_testo(_cerca(obj, CHIAVI_CAMBIO)),
        luogo=_testo(_cerca(obj, CHIAVI_LUOGO)),
        immagine=immagine if isinstance(immagine, str) else "",
    )


def _visita(nodo: Any, fonte: str, base: str, out: list[Annuncio]) -> None:
    if isinstance(nodo, list):
        for x in nodo:
            _visita(x, fonte, base, out)
    elif isinstance(nodo, dict):
        annuncio = a_annuncio(nodo, fonte, base)
        if annuncio:
            out.append(annuncio)
            return
        for v in nodo.values():
            _visita(v, fonte, base, out)


def estrai_annunci(html: str, fonte: str, base: str) -> list[Annuncio]:
    from .pagine import LETTORI  # lettori dedicati per i siti che non usano dati strutturati

    if fonte in LETTORI:
        trovati = LETTORI[fonte](html, base)
    else:
        trovati = []
        for blocco in blocchi_json(html):
            _visita(blocco, fonte, base, trovati)
    unici: dict[str, Annuncio] = {}
    for a in trovati:
        # A parità di indirizzo tieni la versione con più dati
        precedente = unici.get(a.url)
        if not precedente or _completezza(a) > _completezza(precedente):
            unici[a.url] = a
    return list(unici.values())


def _completezza(a: Annuncio) -> int:
    return sum(bool(x) for x in (a.titolo, a.prezzo, a.anno, a.km, a.carburante, a.cambio, a.luogo))
