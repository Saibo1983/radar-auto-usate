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
    [a] = estrai_annunci(html, "altro", "https://esempio.it/cerca")
    assert (a.prezzo, a.km, a.anno, a.carburante) == (21900, 45000, 2020, "Ibrida")


def test_ignora_oggetti_senza_prezzo_o_url():
    dati = {"menu": [{"url": "/chi-siamo", "title": "Chi siamo"}], "banner": {"price": 99}}
    html = pagina(('type="application/ld+json"', dati))
    assert estrai_annunci(html, "x", "https://esempio.it/") is None


def test_lettore_automoto():
    html = '''<li><div class="mcard-body"> <h2 class="mcard-title"> <a class="app-add-search"
      href="/auto-usate/fiat/panda/12-easy/16196795" title="Fiat Panda 1.2 Easy del 2020 usata a Modugno"> x </a></h2>
      <div class="mcard-price-value"> € 10.900 </div>
      <div class="mcard-grid"><div class="mcard-grid-item mcard-grid-item--icon"> <span class="mcard-grid-city" title="Modugno (BA)"> Modugno (BA) </span> </div>
      <div class="mcard-grid-item text-center"> 2020 </div> <div class="mcard-grid-item text-center"> 69.784 Km </div></div></li>'''
    [a] = estrai_annunci(html, "automoto", "https://www.automoto.it/auto-usate/fiat/panda")
    assert (a.titolo, a.prezzo, a.anno, a.km, a.luogo) == ("Fiat Panda 1.2 Easy", 10900, 2020, 69784, "Modugno (BA)")
    assert a.url == "https://www.automoto.it/auto-usate/fiat/panda/12-easy/16196795"


def test_lettore_quattroruote():
    html = '''<div class="ad-teaser-wrapper"> <manage-prefs-widget ad-marmod="VOLKSWAGEN Golf 7ª serie" :ad-price="13900">
      <a href="https://www.quattroruote.it/auto-usate/annuncio/volkswagen-golf-7a-serie-110413264">
      <h6 class="color-secondary car-subtitle"> Golf 7ª serie Golf 1.5 TSI </h6></a>
      <div class="meta-data-ad"> <span class="km"> <span class="capitalize">km:</span> <span class="data">129.000</span> </span>
      <span class="data">2020</span> <span class="data">Benzina</span> <span class="data">Manuale</span> </div>
      <span class="geo"> Via Roma 1 20121 Milano (MI) </span></div>'''
    [a] = estrai_annunci(html, "quattroruote", "https://www.quattroruote.it/")
    assert (a.prezzo, a.anno, a.km, a.carburante, a.cambio, a.luogo) == (13900, 2020, 129000, "Benzina", "Manuale", "Milano (MI)")
    assert a.titolo.startswith("Volkswagen Golf")


def test_lettore_spoticar():
    html = '''<div id="search-list"></div><div class="vehicle-card " data-vo-id="1"> <img data-src="https://img/1.jpg">
      <a href="/trova-veicoli-usati/fiat-panda-10-hybrid-lombardia-milano-1202520834" class="vehicle-card-link">
      <div class="vehicle-card-title"> <h3> Fiat Panda <span class="car-version"> 1.0 Hybrid </span> </h3> </div>
      <span class="tag">58 265 km</span> <span class="tag">Ibrido</span> <span class="tag">01-2024</span> <span class="tag">Manuale</span>
      <span class="price-value"> 10 700 € </span></a></div>'''
    [a] = estrai_annunci(html, "spoticar", "https://www.spoticar.it/trova-veicoli-usati/fiat/panda")
    assert (a.titolo, a.prezzo, a.anno, a.km, a.carburante, a.cambio) == ("Fiat Panda 1.0 Hybrid", 10700, 2024, 58265, "Ibrido", "Manuale")


def test_lettore_autohero():
    stato = {"ROOT_QUERY": {"searchAdV9AdsV2:{}": {"total": 1, "data": [
        {"id": "abc", "manufacturer": "Toyota", "model": "Aygo X", "subType": "1.0",
         "offerPrice": {"amountMinorUnits": 1579900}, "mileage": {"distance": 27987}, "firstRegistrationYear": 2024}]}}}
    html = f"<script>window.__APOLLO_STATE__ = {json.dumps(json.dumps(stato))};</script>"
    [a] = estrai_annunci(html, "autohero", "https://www.autohero.com/it/search/")
    assert (a.titolo, a.prezzo, a.anno, a.km) == ("Toyota Aygo X 1.0", 15799, 2024, 27987)
    assert a.url == "https://www.autohero.com/it/toyota-aygo-x/id/abc/"


def test_pagina_valida_senza_risultati():
    stato = {"ROOT_QUERY": {"searchAdV9AdsV2:{}": {"total": 0, "data": []}}}
    html = f"<script>window.__APOLLO_STATE__ = {json.dumps(json.dumps(stato))};</script>"
    assert estrai_annunci(html, "autohero", "https://www.autohero.com/it/search/") == []
    assert estrai_annunci("<html>pagina diversa</html>", "autohero", "https://www.autohero.com/") is None
