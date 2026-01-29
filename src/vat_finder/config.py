"""Configurazione dell'agente VAT Finder."""

# Massimo numero di query per azienda
MAX_QUERIES_PER_ORG = 5

# Modelli Claude disponibili
MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-20250514",
}

DEFAULT_MODEL = "haiku"
