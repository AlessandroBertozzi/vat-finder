"""Tests per il modulo cache."""

import pytest
from vat_finder.cache import ResultsCache, normalize_for_search


class TestNormalizeForSearch:
    def test_lowercase(self):
        assert normalize_for_search("HELLO") == "hello"

    def test_accents(self):
        assert normalize_for_search("città") == "citta"
        assert normalize_for_search("società") == "societa"

    def test_combined(self):
        assert normalize_for_search("SOCIETÀ S.R.L.") == "societa s.r.l."


class TestResultsCache:
    def test_empty_cache(self):
        cache = ResultsCache()
        result = cache.search("test")
        assert "Cache vuoto" in result

    def test_add_and_search_exact(self):
        cache = ResultsCache()
        cache.add("Politecnico di Bari", {"partita_iva": "12345678901"})

        result = cache.search("Politecnico di Bari")
        assert "MATCH" in result
        assert "12345678901" in result

    def test_add_without_data(self):
        cache = ResultsCache()
        cache.add("Test Company", {"partita_iva": None, "codice_fiscale": None})
        assert len(cache) == 0

    def test_search_partial_match(self):
        cache = ResultsCache()
        cache.add(
            "Agenzia Regionale Per La Tecnologia E L'Innovazione",
            {"partita_iva": "11111111111"}
        )

        # Cerca con parole chiave
        result = cache.search("Agenzia Tecnologia Innovazione")
        assert "MATCH" in result

    def test_search_no_match(self):
        cache = ResultsCache()
        cache.add("Politecnico di Bari", {"partita_iva": "12345678901"})

        result = cache.search("Università di Roma")
        assert "Nessun match" in result
