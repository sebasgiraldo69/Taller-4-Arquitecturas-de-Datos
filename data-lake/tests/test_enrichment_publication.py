import importlib.util
import sys
from pathlib import Path

ENRICHMENT_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "enrichment"
)

sys.path.insert(0, str(ENRICHMENT_DIR))

spec = importlib.util.spec_from_file_location(
    "enrichment_processor",
    ENRICHMENT_DIR / "enrichment_processor.py",
)

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_partial_run_cannot_publish():
    assert not module.can_publish(30, 1, 0)


def test_pending_news_cannot_publish():
    assert not module.can_publish(30, 30, 1)


def test_complete_run_can_publish():
    assert module.can_publish(30, 30, 0)


def test_empty_run_cannot_publish():
    assert not module.can_publish(0, 0, 0)
