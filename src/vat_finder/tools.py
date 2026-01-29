"""Definizione dei tools per l'agente."""

TOOLS = [
    {
        "name": "search_cache",
        "description": (
            "Cerca tra le aziende già elaborate in questa sessione. "
            "Usa SEMPRE questo tool PRIMA di fare ricerche web per verificare "
            "se un'azienda simile è già stata trovata. Cerca per parole chiave o acronimi."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Parole chiave da cercare "
                        "(es. 'ARTI', 'Agenzia Regionale Tecnologia', 'Politecnico')"
                    )
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "web_search",
        "description": (
            "Cerca informazioni sul web. Usa questo tool per trovare Partita IVA "
            "o Codice Fiscale di un'azienda italiana. Puoi fare query come "
            "'NomeAzienda partita iva', 'NomeAzienda codice fiscale', "
            "'NomeAzienda visura camerale', etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "La query di ricerca da eseguire"
                }
            },
            "required": ["query"]
        }
    }
]
