"""Command-line interface per VAT Finder."""

import argparse
import os
import sys

from dotenv import load_dotenv
from anthropic import Anthropic
from tavily import TavilyClient
from rich.console import Console

from .agent import VATFinderAgent
from .config import MODELS, DEFAULT_MODEL, MAX_QUERIES_PER_ORG
from .io import load_companies, save_results

console = Console()


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Find VAT/CF of Italian companies using web search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  vat-finder --test "Politecnico di Bari"
  vat-finder input.csv -n 10
  vat-finder input.csv --skip-existing
  vat-finder input.csv -m sonnet -o output.csv
        """
    )
    parser.add_argument(
        "input_csv",
        nargs="?",
        help="Input CSV file with companies"
    )
    parser.add_argument(
        "-m", "--model",
        choices=list(MODELS.keys()),
        default=DEFAULT_MODEL,
        help=f"Claude model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=None,
        help="Max number of companies to process"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip companies that already have a VAT number"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output CSV file (default: input_with_vat.csv)"
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start index (to resume processing)"
    )
    parser.add_argument(
        "--test",
        type=str,
        default=None,
        help="Test a single company by name"
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=MAX_QUERIES_PER_ORG,
        help=f"Max tool calls per company (default: {MAX_QUERIES_PER_ORG})"
    )

    return parser


def main() -> None:
    """Entry point principale."""
    # Carica variabili d'ambiente
    load_dotenv()

    parser = create_parser()
    args = parser.parse_args()

    # Check for input_csv or --test
    if not args.test and not args.input_csv:
        parser.error("Specify an input CSV file or use --test")

    # Verifica API keys
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    tavily_key = os.environ.get("TAVILY_API_KEY")

    if not anthropic_key:
        console.print("[bold red]Error:[/] ANTHROPIC_API_KEY not configured")
        console.print("[dim]Add the key in .env file or as environment variable[/]")
        sys.exit(1)

    if not tavily_key:
        console.print("[bold red]Error:[/] TAVILY_API_KEY not configured")
        console.print("[dim]Add the key in .env file or as environment variable[/]")
        sys.exit(1)

    # Inizializza client
    anthropic_client = Anthropic(api_key=anthropic_key)
    tavily_client = TavilyClient(api_key=tavily_key)
    model = MODELS[args.model]

    console.print(f"\n[bold cyan]VAT Finder[/] | {args.model} | max {args.max_queries} query")

    # Inizializza agente
    agent = VATFinderAgent(anthropic_client, tavily_client, model, max_queries=args.max_queries)

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
        agent.search_company(company)
        return

    # Carica aziende da CSV
    input_csv = args.input_csv
    output_csv = args.output or input_csv.replace(".csv", "_with_vat.csv")

    console.print(f"\n[dim]Loading companies from[/] {input_csv}...")
    companies = load_companies(input_csv)
    console.print(f"[bold]{len(companies)}[/] companies loaded")

    # Filter if requested
    if args.skip_existing:
        original_count = len(companies)
        companies = [c for c in companies if not c.get("existing_vat")]
        console.print(f"[yellow]Filtered {original_count - len(companies)} companies with existing VAT[/]")

    # Apply start and limit
    if args.start > 0:
        companies = companies[args.start:]
        console.print(f"[dim]Starting from index {args.start}[/]")

    if args.limit:
        companies = companies[:args.limit]
        console.print(f"[dim]Limited to {len(companies)} companies[/]")

    # Processa ogni azienda
    results = []
    found_count = 0

    try:
        for i, company in enumerate(companies):
            result = agent.search_company(company)
            results.append(result)

            if result.get("partita_iva") or result.get("codice_fiscale"):
                found_count += 1

            # Save intermediate results every 10 companies
            if (i + 1) % 10 == 0:
                console.print(f"[dim]Saved {i+1}/{len(companies)}[/]")
                save_results(companies[:i+1], results, output_csv)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Saving...[/]")

    # Salva risultati finali
    if results:
        save_results(companies[:len(results)], results, output_csv)

    # Summary
    if results:
        pct = found_count / len(results) * 100
        color = "green" if pct >= 70 else "yellow" if pct >= 40 else "red"
        console.print(f"\n[bold]Done:[/] {found_count}/{len(results)} found ([{color}]{pct:.0f}%[/]) -> {output_csv}")


if __name__ == "__main__":
    main()
