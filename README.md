# Radar Auto Usate

Ogni giorno alle 11:30 (ora italiana) cerca auto usate su 9 siti e, se trova annunci nuovi, ti manda una email e una notifica push sul telefono.

**Siti controllati:** AutoScout24, Subito.it, Automobile.it, mobile.de, AutoUncle, Quattroruote, Automoto.it, Autohero, Spoticar.

Le ricerche si preparano con l'artefatto **Radar Auto Usate** su claude.ai, che genera il file `config/ricerche.json`. Si può anche modificare il file a mano.

## Come funziona

1. GitHub Actions avvia `python -m radar` ogni giorno (`.github/workflows/radar.yml`).
2. Per ogni ricerca e ogni sito lo script apre la pagina dei risultati ordinata dai più recenti e legge gli annunci dai dati strutturati della pagina (JSON-LD o `__NEXT_DATA__`).
3. Applica i filtri della ricerca: prezzo, anno, km, alimentazione, cambio, marca e modello.
4. Confronta i risultati con `data/stato.json`, che contiene gli annunci già segnalati. La stessa auto pubblicata su più siti viene segnalata una volta sola.
5. Se ci sono annunci nuovi invia l'email e la notifica push, poi salva `data/stato.json` nel repository.

Alla prima esecuzione tutti gli annunci trovati risultano nuovi, quindi la prima email sarà più lunga del solito.

## Configurazione

### 1. Repository privato

Tieni il repository **privato**: `config/ricerche.json` contiene le tue ricerche. Il piano gratuito di GitHub include 2.000 minuti di Actions al mese per i repository privati. Questo progetto ne usa circa 60-100.

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
| `notifiche.solo_nuovi` | `true` avvisa solo per annunci mai visti; `false` rimanda ogni giorno tutti quelli trovati |
| `marca`, `modello` | testo, es. `"Volkswagen"`, `"Golf"` |
| `carrozzeria` | `utilitaria`, `berlina`, `sw`, `suv`, `monovolume`, `coupe`, `cabrio`, `furgone` |
| `alimentazione` | `benzina`, `diesel`, `ibrida`, `elettrica`, `gpl`, `metano` |
| `cambio` | `manuale`, `automatico` |
| `prezzo_min`, `prezzo_max`, `anno_min`, `anno_max`, `km_max`, `potenza_min_cv` | numeri |
| `cap`, `raggio_km` | zona per AutoScout24 |
| `regione` | es. `lombardia`, per Subito |
| `venditore` | `privato`, `concessionario` |
| `fonti` | elenco dei siti: `autoscout24`, `subito`, `automobile`, `mobilede`, `autouncle`, `quattroruote`, `automoto`, `autohero`, `spoticar` |

Un campo `null` o assente significa "qualsiasi". Il campo `url` generato dall'artefatto serve solo come promemoria: lo script ricostruisce gli indirizzi da solo.

### 5. Prima prova

In **Actions → Radar Auto → Run workflow** puoi avviare subito un controllo. Il riepilogo della corsa mostra quanti annunci ha letto ogni sito e gli eventuali problemi.

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
- **Blocchi anti-bot.** Alcuni siti, mobile.de in particolare, possono bloccare le richieste dai server di GitHub. Lo script usa `curl_cffi` per presentarsi come un normale Chrome, aspetta qualche secondo tra una richiesta e l'altra e fa una sola ricerca al giorno, ma non è garantito che funzioni sempre.
- **Filtri parziali.** AutoScout24 riceve tutti i filtri nell'indirizzo. Gli altri siti ne ricevono una parte e lo script applica il resto. Su Autohero e Spoticar la ricerca parte dalla pagina generale, quindi vengono letti solo i primi risultati: per ricerche precise vanno adattati gli indirizzi in `radar/siti.py`.
- **Condizioni d'uso.** Molti portali limitano la raccolta automatica dei loro contenuti. Questo progetto è pensato per uso personale con un controllo al giorno.

## Struttura

```
config/ricerche.json        le tue ricerche
data/stato.json             annunci già segnalati (aggiornato in automatico)
radar/__main__.py           esecuzione giornaliera
radar/siti.py               indirizzi di ricerca per ogni sito
radar/estrai.py             lettura degli annunci dalle pagine
radar/filtri.py             filtri su prezzo, anno, km, motore, modello
radar/stato.py              memoria degli annunci visti e doppioni
radar/notifiche.py          email e push
.github/workflows/radar.yml pianificazione su GitHub Actions
```
