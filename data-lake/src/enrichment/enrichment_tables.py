import pandas as pd

ENTITY_COLUMNS = [
    "news_id",
    "content_hash",
    "entity_text",
    "entity_type",
    "score",
]

PHRASE_COLUMNS = [
    "news_id",
    "content_hash",
    "phrase_text",
    "score",
]


def build_enrichment_tables(enriched_news):
    """
    Convierte resultados procesados de Comprehend
    en dos DataFrames listos para Parquet.
    """
    entity_rows = []
    phrase_rows = []

    for news in enriched_news:
        result = news["enrichment"]

        if result.get("status") != "processed":
            continue

        for entity in result.get("entities", []):
            entity_rows.append({
                "news_id": news["news_id"],
                "content_hash": news["content_hash"],
                "entity_text": entity["text"],
                "entity_type": entity["type"],
                "score": float(entity["score"]),
            })

        for phrase in result.get("key_phrases", []):
            phrase_rows.append({
                "news_id": news["news_id"],
                "content_hash": news["content_hash"],
                "phrase_text": phrase["text"],
                "score": float(phrase["score"]),
            })

    entities_df = pd.DataFrame(
        entity_rows,
        columns=ENTITY_COLUMNS,
    )

    phrases_df = pd.DataFrame(
        phrase_rows,
        columns=PHRASE_COLUMNS,
    )

    return entities_df, phrases_df
