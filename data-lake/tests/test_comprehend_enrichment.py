import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "enrichment"
    / "comprehend_enrichment.py"
)

spec = importlib.util.spec_from_file_location(
    "comprehend_enrichment",
    MODULE_PATH,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_cache_key_is_deterministic():
    text = "Microsoft invierte en Medellín"

    first = module.get_cache_key(text)
    second = module.get_cache_key(text)

    assert first == second


def test_normalize_entities():
    response = {
        "Entities": [
            {
                "Text": "Microsoft",
                "Type": "ORGANIZATION",
                "Score": 0.99,
            },
            {
                "Text": "Medellín",
                "Type": "LOCATION",
                "Score": 0.98,
            },
            {
                "Text": "2026",
                "Type": "DATE",
                "Score": 0.95,
            },
        ]
    }

    result = module.normalize_entities(response)

    assert len(result) == 2
    assert result[0]["type"] == "ORGANIZATION"
    assert result[1]["type"] == "LOCATION"


def test_normalize_key_phrases():
    response = {
        "KeyPhrases": [
            {
                "Text": "inteligencia artificial",
                "Score": 0.97,
            }
        ]
    }

    result = module.normalize_key_phrases(response)

    assert len(result) == 1
    assert result[0]["text"] == "inteligencia artificial"


def test_dry_run_does_not_call_api(monkeypatch, tmp_path):
    monkeypatch.setattr(
        module,
        "CACHE_DIR",
        tmp_path,
    )

    result = module.enrich_news(
        "Microsoft invierte en Medellín",
        "Proyecto de inteligencia artificial",
        allow_api_calls=False,
    )

    assert result["status"] == "not_processed"
    assert result["cache_hit"] is False
    assert result["entities"] == []
    assert result["key_phrases"] == []


def test_cache_reuses_results(monkeypatch, tmp_path):
    monkeypatch.setattr(
        module,
        "CACHE_DIR",
        tmp_path,
    )

    text = module.build_text(
        "Microsoft invierte en Medellín",
        "Proyecto de inteligencia artificial",
    )

    cache_key = module.get_cache_key(text)

    module.save_cache(
        cache_key,
        {
            "entities": [
                {
                    "text": "Microsoft",
                    "type": "ORGANIZATION",
                    "score": 0.99,
                }
            ],
            "key_phrases": [],
            "status": "processed",
        },
    )

    result = module.enrich_news(
        "Microsoft invierte en Medellín",
        "Proyecto de inteligencia artificial",
        allow_api_calls=False,
    )

    assert result["cache_hit"] is True
    assert result["status"] == "processed"
    assert len(result["entities"]) == 1
