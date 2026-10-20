"""Controllo giornaliero: cerca, confronta con i giorni precedenti, avvisa.

Uso:
  python -m radar               esegue se è l'orario giusto e oggi non ha già girato
  python -m radar --forza       esegue subito
  python -m radar --prova       esegue subito, stampa i risultati, non invia e non salva
  python -m radar --prova --fonte subito   prova un solo sito
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from . import notifiche
from .estrai import estrai_annunci
from .filtri import corrisponde
from .modelli import Annuncio
from .rete import ErroreRete, pausa, scarica
from .siti import SITI, nome_sito, url_ricerca
from .stato import Stato

RADICE = Path(__file__).resolve().parent.parent


def carica_config(percorso: Path) -> dict:
    cfg = json.loads(percorso.read_text(encoding="utf-8"))
    notif = cfg.setdefault("notifiche", {})
    # I Secrets del repository hanno la precedenza sul file, così email e canale restano privati
    if os.environ.get("EMAIL_TO"):
        notif["email"] = os.environ["EMAIL_TO"]
    if os.environ.get("NTFY_TOPIC"):
        notif["ntfy_topic"] = os.environ["NTFY_TOPIC"]
    notif.setdefault("solo_nuovi", True)
    cfg.setdefault("fuso_orario", "Europe/Rome")
    cfg.setdefault("orario", "11:30")
    return cfg


def e_ora(cfg: dict, stato: Stato, adesso: datetime) -> tuple[bool, str]:
    if stato.ultima_esecuzione == adesso.date().isoformat():
        return False, "controllo di oggi già fatto"
    ore, minuti = (int(x) for x in cfg["orario"].split(":"))
    if adesso.time() < time(ore, minuti):
        return False, f"troppo presto: il controllo è alle {cfg['orario']}"
    return True, ""


def cerca(cfg: dict, solo_fonte: str | None) -> tuple[list[tuple[dict, list[Annuncio]]], list[str], int]:
    """Restituisce (risultati per ricerca, problemi dei siti, pagine lette)."""
    risultati, problemi, pagine_ok = [], [], 0
    for ricerca in cfg.get("ricerche", []):
        trovati: list[Annuncio] = []
        for fonte in ricerca.get("fonti") or list(SITI):
            if fonte not in SITI or (solo_fonte and fonte != solo_fonte):
                continue
            url = url_ricerca(fonte, ricerca)
            try:
                html = scarica(url)
            except ErroreRete as e:
                problemi.append(f"{nome_sito(fonte)} ({ricerca['nome']}): non raggiungibile, {e}")
                continue
            finally:
                pausa()
            letti = estrai_annunci(html, fonte, url)
            if not letti:
                problemi.append(f"{nome_sito(fonte)} ({ricerca['nome']}): nessun annuncio letto, "
                                "il sito potrebbe aver cambiato formato")
                continue
            pagine_ok += 1
            buoni = [a for a in letti if corrisponde(a, ricerca)]
            print(f"  {nome_sito(fonte):<14} {len(letti):>3} letti, {len(buoni):>3} corrispondono", flush=True)
            trovati.extend(buoni)
        risultati.append((ricerca, trovati))
    return risultati, problemi, pagine_ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="radar")
    ap.add_argument("--forza", action="store_true", help="esegue anche fuori orario")
    ap.add_argument("--prova", action="store_true", help="stampa i risultati senza inviare né salvare")
    ap.add_argument("--fonte", choices=list(SITI), help="controlla un solo sito")
    ap.add_argument("--config", type=Path, default=RADICE / "config" / "ricerche.json")
    ap.add_argument("--stato", type=Path, default=RADICE / "data" / "stato.json")
    args = ap.parse_args(argv)

    cfg = carica_config(args.config)
    stato = Stato(args.stato)
    adesso = datetime.now(ZoneInfo(cfg["fuso_orario"]))
    oggi = adesso.date()

    if not (args.forza or args.prova):
        ok, motivo = e_ora(cfg, stato, adesso)
        if not ok:
            print(f"Nessun controllo: {motivo}.")
            return 0

    print(f"Controllo del {adesso:%d/%m/%Y %H:%M}")
    risultati = []
    tutti, problemi, pagine_ok = cerca(cfg, args.fonte)
    for ricerca, annunci in tutti:
        id_r = ricerca.get("id") or ricerca["nome"]
        da_inviare = stato.nuovi(id_r, annunci, ignora_visti=not cfg["notifiche"]["solo_nuovi"])
        stato.ricorda(id_r, annunci, oggi)
        da_inviare.sort(key=lambda a: a.prezzo or 0)
        risultati.append((ricerca, da_inviare))
        print(f"{ricerca['nome']}: {len(annunci)} corrispondenti, {len(da_inviare)} da segnalare")

    n = notifiche.totale(risultati)
    for p in problemi:
        print(f"  ! {p}")

    if args.prova:
        for ricerca, annunci in risultati:
            for a in annunci:
                print(f"  [{ricerca['nome']}] {a.titolo} | {a.prezzo} € | {a.anno} | {a.km} km | {a.url}")
        return 0

    email = cfg["notifiche"].get("email")
    topic = cfg["notifiche"].get("ntfy_topic")
    if not email and not topic:
        print("Nessun avviso configurato: aggiungi i Secrets EMAIL_TO e/o NTFY_TOPIC")
    if n:
        oggetto = f"Radar Auto: {n} {'nuovo annuncio' if n == 1 else 'nuovi annunci'}"
        if email and "@esempio." not in email:
            if os.environ.get("SMTP_USER") and os.environ.get("SMTP_PASSWORD"):
                testo, html = notifiche.testo_email(risultati, problemi)
                notifiche.invia_email(email, oggetto, testo, html)
                print("Email inviata")  # niente indirizzo: i log di un repository pubblico sono visibili a tutti
            else:
                print("Email non inviata: mancano i secrets SMTP_USER e SMTP_PASSWORD")
        if topic:
            primo = next(a for _, lista in risultati for a in lista)
            notifiche.invia_push(topic, oggetto, notifiche.testo_push(risultati), primo.url)
            print("Notifica push inviata")
    elif pagine_ok == 0 and problemi and topic:
        notifiche.invia_push(topic, "Radar Auto: nessun sito raggiungibile",
                             "Oggi non è stato possibile leggere nessun sito. Controlla il log su GitHub.")

    stato.pulisci(oggi, {r.get("id") or r["nome"] for r in cfg.get("ricerche", [])})
    stato.salva(oggi)

    riepilogo = os.environ.get("GITHUB_STEP_SUMMARY")
    if riepilogo:
        with open(riepilogo, "a", encoding="utf-8") as f:
            f.write(f"### {n} annunci da segnalare\n\n")
            for ricerca, annunci in risultati:
                f.write(f"- **{ricerca['nome']}**: {len(annunci)}\n")
            if problemi:
                f.write("\n**Problemi**\n\n" + "\n".join(f"- {p}" for p in problemi) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
