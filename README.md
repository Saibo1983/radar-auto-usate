# Radar Auto Usate

Ogni giorno alle 11:30 (ora italiana) cerca auto usate su 9 siti e, se trova annunci nuovi, ti manda una email e una notifica push sul telefono.

**Siti controllati:** AutoScout24, Subito.it, Automobile.it, Quattroruote, Automoto.it, Autohero, Spoticar.

| Sito | Filtri applicati dal sito | Note |
|---|---|---|
| AutoScout24 | tutti | ordinati dai più recenti |
| Subito.it | marca, modello, prezzo, anno, regione | il resto lo filtra lo script |
| Automobile.it | marca e modello | il sito ignora gli altri filtri nell'indirizzo e non ordina per data: si leggono i primi 20 risultati |
| Quattroruote | marca, modello, anno | il resto lo filtra lo script |
| Automoto.it | marca e modello | l'alimentazione si ricava dalla sigla del motore (TDI, TSI…) |
| Autohero | marca e modello | concessionario online |
| Spoticar | marca e modello | usato garantito Stellantis |
| mobile.de, AutoUncle | — | **bloccano le richieste dai server di GitHub (HTTP 403)**: il codice c'è, ma sono esclusi dai siti predefiniti |

Le ricerche si preparano con l'artefatto **Radar Auto Usate** su claude.ai, che genera il file `config/ricerche.json`. Si può anche modificare il file a mano.

## L'app

L'app è su **https://saibo1983.github.io/radar-auto-usate/**. Mostra gli **ultimi risultati** del controllo giornaliero e ha un pulsante **Cerca adesso** che avvia subito una ricerca, per auto o furgoni, e dopo 2-4 minuti mostra i risultati.

Il pulsante la prima volta chiede un codice di GitHub (un *fine-grained personal access token* limitato a questo repository, con permesso **Actions: Read and write**), che resta salvato solo nel browser. La ricerca immediata non invia avvisi e non cambia gli annunci già visti: i risultati vanno in `data/ricerca-adesso.json`.

I **furgoni** (`"tipo": "furgone"`) si cercano su AutoScout24 e Subito; gli altri siti vendono solo auto.

## Come funziona

1. GitHub Actions avvia `python -m radar` ogni giorno (`.github/workflows/radar.yml`).
2. Per ogni ricerca e ogni sito lo script apre la pagina dei risultati ordinata dai più recenti e legge gli annunci dai dati strutturati della pagina (JSON-LD o `__NEXT_DATA__`).
3. Applica i filtri della ricerca: prezzo, anno, km, alimentazione, cambio, marca e modello.
4. Confronta i risultati con `data/stato.json`, che contiene gli annunci già segnalati. La stessa auto pubblicata su più siti viene segnalata una volta sola.
5. Se ci sono annunci nuovi invia l'email e la notifica push, poi salva `data/stato.json` nel repository.

Alla prima esecuzione tutti gli annunci trovati risultano nuovi, quindi la prima email sarà più lunga del solito.

## Configurazione

### 1. Repository pubblico: cosa resta privato

Il repository è pubblico, quindi tutto ciò che è nei file si vede: le ricerche in `config/ricerche.json` e gli annunci già visti in `data/stato.json`. Per questo **email e canale push non vanno mai nei file**, ma solo nei Secrets (punti 2 e 3), che restano privati anche in un repository pubblico. L'artefatto esporta la configurazione già senza questi dati.

Nei repository pubblici GitHub Actions è gratuito senza limiti di minuti. GitHub sospende i workflow pianificati dopo 60 giorni senza attività nel repository: qui non succede, perché ogni controllo salva un commit con `data/stato.json`.

### 2. Email (Gmail)

1. Attiva la verifica in due passaggi sul tuo account Google.
2. Crea una *password per le app* su <https://myaccount.google.com/apppasswords>.
3. Nel repository vai su **Settings → Secrets and variables → Actions → New repository secret** e aggiungi:

| Secret | Valore |
|---|---|
| `SMTP_USER` | il tuo indirizzo Gmail |
| `SMTP_PASSWORD` | la password per le app (16 caratteri) |
| `EMAIL_TO` | l'indirizzo che riceve gli avvisi |

Per un altro provider aggiungi anche `SMTP_HOST` e `SMTP_PORT` (465 per SSL, 587 per STARTTLS).

### 3. Notifiche push (ntfy)

1. Installa l'app **ntfy** ([Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy), [iPhone](https://apps.apple.com/app/ntfy/id1625396347)).
2. Nell'app premi **+** e iscriviti a un canale con un nome difficile da indovinare, per esempio quello proposto dall'artefatto (`radar-auto-xxxxxxxx`).
3. Aggiungi il secret `NTFY_TOPIC` con lo stesso nome.

Chi conosce il nome del canale può leggerne le notifiche: non usare nomi semplici.

### 4. Ricerche

Copia la configurazione dall'artefatto in `config/ricerche.json`. I campi:

| Campo | Valori |
|---|---|
| `orario` | ora del controllo, es. `"11:30"` (vedi sotto per cambiarla) |
| `notifiche.email`, `notifiche.ntfy_topic` | non usarli in un repository pubblico: al loro posto ci sono i Secrets `EMAIL_TO` e `NTFY_TOPIC` |
| `notifiche.solo_nuovi` | `true` avvisa solo per annunci mai visti; `false` rimanda ogni giorno tutti quelli trovati |
| `tipo` | `auto` (predefinito) o `furgone` |
| `marca`, `modello` | testo, es. `"Volkswagen"`, `"Golf"` |
| `carrozzeria` | `utilitaria`, `berlina`, `sw`, `suv`, `monovolume`, `coupe`, `cabrio`, `furgone` |
| `alimentazione` | `benzina`, `diesel`, `ibrida`, `elettrica`, `gpl`, `metano` |
| `cambio` | `manuale`, `automatico` |
| `prezzo_min`, `prezzo_max`, `anno_min`, `anno_max`, `km_max`, `potenza_min_cv` | numeri |
| `cap`, `raggio_km` | zona per AutoScout24 |
| `regione` | es. `lombardia`, per Subito |
| `venditore` | `privato`, `concessionario` |
| `fonti` | elenco dei siti: `autoscout24`, `subito`, `automobile`, `quattroruote`, `automoto`, `autohero`, `spoticar` (anche `mobilede` e `autouncle`, che però da GitHub sono bloccati) |

Un campo `null` o assente significa "qualsiasi". Il campo `url` generato dall'artefatto serve solo come promemoria: lo script ricostruisce gli indirizzi da solo.

### 5. Prima prova

In **Actions → Radar Auto → Run workflow**:

- con **Solo prova** spuntato legge i siti e scrive i risultati in `data/ultima-prova.md`, senza inviare avvisi né segnare gli annunci come visti;
- senza **Solo prova** fa un controllo vero, con email e notifica.

Se un sito smette di funzionare, **Actions → Diagnosi siti → Run workflow** scarica le pagine indicate nel ramo `diagnosi`, così si può vedere com'è cambiato il sito.

## Cambiare orario

Lo script parte solo se in Italia è già passato l'orario scelto e oggi non ha ancora controllato. GitHub però avvia il workflow solo agli orari scritti in `radar.yml`, in UTC. Gli orari attuali (9:30 e 10:30 UTC) coprono le 11:30 italiane sia con l'ora legale sia con l'ora solare.

Per un orario diverso cambia `orario` nel config e le due righe `cron` nel workflow. Esempio per le 18:00: `"0 16 * * *"` e `"0 17 * * *"`.

GitHub può avviare i workflow pianificati con qualche minuto di ritardo, a volte anche mezz'ora nelle ore di punta.

## Usarlo sul computer

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m radar --prova                  # cerca e stampa, non invia e non salva
python -m radar --prova --fonte subito   # prova un solo sito
pytest                                   # test
```

## Limiti

- **I siti cambiano.** Se un sito modifica le sue pagine, lo script può smettere di leggerlo. Lo segnala nell'email e nel riepilogo di GitHub ("nessun annuncio letto"). Va allora aggiornato `radar/estrai.py` o `radar/siti.py`.
- **Blocchi anti-bot.** mobile.de e AutoUncle bloccano già le richieste dai server di GitHub; altri potrebbero farlo in futuro. Lo script usa `curl_cffi` per presentarsi come un normale Chrome, aspetta qualche secondo tra una richiesta e l'altra e fa una sola ricerca al giorno, ma non è garantito che funzioni sempre.
- **Solo la prima pagina.** Per ogni sito si legge la prima pagina di risultati (da 11 a 40 annunci). Con un controllo al giorno basta per i siti ordinati dai più recenti (AutoScout24, Subito). Sugli altri, con ricerche molto ampie, qualche annuncio nuovo può sfuggire: più la ricerca è precisa, meglio funziona.
- **Condizioni d'uso.** Molti portali limitano la raccolta automatica dei loro contenuti. Questo progetto è pensato per uso personale con un controllo al giorno.

## Struttura

```
config/ricerche.json        le tue ricerche
data/stato.json             annunci già segnalati (aggiornato in automatico)
index.html                  l'app (GitHub Pages)
radar/__main__.py           esecuzione giornaliera
radar/adesso.py             ricerca immediata del pulsante "Cerca adesso"
radar/siti.py               indirizzi di ricerca per ogni sito
radar/estrai.py             lettura degli annunci dai dati strutturati (JSON-LD, Next.js)
radar/pagine.py             lettori dedicati: Automoto, Quattroruote, Spoticar, Autohero
radar/filtri.py             filtri su prezzo, anno, km, motore, modello
radar/stato.py              memoria degli annunci visti e doppioni
radar/notifiche.py          email e push
.github/workflows/radar.yml pianificazione su GitHub Actions
.github/workflows/cerca-adesso.yml ricerca immediata avviata dall'app
.github/workflows/diagnosi.yml scarica pagine per capire perché un sito non viene letto
strumenti/scarica_pagine.py usato dalla diagnosi
```
