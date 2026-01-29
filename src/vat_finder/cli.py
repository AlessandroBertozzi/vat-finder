"""Command-line interface per VAT Finder."""

import argparse
import os
import sys

from dotenv import load_dotenv
from anthropic import Anthropic
from tavily import TavilyClient

from .agent import VATFinderAgent
from .config import MODELS, DEFAULT_MODEL, MAX_QUERIES_PER_ORG
from .io import load_companies, save_results


def create_parser() -> argparse.ArgumentParser:
    """Crea il parser degli argomenti."""
    parser = argparse.ArgumentParser(
        description="Trova P.IVA/CF di aziende italiane usando ricerche web",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  vat-finder --test "Politecnico di Bari"
  vat-finder input.csv -n 10
  vat-finder input.csv --skip-existing
  vat-finder input.csv -m sonnet -o output.csv
        """
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        help="File CSV di input con le aziende"
    )
    parser.add_argument(
        "-m", "--model",
        choices=list(MODELS.keys()),
        default=DEFAULT_MODEL,
        help=f"Modello Claude da usare (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=None,
        help="Numero massimo di aziende da processare"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Salta aziende che hanno già un VAT number"
    )
    parser.add_argument(
        "-o", "--output",
        help="File CSV di output (default: input_with_vat.csv)"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Indice da cui iniziare (per riprendere elaborazioni)"
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        help="Testa una singola azienda passando il nome direttamente"
    )

    return parser


def main() -> None:
    """Entry point principale."""
    # Carica variabili d'ambiente
    load_dotenv()

    parser = create_parser()
    args = parser.parse_args()

    # Verifica che ci sia input_csv o --test
    if not args.test and not args.input_csv:
        parser.error("Specificare un file CSV di input oppure usare --test")

    # Verifica API keys
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")

    if not anthropic_key:
        print("Errore: ANTHROPIC_API_KEY non configurata")
        print("Aggiungi la chiave nel file .env o come variabile d'ambiente")
        sys.exit(1)

    if not tavily_key:
        print("Errore: TAVILY_API_KEY non configurata")
        print("Aggiungi la chiave nel file .env o come variabile d'ambiente")
        sys.exit(1)

    # Inizializza client
    anthropic_client = Anthropic(api_key=anthropic_key)
    tavily_client = TavilyClient(api_key=tavily_key)
    model = MODELS[args.model]

    print(f"Modello: {args.model} ({model})")
    print(f"Max query per azienda: {MAX_QUERIES_PER_ORG}")

    # Inizializza agente
    agent = VATFinderAgent(anthropic_client, tavily_client, model)

    # Modalità test
    if args.test:
        company = {
            "id": 0,
            "name": args.test,
            "existing_vat": "",
            "city": "",
            "street": "",
            "postal_code": "",
            "original_row": {"Name": args.test}
        }
        result = agent.search_company(company)
        print(f"\n{'='*60}")
        print("RISULTATO FINALE:")
        print(f"  P.IVA: {result.get('partita_iva', 'Non trovata')}")
        print(f"  CF: {result.get('codice_fiscale', 'Non trovato')}")
        print(f"  Fonte: {result.get('fonte', 'N/A')}")
        print(f"  Query usate: {result.get('queries_used', 0)}")
        print(f"  Note: {result.get('note', '')}")
        return

    # Carica aziende da CSV
    input_csv = args.input_csv
    output_csv = args.output or input_csv.replace(".csv", "_with_vat.csv")

    print(f"\nCaricamento aziende da {input_csv}...")
    companies = load_companies(input_csv)
    print(f"Caricate {len(companies)} aziende")

    # Filtra se richiesto
    if args.skip_existing:
        original_count = len(companies)
        companies = [c for c in companies if not c.get("existing_vat")]
        print(f"Filtrate {original_count - len(companies)} aziende con VAT esistente")

    # Applica start e limit
    if args.start > 0:
        companies = companies[args.start:]
        print(f"Partendo dall'indice {args.start}")

    if args.limit:
        companies = companies[:args.limit]
        print(f"Limitate a {len(companies)} aziende")

    # Processa ogni azienda
    results = []
    found_count = 0

    try:
        for i, company in enumerate(companies):
            print(f"\n[{i+1}/{len(companies)}]", end="")
            result = agent.search_company(company)
            results.append(result)

            if result.get("partita_iva") or result.get("codice_fiscale"):
                found_count += 1

            # Salva risultati intermedi ogni 10 aziende
            if (i + 1) % 10 == 0:
                print(f"\n--- Salvataggio intermedio ({i+1} aziende) ---")
                save_results(companies[:i+1], results, output_csv)

    except KeyboardInterrupt:
        print("\n\nInterrotto dall'utente. Salvataggio risultati parziali...")

    # Salva risultati finali
    if results:
        save_results(companies[:len(results)], results, output_csv)

    # Statistiche finali
    print(f"\n{'='*60}")
    print("COMPLETATO!")
    print(f"{'='*60}")
    print(f"Aziende processate: {len(results)}")
    print(f"P.IVA/CF trovati: {found_count}")
    if results:
        print(f"Percentuale successo: {found_count/len(results)*100:.1f}%")
    print(f"Output: {output_csv}")


if __name__ == "__main__":
    main()
