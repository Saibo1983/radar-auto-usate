"""Invio di email e notifiche push (ntfy)."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage
from html import escape

from .modelli import Annuncio
from .siti import nome_sito

MAX_PER_RICERCA = 30
APP = "https://saibo1983.github.io/radar-auto-usate/"


def _euro(n: int | None) -> str:
    return f"€ {n:,}".replace(",", ".") if n else "prezzo n.d."


def _dettagli(a: Annuncio) -> str:
    parti = [str(a.anno) if a.anno else "", f"{a.km:,} km".replace(",", ".") if a.km is not None else "",
             a.carburante, a.cambio, a.luogo]
    return " · ".join(p for p in parti if p)


def totale(risultati: list[tuple[dict, list[Annuncio]]]) -> int:
    return sum(len(a) for _, a in risultati)


def testo_email(risultati, avvisi_siti: list[str]) -> tuple[str, str]:
    """Restituisce (testo semplice, html)."""
    righe, html = [], [
        '<div style="font-family:Arial,sans-serif;max-width:680px;color:#16202c">',
        f'<h2 style="margin:0 0 4px">{totale(risultati)} nuovi annunci</h2>',
    ]
    for ricerca, annunci in risultati:
        if not annunci:
            continue
        righe.append(f"\n== {ricerca['nome']} ({len(annunci)}) ==")
        html.append(f'<h3 style="margin:24px 0 8px;border-bottom:2px solid #1d3f9e">'
                    f'{escape(ricerca["nome"])} <span style="color:#5b6676">({len(annunci)})</span></h3>')
        for a in annunci[:MAX_PER_RICERCA]:
            righe.append(f"- {a.titolo or 'Annuncio'} | {_euro(a.prezzo)} | {_dettagli(a)} | "
                         f"{nome_sito(a.fonte)}\n  {a.url}")
            html.append(
                '<table role="presentation" style="width:100%;border-collapse:collapse;margin:0 0 10px"><tr>'
                + (f'<td style="width:110px;padding-right:10px;vertical-align:top"><img src="{escape(a.immagine)}" '
                   'width="110" style="border-radius:4px;display:block" alt=""></td>' if a.immagine else "")
                + f'<td style="vertical-align:top"><a href="{escape(a.url)}" style="color:#1d3f9e;font-weight:bold">'
                f'{escape(a.titolo or "Annuncio")}</a><br>'
                f'<strong>{_euro(a.prezzo)}</strong> <span style="color:#5b6676">{escape(_dettagli(a))}</span><br>'
                f'<span style="font-size:12px;color:#5b6676">{escape(nome_sito(a.fonte))}</span></td></tr></table>'
            )
        if len(annunci) > MAX_PER_RICERCA:
            altri = len(annunci) - MAX_PER_RICERCA
            righe.append(f"... e altri {altri}")
            html.append(f'<p style="color:#5b6676">e altri {altri} annunci</p>')
    if avvisi_siti:
        righe.append("\nProblemi con alcuni siti:\n" + "\n".join(f"- {x}" for x in avvisi_siti))
        html.append('<p style="margin-top:24px;font-size:12px;color:#5b6676"><strong>Problemi con alcuni siti</strong><br>'
                    + "<br>".join(escape(x) for x in avvisi_siti) + "</p>")
    html.append("</div>")
    return "\n".join(righe).strip(), "".join(html)


def testo_nessuno(risultati, avvisi_siti: list[str], messaggio: str) -> tuple[str, str]:
    """Email del controllo senza annunci nuovi: (testo semplice, html)."""
    righe = [messaggio, "", "Ricerche controllate:"] + [f"- {r['nome']}" for r, _ in risultati]
    html = ['<div style="font-family:Arial,sans-serif;max-width:680px;color:#16202c">',
            f'<p style="font-size:16px">{escape(messaggio)}</p>',
            '<p style="margin-bottom:4px">Ricerche controllate:</p><ul style="margin-top:0">',
            *(f"<li>{escape(r['nome'])}</li>" for r, _ in risultati), "</ul>"]
    if avvisi_siti:
        righe.append("\nProblemi con alcuni siti:\n" + "\n".join(f"- {x}" for x in avvisi_siti))
        html.append('<p style="font-size:12px;color:#5b6676"><strong>Problemi con alcuni siti</strong><br>'
                    + "<br>".join(escape(x) for x in avvisi_siti) + "</p>")
    righe.append(f"\nApri l'app: {APP}")
    html.append(f'<p><a href="{APP}" style="color:#1d3f9e">Apri l\'app</a></p></div>')
    return "\n".join(righe), "".join(html)


def invia_email(destinatario: str, oggetto: str, testo: str, html: str) -> None:
    host = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
    porta = int(os.environ.get("SMTP_PORT") or 465)
    utente = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = oggetto
    msg["From"] = os.environ.get("EMAIL_FROM") or utente
    msg["To"] = destinatario
    msg.set_content(testo)
    msg.add_alternative(html, subtype="html")

    contesto = ssl.create_default_context()
    if porta == 465:
        with smtplib.SMTP_SSL(host, porta, context=contesto, timeout=30) as s:
            s.login(utente, password)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, porta, timeout=30) as s:
            s.starttls(context=contesto)
            s.login(utente, password)
            s.send_message(msg)


def invia_push(topic: str, titolo: str, messaggio: str, link: str | None = None) -> None:
    server = (os.environ.get("NTFY_SERVER") or "https://ntfy.sh").rstrip("/")
    corpo = {"topic": topic, "title": titolo, "message": messaggio, "tags": ["red_car"]}
    if link:
        corpo["click"] = link
    richiesta = urllib.request.Request(server, data=json.dumps(corpo).encode(), method="POST",
                                       headers={"Content-Type": "application/json"})
    token = os.environ.get("NTFY_TOKEN")
    if token:
        richiesta.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(richiesta, timeout=30) as r:
        r.read()


def testo_push(risultati) -> str:
    parti = [f"{len(a)} · {r['nome']}" for r, a in risultati if a]
    return "\n".join(parti)
