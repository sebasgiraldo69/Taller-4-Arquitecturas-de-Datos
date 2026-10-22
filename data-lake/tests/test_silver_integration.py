import importlib.util
from pathlib import Path

import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "processing"
    / "news_change_detector.py"
)

spec = importlib.util.spec_from_file_location(
    "news_change_detector",
    MODULE_PATH,
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_silver_change_history():
    snapshots = [
        {
            "run_id": "run-001",
            "section": "tecnologia",
            "ingested_at": "2026-10-22T10:00:00+00:00",
            "news": [
                {
                    "news_id": "news-001",
                    "url": "https://example.com/news-001",
                    "title": "Noticia original",
                    "section": "tecnologia",
                    "content_hash": "hash-v1",
                }
            ],
        },
        {
            "run_id": "run-002",
            "section": "tecnologia",
            "ingested_at": "2026-10-22T11:00:00+00:00",
            "news": [
                {
                    "news_id": "news-001",
                    "url": "https://example.com/news-001",
                    "title": "Noticia original",
                    "section": "tecnologia",
                    "content_hash": "hash-v1",
                }
            ],
        },
        {
            "run_id": "run-003",
            "section": "tecnologia",
            "ingested_at": "2026-10-22T12:00:00+00:00",
            "news": [
                {
                    "news_id": "news-001",
                    "url": "https://example.com/news-001",
                    "title": "Noticia actualizada",
                    "section": "tecnologia",
                    "content_hash": "hash-v2",
                }
            ],
        },
    ]

    changes = module.detect_changes(snapshots)
    df = pd.DataFrame(changes)

    assert len(df) == 3
    assert df["status"].tolist() == [
        "new",
        "unchanged",
        "updated",
    ]

    assert df["news_id"].nunique() == 1
    assert df.iloc[-1]["content_hash"] == "hash-v2"
    assert df.iloc[-1]["run_id"] == "run-003"
