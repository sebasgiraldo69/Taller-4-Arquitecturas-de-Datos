import importlib.util
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "processing"
    / "news_change_detector.py"
)

spec = importlib.util.spec_from_file_location(
    "news_change_detector", MODULE_PATH
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

detect_changes = module.detect_changes


def test_new_updated_unchanged():
    snapshots = [
        {
            "run_id": "run-001",
            "section": "tecnologia",
            "ingested_at": "2026-10-22T10:00:00+00:00",
            "news": [
                {
                    "news_id": "noticia-001",
                    "title": "Título original",
                    "section": "tecnologia",
                    "content_hash": "hash-original",
                }
            ],
        },
        {
            "run_id": "run-002",
            "section": "tecnologia",
            "ingested_at": "2026-10-22T11:00:00+00:00",
            "news": [
                {
                    "news_id": "noticia-001",
                    "title": "Título original",
                    "section": "tecnologia",
                    "content_hash": "hash-original",
                }
            ],
        },
        {
            "run_id": "run-003",
            "section": "tecnologia",
            "ingested_at": "2026-10-22T12:00:00+00:00",
            "news": [
                {
                    "news_id": "noticia-001",
                    "title": "Título actualizado",
                    "section": "tecnologia",
                    "content_hash": "hash-modificado",
                }
            ],
        },
    ]

    changes = detect_changes(snapshots)

    statuses = [change["status"] for change in changes]

    assert statuses == [
        "new",
        "unchanged",
        "updated",
    ]
