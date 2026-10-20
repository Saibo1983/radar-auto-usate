"""Indirizzi di ricerca per ogni sito.

Le stesse regole dell'artefatto Radar Auto Usate: dove il sito accetta i filtri
nell'indirizzo li passiamo, altrimenti li applica radar/filtri.py dopo.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from .modelli import slug

AS_FUEL = {"benzina": "B", "diesel": "D", "ibrida": "2", "elettrica": "E", "gpl": "L", "metano": "C"}
AS_GEAR = {"manuale": "M", "automatico": "A"}
AS_BODY = {"utilitaria": "1", "cabrio": "2", "coupe": "3", "suv": "4", "sw": "5",
           "berlina": "6", "monovolume": "12", "furgone": "13"}
AS_SELLER = {"privato": "P", "concessionario": "D"}


def _marca_sito(marca: str | None, sito: str) -> str:
    if (marca or "").lower() == "volkswagen":
        return "VW" if sito == "autouncle" else "vw"
    return marca or ""


def url_autoscout24(r: dict) -> str:
    path = "https://www.autoscout24.it/lst"
    if r.get("marca"):
        path += "/" + slug(r["marca"])
        if r.get("modello"):
            path += "/" + slug(r["modello"])
    p = {"atype": "C", "cy": "I", "damaged_listing": "exclude", "sort": "age", "desc": "1", "ustate": "N,U"}
    if r.get("prezzo_min"):
        p["pricefrom"] = r["prezzo_min"]
    if r.get("prezzo_max"):
        p["priceto"] = r["prezzo_max"]
    if r.get("anno_min"):
        p["fregfrom"] = r["anno_min"]
    if r.get("anno_max"):
        p["fregto"] = r["anno_max"]
    if r.get("km_max"):
        p["kmto"] = r["km_max"]
    if r.get("potenza_min_cv"):
        p["powerfrom"] = round(r["potenza_min_cv"] * 0.7355)
        p["powertype"] = "kw"
    for chiave, mappa, param in (("alimentazione", AS_FUEL, "fuel"), ("cambio", AS_GEAR, "gear"),
                                 ("carrozzeria", AS_BODY, "body"), ("venditore", AS_SELLER, "custtype")):
        if r.get(chiave) in mappa:
            p[param] = mappa[r[chiave]]
    cap = str(r.get("cap") or "")
    if len(cap) == 5 and cap.isdigit():
        p["zip"] = cap
        if r.get("raggio_km"):
            p["zipr"] = r["raggio_km"]
    return path + "?" + urlencode(p)


def url_subito(r: dict) -> str:
    area = r.get("regione") or "italia"
    p = {}
    q = " ".join(x for x in (r.get("marca"), r.get("modello")) if x)
    if q:
        p["q"] = q
    if r.get("prezzo_min"):
        p["ps"] = r["prezzo_min"]
    if r.get("prezzo_max"):
        p["pe"] = r["prezzo_max"]
    p["order"] = "datedesc"
    return f"https://www.subito.it/annunci-{area}/vendita/auto/?" + urlencode(p)


def url_automobile(r: dict) -> str:
    parti = [x for x in (slug(_marca_sito(r.get("marca"), "automobile")), slug(r.get("modello"))) if x]
    return "https://www.automobile.it/" + ("-".join(parti) if parti else "auto-usate")


def url_mobilede(r: dict) -> str:
    # Marca e modello su mobile.de sono codici numerici: li filtra radar/filtri.py
    ft = {"benzina": "PETROL", "diesel": "DIESEL", "ibrida": "HYBRID", "elettrica": "ELECTRICITY",
          "gpl": "LPG", "metano": "CNG"}
    tr = {"manuale": "MANUAL_GEAR", "automatico": "AUTOMATIC_GEAR"}
    p = {"isSearchRequest": "true", "s": "Car", "vc": "Car", "dam": "false", "sb": "doc", "od": "down"}
    if r.get("prezzo_min") or r.get("prezzo_max"):
        p["p"] = f"{r.get('prezzo_min') or ''}:{r.get('prezzo_max') or ''}"
    if r.get("anno_min") or r.get("anno_max"):
        p["fr"] = f"{r.get('anno_min') or ''}:{r.get('anno_max') or ''}"
    if r.get("km_max"):
        p["ml"] = f":{r['km_max']}"
    if r.get("alimentazione") in ft:
        p["ft"] = ft[r["alimentazione"]]
    if r.get("cambio") in tr:
        p["tr"] = tr[r["cambio"]]
    return "https://suchen.mobile.de/fahrzeuge/search.html?" + urlencode(p)


def url_autouncle(r: dict) -> str:
    parti = [quote(x) for x in (_marca_sito(r.get("marca"), "autouncle"), r.get("modello") or "") if x]
    return "https://www.autouncle.it/it/auto-usate" + ("/" + "/".join(parti) if parti else "")


def url_quattroruote(r: dict) -> str:
    u = "https://www.quattroruote.it/auto-usate/annunci"
    if r.get("marca"):
        u += "/marca-" + slug(r["marca"])
        if r.get("modello"):
            u += "/modello-" + slug(r["modello"])
    return u


def url_automoto(r: dict) -> str:
    u = "https://www.automoto.it/auto-usate"
    if r.get("marca"):
        u += "/" + slug(r["marca"])
        if r.get("modello"):
            u += "/" + slug(r["modello"])
    return u


def url_autohero(r: dict) -> str:
    return "https://www.autohero.com/it/search/"


def url_spoticar(r: dict) -> str:
    return "https://www.spoticar.it/auto-usate"


SITI = {
    "autoscout24": ("AutoScout24", url_autoscout24),
    "subito": ("Subito", url_subito),
    "automobile": ("Automobile.it", url_automobile),
    "mobilede": ("mobile.de", url_mobilede),
    "autouncle": ("AutoUncle", url_autouncle),
    "quattroruote": ("Quattroruote", url_quattroruote),
    "automoto": ("Automoto", url_automoto),
    "autohero": ("Autohero", url_autohero),
    "spoticar": ("Spoticar", url_spoticar),
}


def nome_sito(fonte: str) -> str:
    return SITI.get(fonte, (fonte, None))[0]


def url_ricerca(fonte: str, ricerca: dict) -> str:
    return SITI[fonte][1](ricerca)
