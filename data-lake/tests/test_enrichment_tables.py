import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "enrichment"
    / "enrichment_tables.py"
)

spec = importlib.util.spec_from_file_location(
    "enrichment_tables",
    MODULE_PATH,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_build_enrichment_tables():
    sample = [
        {
            "news_id": "news-001",
            "content_hash": "hash-v1",
            "enrichment": {
                "status": "processed",
                "entities": [
                    {
                        "text": "Microsoft",
                        "type": "ORGANIZATION",
                        "score": 0.99,
                    },
                    {
                        "text": "Medellín",
                        "type": "LOCATION",
                        "score": 0.98,
                    },
                ],
                "key_phrases": [
                    {
                        "text": "inteligencia artificial",
                        "score": 0.97,
                    }
                ],
            },
        },
        {
            "news_id": "news-002",
            "content_hash": "hash-v2",
            "enrichment": {
                "status": "not_processed",
                "entities": [],
                "key_phrases": [],
            },
        },
    ]

    entities, phrases = module.build_enrichment_tables(sample)

    assert len(entities) == 2
    assert len(phrases) == 1

    assert entities["news_id"].nunique() == 1
    assert entities.iloc[0]["entity_type"] == "ORGANIZATION"
    assert phrases.iloc[0]["phrase_text"] == "inteligencia artificial"
    assert "news-002" not in entities["news_id"].values
