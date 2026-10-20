import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from radar.__main__ import e_ora
from radar.filtri import corrisponde
from radar.modelli import Annuncio
from radar.siti import SITI, url_autoscout24, url_ricerca
from radar.stato import Stato

GOLF = {"id": "g", "nome": "Golf", "marca": "Volkswagen", "modello": "Golf", "alimentazione": "diesel",
        "prezzo_max": 15000, "anno_min": 2018, "km_max": 120000}


def auto(**kw) -> Annuncio:
    base = dict(fonte="subito", url="https://x/1", titolo="Volkswagen Golf 2.0 TDI", prezzo=12000,
                anno=2019, km=90000, carburante="Diesel")
    base.update(kw)
    return Annuncio(**base)


def test_filtri():
    assert corrisponde(auto(), GOLF)
    assert corrisponde(auto(titolo="Golf 7 2.0 tdi highline"), GOLF)  # privato senza marca nel titolo
    assert corrisponde(auto(titolo="VW Golf Variant"), GOLF)
    assert not corrisponde(auto(prezzo=16000), GOLF)
    assert not corrisponde(auto(anno=2016), GOLF)
    assert not corrisponde(auto(km=130000), GOLF)
    assert not corrisponde(auto(carburante="Benzina"), GOLF)
    assert not corrisponde(auto(carburante="Ibrida diesel"), GOLF)
    assert not corrisponde(auto(titolo="Volkswagen Polo 1.6 TDI"), GOLF)
    assert corrisponde(auto(km=None, anno=None, carburante=""), GOLF)  # dati mancanti non escludono
    assert not corrisponde(auto(titolo="Volkswagen Golf 8 sinistrata"), GOLF)


def test_url_autoscout_con_filtri():
    u = url_autoscout24({**GOLF, "cap": "20121", "raggio_km": 50, "cambio": "automatico"})
    assert u.startswith("https://www.autoscout24.it/lst/volkswagen/golf?")
    for pezzo in ("priceto=15000", "fregfrom=2018", "kmto=120000", "fuel=D", "gear=A", "zip=20121", "zipr=50"):
        assert pezzo in u


def test_tutti_i_siti_hanno_un_url():
    for fonte in SITI:
        assert url_ricerca(fonte, GOLF).startswith("https://")


def test_stato_nuovi_e_doppioni(tmp_path):
    s = Stato(tmp_path / "stato.json")
    a1 = auto(url="https://a/1")
    a1_altro_sito = auto(url="https://b/9", fonte="autoscout24", km=90300)  # stessa auto su un altro sito
    a2 = auto(url="https://a/2", prezzo=9000)
    assert s.nuovi("g", [a1, a1_altro_sito, a2]) == [a1, a2]
    s.ricorda("g", [a1, a1_altro_sito, a2], date(2026, 10, 20))
    s.salva(date(2026, 10, 20))

    s2 = Stato(tmp_path / "stato.json")
    a3 = auto(url="https://a/3", prezzo=11000)
    assert s2.nuovi("g", [a1, a2, a3]) == [a3]
    assert len(s2.nuovi("g", [a1, a2, a3], ignora_visti=True)) == 3


def test_pulizia_vecchi(tmp_path):
    s = Stato(tmp_path / "stato.json")
    s.ricorda("g", [auto()], date(2026, 1, 1))
    s.ricorda("vecchia", [auto()], date(2026, 10, 1))
    s.pulisci(date(2026, 10, 20), {"g"})
    assert s.dati["visti"] == {"g": {"url": {}, "auto": {}}}


def test_orario(tmp_path):
    cfg = {"orario": "11:30"}
    s = Stato(tmp_path / "stato.json")
    roma = ZoneInfo("Europe/Rome")
    assert not e_ora(cfg, s, datetime(2026, 10, 20, 10, 30, tzinfo=roma))[0]
    assert e_ora(cfg, s, datetime(2026, 10, 20, 11, 31, tzinfo=roma))[0]
    s.salva(date(2026, 10, 20))
    assert not e_ora(cfg, s, datetime(2026, 10, 20, 12, 30, tzinfo=roma))[0]


def test_carburante_dal_titolo():
    golf = {"modello": "Golf", "alimentazione": "diesel"}
    assert corrisponde(auto(carburante="", titolo="Volkswagen Golf 1.6 TDI Business"), golf)
    assert not corrisponde(auto(carburante="", titolo="Volkswagen Golf 1.5 TSI Life"), golf)
    assert not corrisponde(auto(carburante="", titolo="Fiat Panda 1.0 FireFly Hybrid"), {"alimentazione": "benzina"})


def test_furgoni():
    from radar.siti import fonti_per, url_subito

    ducato = {"marca": "Fiat", "modello": "Ducato", "tipo": "furgone", "prezzo_max": 20000}
    assert fonti_per(ducato) == ["autoscout24", "subito"]
    assert fonti_per({**ducato, "fonti": ["subito", "spoticar"]}) == ["subito"]
    assert "atype=X" in url_autoscout24(ducato)
    assert "/vendita/veicoli-commerciali/" in url_subito(ducato)
    assert "atype=C" in url_autoscout24(GOLF) and len(fonti_per(GOLF)) == 7


def test_ricerca_adesso_accetta_solo_campi_noti():
    from radar.adesso import pulisci

    r = pulisci({"marca": "Fiat", "prezzo_max": 9000, "anno_min": "2018", "fonti": ["subito", "x"],
                 "tipo": "astronave", "comando": "rm -rf /"})
    assert r == {"marca": "Fiat", "prezzo_max": 9000, "fonti": ["subito"], "tipo": "auto", "nome": "Fiat"}


def test_salva_ricerche_dall_app(tmp_path):
    from radar.salva_ricerche import aggiorna

    percorso = tmp_path / "ricerche.json"
    percorso.write_text(json.dumps({"orario": "11:55", "notifiche": {"solo_nuovi": True}, "ricerche": []}))
    annunci = tmp_path / "annunci"
    annunci.mkdir()
    (annunci / "r1.json").write_text("{}")
    (annunci / "vecchia.json").write_text("{}")
    aggiorna(percorso, [
        {"id": "r1", "attiva": True, "marca": "Fiat", "modello": "Panda", "prezzo_max": 8000, "fonti": ["subito"]},
        {"id": "../x", "attiva": False, "nome": "Pausa", "comando": "rm -rf /"},
        "non una ricerca",
    ], annunci)
    cfg = json.loads(percorso.read_text())
    assert cfg["orario"] == "11:55" and cfg["notifiche"] == {"solo_nuovi": True}
    assert cfg["ricerche"][0] == {"id": "r1", "attiva": True, "nome": "Fiat Panda", "marca": "Fiat",
                                  "modello": "Panda", "tipo": "auto", "prezzo_max": 8000, "fonti": ["subito"]}
    assert cfg["ricerche"][1]["id"] == "r2" and cfg["ricerche"][1]["attiva"] is False
    assert len(cfg["ricerche"]) == 2
    assert sorted(f.name for f in annunci.iterdir()) == ["r1.json"]


def test_ricerca_in_pausa_non_viene_cercata(monkeypatch):
    import radar.__main__ as radar

    monkeypatch.setattr(radar, "scarica", lambda url: "")
    monkeypatch.setattr(radar, "pausa", lambda: None)
    tutti, _, _ = radar.cerca({"ricerche": [{**GOLF, "attiva": False, "fonti": ["subito"]}]}, None)
    assert tutti == []


def test_ricerca_adesso_di_una_ricerca_salvata_resta_memorizzata(tmp_path, monkeypatch):
    import radar.adesso as adesso

    monkeypatch.setattr(adesso, "RADICE", tmp_path)
    monkeypatch.setattr(adesso, "cerca", lambda cfg, fonte: ([(cfg["ricerche"][0], [])], [], 1))
    adesso.cerca.righe = []
    monkeypatch.setenv("RICERCA", json.dumps({"marca": "Fiat", "modello": "Panda"}))
    assert adesso.main(["abc", "r1"]) == 0
    d = json.loads((tmp_path / "data" / "annunci" / "r1.json").read_text())
    assert d["richiesta"] == "abc" and d["ricerche"][0]["id"] == "r1"
    assert not (tmp_path / "data" / "ricerca-adesso.json").exists()

    assert adesso.main(["def", "../x"]) == 0  # id non valido: ricerca dal modulo
    assert json.loads((tmp_path / "data" / "ricerca-adesso.json").read_text())["richiesta"] == "def"


def test_cambio_automatico_senza_indicazioni_serve_il_titolo():
    panda = {"marca": "Fiat", "modello": "Panda", "cambio": "automatico"}
    assert not corrisponde(Annuncio(fonte="automoto", url="u", titolo="Fiat Panda 1.2 Easy"), panda)
    assert corrisponde(Annuncio(fonte="automoto", url="u", titolo="Fiat Panda 1.2 Dualogic Lounge"), panda)
    assert corrisponde(Annuncio(fonte="subito", url="u", titolo="Fiat Panda", cambio="Automatico"), panda)
    assert not corrisponde(Annuncio(fonte="autohero", url="u", titolo="Fiat Panda", cambio="Manuale"), panda)
    # Per il manuale un annuncio senza indicazioni resta valido
    assert corrisponde(Annuncio(fonte="automoto", url="u", titolo="Fiat Panda 1.2 Easy"), {**panda, "cambio": "manuale"})
