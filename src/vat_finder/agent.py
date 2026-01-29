"""Agente principale per la ricerca di P.IVA e CF."""

import json
from anthropic import Anthropic
from tavily import TavilyClient

from .cache import ResultsCache
from .config import MAX_QUERIES_PER_ORG
from .prompts import SYSTEM_PROMPT
from .tools import TOOLS


class VATFinderAgent:
    """Agente che cerca P.IVA/CF usando tool_use di Claude."""

    def __init__(self, anthropic_client: Anthropic, tavily_client: TavilyClient, model: str):
        self.anthropic = anthropic_client
        self.tavily = tavily_client
        self.model = model
        self.cache = ResultsCache()

    def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        """Esegue un tool e restituisce il risultato."""
        if tool_name == "search_cache":
            query = tool_input.get("query", "")
            print(f"    [CACHE] Ricerca: {query}")
            return self.cache.search(query)

        elif tool_name == "web_search":
            query = tool_input.get("query", "")
            print(f"    [WEB] Ricerca: {query}")

            try:
                response = self.tavily.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    include_answer=False
                )

                results = response.get("results", [])
                if not results:
                    return "Nessun risultato trovato."

                # Formatta i risultati per Claude
                formatted = []
                for r in results:
                    formatted.append(
                        f"URL: {r.get('url', 'N/A')}\n"
                        f"Titolo: {r.get('title', 'N/A')}\n"
                        f"Contenuto: {r.get('content', 'N/A')}"
                    )

                return "\n\n---\n\n".join(formatted)

            except Exception as e:
                return f"Errore nella ricerca: {e}"

        return f"Tool sconosciuto: {tool_name}"

    def _extract_json_result(self, text: str) -> dict | None:
        """Estrae il JSON dal testo di risposta."""
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass
        return None

    def search_company(self, company: dict) -> dict:
        """Cerca P.IVA/CF per un'azienda usando l'agentic loop."""

        print(f"\n{'='*60}")
        print(f"Azienda: {company['name']}")
        if company.get('city'):
            print(f"Città: {company['city']}")
        if company.get('existing_vat'):
            print(f"VAT esistente: {company['existing_vat']}")
        print(f"{'='*60}")

        # Messaggio iniziale per Claude
        user_message = f"""Trova la Partita IVA e/o il Codice Fiscale di questa azienda:

Nome: {company['name']}
Città: {company.get('city', 'Non specificata')}
Indirizzo: {company.get('street', 'Non specificato')}
CAP: {company.get('postal_code', 'Non specificato')}

Hai a disposizione massimo {MAX_QUERIES_PER_ORG} ricerche. Inizia!"""

        messages = [{"role": "user", "content": user_message}]
        queries_used = 0

        # Agentic loop
        while queries_used < MAX_QUERIES_PER_ORG:
            response = self.anthropic.messages.create(
                model=self.model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            # Controlla se Claude ha finito
            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, 'text'):
                        print(f"\n  [AGENTE] {block.text[:200]}...")
                        result = self._extract_json_result(block.text)
                        if result:
                            result['queries_used'] = queries_used
                            self.cache.add(company['name'], result)
                            return result

                return {
                    "partita_iva": None,
                    "codice_fiscale": None,
                    "queries_used": queries_used,
                    "note": "Risposta non strutturata"
                }

            # Processa tool_use
            tool_results = []
            assistant_content = response.content

            for block in response.content:
                if block.type == "tool_use":
                    queries_used += 1
                    print(f"\n  [{queries_used}/{MAX_QUERIES_PER_ORG}]", end="")

                    tool_result = self._execute_tool(block.name, block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result
                    })
                elif hasattr(block, 'text') and block.text:
                    print(f"\n  [PENSIERO] {block.text[:100]}...")

            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        # Query esaurite, chiedi risposta finale
        messages.append({
            "role": "user",
            "content": "Hai esaurito le ricerche disponibili. Rispondi con il JSON del risultato."
        })

        response = self.anthropic.messages.create(
            model=self.model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=messages
        )

        for block in response.content:
            if hasattr(block, 'text'):
                result = self._extract_json_result(block.text)
                if result:
                    result['queries_used'] = queries_used
                    self.cache.add(company['name'], result)
                    return result

        return {
            "partita_iva": None,
            "codice_fiscale": None,
            "queries_used": queries_used,
            "note": "Nessun risultato"
        }
