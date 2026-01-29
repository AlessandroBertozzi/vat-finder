"""Cache per i risultati già elaborati."""

import unicodedata


def normalize_for_search(text: str) -> str:
    """Normalizza testo per ricerca fuzzy."""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.lower()


class ResultsCache:
    """Cache dei risultati già trovati per evitare ricerche duplicate."""

    # Parole da ignorare nel matching
    STOP_WORDS = {'di', 'del', 'della', 'per', 'la', 'il', 'e', 'a', 'in', 'srl', 'spa', 'snc'}

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def __len__(self) -> int:
        return len(self._cache)

    def add(self, company_name: str, result: dict) -> None:
        """Aggiunge un risultato al cache."""
        if result.get('partita_iva') or result.get('codice_fiscale'):
            self._cache[company_name] = result

    def search(self, query: str) -> str:
        """Cerca nel cache delle aziende già elaborate."""
        if not self._cache:
            return "Cache vuoto - nessuna azienda ancora elaborata."

        query_normalized = normalize_for_search(query)
        query_words = set(query_normalized.split())

        matches = []
        for company_name, result in self._cache.items():
            name_normalized = normalize_for_search(company_name)

            # Match se la query è contenuta nel nome o viceversa
            if query_normalized in name_normalized or name_normalized in query_normalized:
                matches.append((company_name, result, "exact"))
                continue

            # Match per parole in comune
            name_words = set(name_normalized.split())
            common_words = query_words & name_words
            common_words -= self.STOP_WORDS

            if len(common_words) >= 2:
                matches.append((company_name, result, f"words: {common_words}"))

        if not matches:
            return f"Nessun match trovato nel cache per '{query}'. Aziende in cache: {len(self._cache)}"

        # Formatta i risultati
        results = []
        for company_name, result, match_type in matches:
            piva = result.get('partita_iva', 'N/A')
            cf = result.get('codice_fiscale', 'N/A')
            results.append(
                f"MATCH ({match_type}):\n  Azienda: {company_name}\n  P.IVA: {piva}\n  CF: {cf}"
            )

        return "\n\n".join(results)
