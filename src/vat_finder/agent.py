"""Agente principale per la ricerca di P.IVA e CF."""

import json
from anthropic import Anthropic
from tavily import TavilyClient
from rich.console import Console
from rich.tree import Tree

from .cache import ResultsCache
from .config import MAX_QUERIES_PER_ORG
from .prompts import SYSTEM_PROMPT
from .tools import TOOLS

console = Console()


class VATFinderAgent:
    """Agente che cerca P.IVA/CF usando tool_use di Claude."""

    def __init__(self, anthropic_client: Anthropic, tavily_client: TavilyClient, model: str, max_queries: int = MAX_QUERIES_PER_ORG):
        self.anthropic = anthropic_client
        self.tavily = tavily_client
        self.model = model
        self.max_queries = max_queries
        self.cache = ResultsCache()

    def _execute_tool(self, tool_name: str, tool_input: dict, tree: Tree) -> str:
        """Esegue un tool e restituisce il risultato."""
        if tool_name == "search_cache":
            query = tool_input.get("query", "")
            tree.add(f"[cyan]CACHE[/] {query}")
            return self.cache.search(query)

        elif tool_name == "web_search":
            query = tool_input.get("query", "")
            tree.add(f"[yellow]WEB[/] {query}")

            try:
                response = self.tavily.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    include_answer=False
                )

                results = response.get("results", [])
                if not results:
                    return "No results found."

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
                return f"Search error: {e}"

        return f"Unknown tool: {tool_name}"

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

        # Crea l'albero per questa azienda
        company_label = f"[bold]{company['name']}[/]"
        if company.get('city'):
            company_label += f" [dim]({company['city']})[/]"
        tree = Tree(company_label)

        # Messaggio iniziale per Claude
        user_message = f"""Trova la Partita IVA e/o il Codice Fiscale di questa azienda:

Nome: {company['name']}
Città: {company.get('city', 'Non specificata')}
Indirizzo: {company.get('street', 'Non specificato')}
CAP: {company.get('postal_code', 'Non specificato')}

Hai a disposizione massimo {self.max_queries} ricerche. Inizia!"""

        messages = [{"role": "user", "content": user_message}]
        queries_used = 0

        # Agentic loop
        while queries_used < self.max_queries:
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
                        result = self._extract_json_result(block.text)
                        if result:
                            result['queries_used'] = queries_used
                            self.cache.add(company['name'], result)
                            # Aggiungi risultato all'albero e stampa
                            piva = result.get('partita_iva')
                            cf = result.get('codice_fiscale')
                            if piva or cf:
                                res_str = f"[bold green]P.IVA: {piva or '-'}[/] | [bold green]CF: {cf or '-'}[/]"
                            else:
                                res_str = "[dim]Not found[/]"
                            tree.add(res_str)
                            console.print(tree)
                            return result

                tree.add("[dim]Unstructured response[/]")
                console.print(tree)
                return {
                    "partita_iva": None,
                    "codice_fiscale": None,
                    "queries_used": queries_used,
                    "note": "Unstructured response"
                }

            # Processa tool_use
            tool_results = []
            assistant_content = response.content

            for block in response.content:
                if block.type == "tool_use":
                    queries_used += 1
                    tool_result = self._execute_tool(block.name, block.input, tree)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result
                    })

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
                    piva = result.get('partita_iva')
                    cf = result.get('codice_fiscale')
                    if piva or cf:
                        res_str = f"[bold green]P.IVA: {piva or '-'}[/] | [bold green]CF: {cf or '-'}[/]"
                    else:
                        res_str = "[dim]Not found[/]"
                    tree.add(res_str)
                    console.print(tree)
                    return result

        tree.add("[dim]No result[/]")
        console.print(tree)
        return {
            "partita_iva": None,
            "codice_fiscale": None,
            "queries_used": queries_used,
            "note": "No result"
        }
