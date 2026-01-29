# VAT Finder

Agente AI per trovare Partita IVA e Codice Fiscale di aziende italiane tramite ricerche web.

## Funzionalità

- **Ricerca automatica**: L'agente decide autonomamente quali query fare per trovare P.IVA/CF
- **Cache intelligente**: Evita ricerche duplicate riconoscendo aziende simili già elaborate
- **Tool use**: Usa l'architettura tool_use di Claude per un approccio veramente agentico
- **Ricerca web**: Integrazione con Tavily per ricerche web accurate
- **Batch processing**: Processa file CSV con migliaia di aziende
- **Salvataggio incrementale**: Salva i risultati ogni 10 aziende per evitare perdite di dati

## Installazione

### Da sorgente

```bash
git clone https://github.com/yourusername/vat-finder.git
cd vat-finder
pip install -e .
```

### Dipendenze manuali

```bash
pip install anthropic tavily-python python-dotenv
```

## Configurazione

Crea un file `.env` nella directory del progetto:

```env
ANTHROPIC_API_KEY=your-anthropic-api-key
TAVILY_API_KEY=your-tavily-api-key
```

Oppure esporta le variabili d'ambiente:

```bash
export ANTHROPIC_API_KEY="your-key"
export TAVILY_API_KEY="your-key"
```

## Utilizzo

### Test singola azienda

```bash
vat-finder --test "Politecnico di Bari"
```

### Processare un file CSV

```bash
# Processa tutte le aziende
vat-finder input.csv

# Limita a 10 aziende
vat-finder input.csv -n 10

# Salta aziende con VAT già presente
vat-finder input.csv --skip-existing

# Usa modello Sonnet (più preciso)
vat-finder input.csv -m sonnet

# Specifica file di output
vat-finder input.csv -o risultati.csv

# Riprendi da un certo indice
vat-finder input.csv --start 50 -n 20
```

### Opzioni

| Opzione | Descrizione |
|---------|-------------|
| `-n, --limit N` | Processa solo N aziende |
| `--skip-existing` | Salta aziende con VAT già presente |
| `-m, --model MODEL` | Modello Claude: `haiku` (default) o `sonnet` |
| `-o, --output FILE` | File CSV di output |
| `--start N` | Inizia dall'indice N |
| `--test "NOME"` | Testa una singola azienda |

## Formato CSV

### Input

Il file CSV deve avere almeno la colonna `Name`. Colonne opzionali:

| Colonna | Descrizione |
|---------|-------------|
| `Name` | Nome dell'azienda (obbligatorio) |
| `VAT Number` | P.IVA esistente (opzionale) |
| `City` | Città (aiuta la ricerca) |
| `Street` | Indirizzo |
| `Postal Code` | CAP |

### Output

Il CSV di output include tutte le colonne originali più:

| Colonna | Descrizione |
|---------|-------------|
| `Found_PIVA` | Partita IVA trovata |
| `Found_CF` | Codice Fiscale trovato |
| `Source` | Fonte dell'informazione |
| `Queries_Used` | Numero di query usate |
| `Notes` | Note aggiuntive |

## Come funziona

1. **Cache check**: L'agente cerca prima nel cache se un'azienda simile è già stata elaborata
2. **Ricerca web**: Se non trova nel cache, usa Tavily per cercare sul web
3. **Analisi**: Claude analizza i risultati e estrae P.IVA/CF
4. **Iterazione**: Se non trova, prova query diverse (max 5 per azienda)
5. **Salvataggio**: I risultati vengono salvati nel cache e nel CSV

## Architettura

```
src/vat_finder/
├── __init__.py      # Package exports
├── agent.py         # Classe VATFinderAgent
├── cache.py         # Cache dei risultati
├── cli.py           # Command-line interface
├── config.py        # Configurazione
├── io.py            # Input/output CSV
├── prompts.py       # System prompt
└── tools.py         # Definizione tools
```

## Licenza

MIT
