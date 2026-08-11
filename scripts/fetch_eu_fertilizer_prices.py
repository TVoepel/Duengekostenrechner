"""
Ruft monatliche Düngemittelpreise vom EU Agri-food Data Portal ab und
speichert sie als lokale, cachefähige JSON-Datei für den NutriSen
Düngerechner (nutrisen_calculator.html).

WARUM EIN SEPARATES SKRIPT (statt Live-Abruf im Browser)?
- Der Browser der Website-Besucher soll NICHT bei jedem Aufruf direkt
  die EU-Server anfragen (CORS-Probleme, Timeouts, Gefahr einer
  temporären IP-Sperre bei steigendem Traffic).
- Stattdessen läuft dieses Skript regelmäßig (z. B. per Cronjob einmal
  täglich/wöchentlich) und schreibt die Ergebnisse in eine JSON-Datei,
  die zusammen mit der Webseite ausgeliefert wird. Der Rechner liest
  diese Datei dann per einfachem, schnellem fetch() derselben Domain.

DATENQUELLE:
  Europäische Kommission – Agri-food Data Portal (DG AGRI), Datensatz
  "Fertiliser prices". Offizielle Doku/Portal:
  https://agridata.ec.europa.eu/extensions/dataportal/agricultural_markets.html
  API-Basis: https://ec.europa.eu/agrifood/api/fertiliser/prices

RECHTLICHER HINWEIS:
  Es handelt sich um von Mitgliedstaaten gemeldete, aggregierte
  Marktdaten der Europäischen Kommission. Für tagesaktuelle Richtigkeit
  wird keine Haftung übernommen; die Europäische Kommission schließt
  ihrerseits jegliche Haftung für die Nutzung ihrer API-/Portaldaten
  aus. Bei Veröffentlichung ist die Quelle zu nennen:
  "Quelle: Europäische Kommission – Agri-Food Data Portal".

Benötigte Pakete: requests, pandas, openpyxl (für optionalen Excel-Export)
  pip install requests pandas openpyxl
"""

import json
import sys
from datetime import datetime, timezone

import requests
import pandas as pd

# Offizieller API-Endpunkt für den Datensatz "Fertiliser prices" des
# Agri-food Data Portal. "https://europa.eu" (wie im Ausgangsbeispiel)
# ist nur die allgemeine EU-Startseite und liefert kein JSON - das war
# ein Platzhalter und musste durch den echten Endpunkt ersetzt werden.
API_URL = "https://ec.europa.eu/agrifood/api/fertiliser/prices"

MEMBER_STATE_CODE = "DE"  # Deutschland

# Mapping der EU-Produktbezeichnungen auf die im Rechner verwendeten
# Düngemittel-Namen (siehe FERTILIZERS in nutrisen_calculator.html).
# Die exakten Bezeichnungen im Datensatz können variieren; hier werden
# gängige Substring-Muster verwendet. Bei Bedarf anpassen/erweitern.
PRODUCT_NAME_MAP = {
    "ammonium nitrate": "KAS 27% N",
    "calcium ammonium nitrate": "KAS 27% N",
    "urea ammonium sulphate": "ASS 26% N + 13% S",
    "urea": "Harnstoff 46% N",
    "uan": "AHL 28% N",
    "urea ammonium nitrate": "AHL 28% N",
    "dap": "DAP 18% N + 46% P2O5",
    "diammonium phosphate": "DAP 18% N + 46% P2O5",
    "npk": "NPK 15-15-15",
}

OUTPUT_JSON = "eu_fertilizer_prices.json"
OUTPUT_XLSX = "duengemittelpreise_deutschland.xlsx"


def map_product_name(description: str):
    if not isinstance(description, str):
        return None
    desc_lower = description.lower()
    for pattern, mapped_name in PRODUCT_NAME_MAP.items():
        if pattern in desc_lower:
            return mapped_name
    return None


def fetch_eu_fertilizer_prices() -> pd.DataFrame:
    print(f"Rufe Daten vom EU Agri-food Data Portal ab: {API_URL}")
    response = requests.get(
        API_URL,
        params={"memberStateCode": MEMBER_STATE_CODE},
        timeout=30,
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)
    if df.empty:
        raise ValueError("Die API hat keine Datensätze zurückgegeben.")

    df["memberStateCode"] = df.get("memberStateCode", "").fillna("")
    df_germany = df[df["memberStateCode"].str.upper() == MEMBER_STATE_CODE].copy()

    if df_germany.empty:
        print(
            "Hinweis: Keine spezifischen Datensätze mit dem Länderkürzel "
            f"'{MEMBER_STATE_CODE}' gefunden. Es werden alle zurückgegebenen "
            "Datensätze verwendet (ggf. war der Server-seitige Filter bereits wirksam)."
        )
        df_germany = df.copy()

    df_germany = df_germany.sort_values(by="beginDate", ascending=False)
    return df_germany


def build_price_points(df: pd.DataFrame) -> list:
    """Erzeugt Preispunkte im Format, das der Rechner importieren kann:
    [{ fert, date, price, note }]
    """
    points = []
    for _, row in df.iterrows():
        mapped = map_product_name(row.get("productDescription", ""))
        if not mapped:
            continue
        price = row.get("price")
        begin_date = row.get("beginDate")
        if price is None or not begin_date:
            continue
        points.append(
            {
                "fert": mapped,
                "date": str(begin_date)[:10],
                "price": float(price),
                "note": (
                    "EU Agri-food Data Portal – "
                    f"{row.get('productDescription', '')} "
                    f"({row.get('unit', '')})"
                ),
            }
        )
    return points


def main():
    try:
        df_germany = fetch_eu_fertilizer_prices()
    except requests.exceptions.RequestException as exc:
        print(f"Fehler beim API-Abruf: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Ein Fehler ist aufgetreten: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"\nGefundene Einträge für {MEMBER_STATE_CODE}: {len(df_germany)}")
    cols = [c for c in ["beginDate", "productDescription", "price", "unit"] if c in df_germany.columns]
    print(df_germany[cols].head(10))

    price_points = build_price_points(df_germany)

    output = {
        "source": "Europäische Kommission – Agri-Food Data Portal",
        "sourceUrl": "https://agridata.ec.europa.eu/extensions/dataportal/agricultural_markets.html",
        "disclaimer": (
            "Es handelt sich um aggregierte, von den Mitgliedstaaten gemeldete "
            "EU-Marktdaten. Für die tagesaktuelle Richtigkeit dieser Daten oder "
            "daraus resultierende Handelsentscheidungen/-verluste wird keine "
            "Haftung übernommen. Die Europäische Kommission schließt ihrerseits "
            "jegliche Haftung für die Nutzung ihrer API- bzw. Portaldaten aus."
        ),
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "memberStateCode": MEMBER_STATE_CODE,
        "pricePoints": price_points,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nJSON für den Düngerechner gespeichert unter: {OUTPUT_JSON}")

    try:
        df_germany.to_excel(OUTPUT_XLSX, index=False)
        print(f"Zusätzlich als Excel gespeichert unter: {OUTPUT_XLSX}")
    except ImportError:
        print("Hinweis: 'openpyxl' nicht installiert, Excel-Export übersprungen.")


if __name__ == "__main__":
    main()
