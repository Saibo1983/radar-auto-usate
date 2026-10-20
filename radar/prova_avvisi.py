"""Invia un'email e una notifica push di prova, per controllare i Secrets.

Non legge i siti e non tocca gli annunci già visti. Esce con errore se un
avviso non parte, così su GitHub il controllo risulta rosso.

Uso: python -m radar.prova_avvisi
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from . import notifiche
from .__main__ import RADICE, carica_config

APP = notifiche.APP


def main() -> int:
    cfg = carica_config(RADICE / "config" / "ricerche.json")
    email = cfg["notifiche"].get("email")
    topic = cfg["notifiche"].get("ntfy_topic")
    ora = datetime.now(ZoneInfo(cfg["fuso_orario"]))
    oggetto = "Radar Auto: prova degli avvisi"
    messaggio = f"Se leggi questo messaggio gli avvisi funzionano ({ora:%d/%m/%Y %H:%M})."
    errori = []

    # Niente indirizzi o nomi del canale nei messaggi: i log di un repository pubblico sono visibili a tutti
    if not email:
        errori.append("Email: manca il secret EMAIL_TO")
    elif not (os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD")):
        errori.append("Email: mancano i secrets SMTP_USER e SMTP_PASSWORD")
    else:
        try:
            notifiche.invia_email(email, oggetto, messaggio, f"<p>{messaggio}</p>")
            print("Email inviata")
        except Exception as e:
            errori.append(f"Email non inviata: {type(e).__name__}: {e}")

    if not topic:
        errori.append("Push: manca il secret NTFY_TOPIC")
    else:
        try:
            notifiche.invia_push(topic, oggetto, messaggio, APP)
            print("Notifica push inviata")
        except Exception as e:
            errori.append(f"Push non inviata: {type(e).__name__}: {e}")

    for e in errori:
        print(f"! {e}")
    return 1 if errori else 0


if __name__ == "__main__":
    sys.exit(main())
