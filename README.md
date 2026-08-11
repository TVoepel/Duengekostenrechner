# Duengekostenrechner

Calculate fertilizer prices based on fertilizer strategy.

## NutriSen Düngerechner (`nutrisen_calculator.html`)

Statischer HTML/JS-Rechner zum Vergleich von betriebsüblicher und
NutriSen-optimierter Düngung über beliebig viele Gaben. Preise werden
primär aus selbst erfassten, belegbaren Einkaufspreisen ermittelt
(lineare Interpolation zwischen Preispunkten), optional ergänzt um
monatliche Richtwerte aus dem EU Agri-food Data Portal.

### Monatliche EU-Düngemittelpreise cachen

Der Browser ruft die EU-API **nicht live** ab (Timeout-/Sperr-Risiko).
Stattdessen erzeugt `scripts/fetch_eu_fertilizer_prices.py` regelmäßig
eine lokale `eu_fertilizer_prices.json`, die der Rechner per einfachem
`fetch()` derselben Domain einliest.

```bash
pip install requests pandas openpyxl
python scripts/fetch_eu_fertilizer_prices.py
```

Das Skript sollte regelmäßig per Cronjob (z. B. täglich oder wöchentlich)
ausgeführt werden; die erzeugte `eu_fertilizer_prices.json` muss im
selben Verzeichnis wie `nutrisen_calculator.html` liegen (bzw. dorthin
deployed werden), damit der Button „Zwischengespeicherte EU-Preise
laden" sie findet.

**Quellenangabe / Haftungsausschluss:** Die EU-Preisdaten stammen von
der Europäischen Kommission – Agri-Food Data Portal
(agridata.ec.europa.eu) und sind aggregierte, von den Mitgliedstaaten
gemeldete Marktdaten. Für deren tagesaktuelle Richtigkeit oder daraus
resultierende Handelsverluste wird keine Haftung übernommen; die
Europäische Kommission schließt ihrerseits jegliche Haftung für die
Nutzung ihrer API-/Portaldaten aus.
