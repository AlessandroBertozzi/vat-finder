"""Funzioni di input/output per file CSV."""

import csv


def load_companies(csv_path: str) -> list[dict]:
    """Carica le aziende dal file CSV."""
    companies = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            company = {
                "id": idx,
                "name": row["Name"],
                "existing_vat": row.get("VAT Number", ""),
                "city": row.get("City", ""),
                "street": row.get("Street", ""),
                "postal_code": row.get("Postal Code", ""),
                "original_row": row
            }
            companies.append(company)
    return companies


def save_results(companies: list[dict], results: list[dict], output_path: str) -> None:
    """Salva i risultati in un CSV."""
    if not companies:
        return

    fieldnames = list(companies[0]["original_row"].keys())
    fieldnames.extend(["Found_PIVA", "Found_CF", "Source", "Queries_Used", "Notes"])

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for company, result in zip(companies, results):
            row = company["original_row"].copy()
            row["Found_PIVA"] = result.get("partita_iva", "")
            row["Found_CF"] = result.get("codice_fiscale", "")
            row["Source"] = result.get("fonte", "")
            row["Queries_Used"] = result.get("queries_used", 0)
            row["Notes"] = result.get("note", "")
            writer.writerow(row)

    print(f"\nRisultati salvati in {output_path}")
