"""Download delle pagine, con l'aspetto di un browser normale e senza fretta."""

from __future__ import annotations

import random
import time

INTESTAZIONI = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.7",
}

try:
    # curl_cffi imita anche l'impronta TLS di Chrome: alcuni siti bloccano le librerie standard
    from curl_cffi import requests as _http

    def _get(url: str, timeout: int):
        return _http.get(url, headers=INTESTAZIONI, timeout=timeout, impersonate="chrome")
except ImportError:  # pragma: no cover - ripiego se curl_cffi non è installato
    import requests as _http

    def _get(url: str, timeout: int):
        return _http.get(url, headers=INTESTAZIONI, timeout=timeout)


class ErroreRete(Exception):
    pass


def scarica(url: str, tentativi: int = 3, timeout: int = 30) -> str:
    ultimo = ""
    for i in range(tentativi):
        if i:
            time.sleep(2 ** i + random.random())
        try:
            r = _get(url, timeout)
        except Exception as e:  # noqa: BLE001 - qualsiasi errore di rete va ritentato
            ultimo = str(e)
            continue
        if r.status_code == 200:
            return r.text
        ultimo = f"HTTP {r.status_code}"
        if r.status_code in (403, 404, 410):
            break
    raise ErroreRete(ultimo)


def pausa() -> None:
    """Qualche secondo tra una richiesta e l'altra, per non pesare sui siti."""
    time.sleep(random.uniform(2, 5))
