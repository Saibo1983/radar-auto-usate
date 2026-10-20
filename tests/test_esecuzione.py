import json

import radar.__main__ as radar
from radar import notifiche


def test_esecuzione_completa(tmp_path, monkeypatch):
    cfg = {"orario": "11:30", "notifiche": {"email": "io@test.it", "ntfy_topic": "canale-prova"},
           "ricerche": [{"id": "g", "nome": "Golf", "marca": "Volkswagen", "modello": "Golf",
                         "prezzo_max": 15000, "fonti": ["subito", "autoscout24"]}]}
    (tmp_path / "cfg.json").write_text(json.dumps(cfg))
    pagina = {"listings": [
        {"url": "/a/1", "title": "Volkswagen Golf 1.6 TDI", "price": 11000, "mileage": 80000, "year": 2018},
        {"url": "/a/2", "title": "Volkswagen Golf GTI", "price": 25000, "mileage": 40000, "year": 2020},
    ]}
    html = f'<script type="application/json">{json.dumps(pagina)}</script>'
    monkeypatch.setattr(radar, "scarica", lambda url: html)
    monkeypatch.setattr(radar, "pausa", lambda: None)
    email, push = [], []
    monkeypatch.setattr(notifiche, "invia_email", lambda *a: email.append(a))
    monkeypatch.setattr(notifiche, "invia_push", lambda *a: push.append(a))
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")
    monkeypatch.delenv("EMAIL_TO", raising=False)
    monkeypatch.delenv("NTFY_TOPIC", raising=False)
    argomenti = ["--forza", "--config", str(tmp_path / "cfg.json"), "--stato", str(tmp_path / "stato.json")]

    assert radar.main(argomenti) == 0
    # La stessa Golf su due siti conta una volta; la GTI supera il prezzo massimo
    assert len(email) == 1 and email[0][1] == "Radar Auto: 1 nuovo annuncio"
    assert "Volkswagen Golf 1.6 TDI" in email[0][3]
    assert push[0][0] == "canale-prova"

    # Gli annunci della ricerca restano memorizzati per "Vedi annunci" nell'app
    memorizzati = json.loads((tmp_path / "annunci" / "g.json").read_text())
    assert [a["titolo"] for a in memorizzati["ricerche"][0]["annunci"]] == ["Volkswagen Golf 1.6 TDI"]

    # Il giorno dopo la stessa auto non viene segnalata di nuovo
    assert radar.main(argomenti) == 0
    # ma arriva comunque un avviso che dice che non ci sono novità
    assert len(email) == 2 and len(push) == 2
    assert email[1][1] == push[1][1] == "Radar Auto: nessun nuovo annuncio"
    assert "Golf" in push[1][2] and "Golf" in email[1][2]
