import json

from radar.estrai import estrai_annunci, numero


def pagina(*blocchi: tuple[str, object]) -> str:
    script = "".join(f'<script {attr}>{json.dumps(dati)}</script>' for attr, dati in blocchi)
    return f"<html><head>{script}</head><body></body></html>"


def test_numero_formati_italiani():
    assert numero("€ 12.900,-") == 12900
    assert numero("120.000 km") == 120000
    assert numero(8500.0) == 8500
    assert numero({"value": 15000}) == 15000
    assert numero(None) is None


def test_next_data_stile_autoscout():
    dati = {"props": {"pageProps": {"listings": [
        {"id": "a1", "url": "/annunci/volkswagen-golf-1", "price": {"priceFormatted": "€ 12.900,-"},
         "vehicle": {"make": "Volkswagen", "model": "Golf", "mileageInKm": "98.000 km", "fuel": "Diesel"},
         "tracking": {"firstRegistration": "05-2019"}, "location": {"city": "Milano"}},
        {"id": "a2", "url": "/annunci/volkswagen-golf-2", "price": {"priceFormatted": "€ 9.500,-"},
         "vehicle": {"make": "Volkswagen", "model": "Golf", "mileageInKm": "150.000 km", "fuel": "Benzina"},
         "tracking": {"firstRegistration": "01-2015"}},
    ]}}}
    html = pagina(('id="__NEXT_DATA__" type="application/json"', dati))
    annunci = estrai_annunci(html, "autoscout24", "https://www.autoscout24.it/lst/volkswagen/golf")
    assert len(annunci) == 2
    a = annunci[0]
    assert a.url == "https://www.autoscout24.it/annunci/volkswagen-golf-1"
    assert (a.prezzo, a.anno, a.km) == (12900, 2019, 98000)
    assert "Golf" in a.titolo and a.carburante == "Diesel" and a.luogo == "Milano"


def test_features_stile_subito():
    dati = {"props": {"state": {"items": {"list": [{"item": {
        "subject": "Fiat Panda 1.2 Easy", "urls": {"default": "https://www.subito.it/auto/fiat-panda-1.htm"},
        "features": {
            "/price": {"values": [{"key": "6500", "value": "6.500 €"}]},
            "/year": {"values": [{"key": "2017", "value": "2017"}]},
            "/mileage_scalar": {"values": [{"key": "78000", "value": "78.000"}]},
            "/fuel": {"values": [{"key": "1", "value": "Benzina"}]},
        }}}]}}}}
    html = pagina(('id="__NEXT_DATA__" type="application/json"', dati))
    [a] = estrai_annunci(html, "subito", "https://www.subito.it/annunci-italia/vendita/auto/")
    assert (a.titolo, a.prezzo, a.anno, a.km, a.carburante) == ("Fiat Panda 1.2 Easy", 6500, 2017, 78000, "Benzina")


def test_json_ld_schema_org():
    dati = {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
        {"@type": "ListItem", "item": {"@type": "Car", "name": "Toyota C-HR 1.8 Hybrid",
                                       "url": "https://esempio.it/auto/1",
                                       "offers": {"@type": "Offer", "price": "21900", "priceCurrency": "EUR"},
                                       "mileageFromOdometer": {"value": 45000, "unitCode": "KMT"},
                                       "vehicleModelDate": "2020", "fuelType": "Ibrida"}}]}
    html = pagina(('type="application/ld+json"', dati))
    [a] = estrai_annunci(html, "autohero", "https://esempio.it/cerca")
    assert (a.prezzo, a.km, a.anno, a.carburante) == (21900, 45000, 2020, "Ibrida")


def test_ignora_oggetti_senza_prezzo_o_url():
    dati = {"menu": [{"url": "/chi-siamo", "title": "Chi siamo"}], "banner": {"price": 99}}
    html = pagina(('type="application/ld+json"', dati))
    assert estrai_annunci(html, "x", "https://esempio.it/") == []
