# VAT Finder

AI agent to find Italian VAT numbers (Partita IVA) and tax codes (Codice Fiscale) using web search.

## Setup

```bash
pip install -e .
```

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your-key
TAVILY_API_KEY=your-key
```

## Usage

```bash
# Test single company
vat-finder --test "Politecnico di Bari"

# Process CSV file
vat-finder data/input.csv

# Limit to N companies
vat-finder data/input.csv -n 10

# Skip companies with existing VAT
vat-finder data/input.csv --skip-existing

# Use Sonnet model (more accurate)
vat-finder data/input.csv -m sonnet
```

## How it works

1. Agent checks cache for similar companies already processed
2. If not found, searches the web using Tavily
3. Claude analyzes results and extracts VAT/tax code
4. Max 5 queries per company, then moves to next
