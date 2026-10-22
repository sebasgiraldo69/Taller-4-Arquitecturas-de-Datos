import hashlib
import json
import os
from pathlib import Path
from s3_cache import load_s3_cache, save_s3_cache
import os
from pathlib import Path    
import boto3
from botocore.exceptions import ClientError

REGION = "us-east-1"
LANGUAGE_CODE = "es"

CACHE_DIR = Path(
    os.environ.get(
        "COMPREHEND_CACHE_DIR",
        str(Path(__file__).resolve().parents[2] / "cache" / "comprehend"),
    )
)


def build_text(title, description):
    """Construye el texto que analizará Comprehend."""
    title = (title or "").strip()
    description = (description or "").strip()

    text = f"{title}. {description}".strip()

    # Comprehend DetectEntities y DetectKeyPhrases
    # aceptan hasta 100 KB por solicitud.
    encoded = text.encode("utf-8")

    if len(encoded) > 100_000:
        raise ValueError("Texto supera el límite de 100 KB")

    return text


def get_cache_key(text, language=LANGUAGE_CODE):
    """Identificador determinista del texto analizado."""
    payload = f"{language}|{text}"

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def get_cache_path(cache_key):
    return CACHE_DIR / f"{cache_key}.json"


def load_cache(cache_key):
    path = get_cache_path(cache_key)

    if not path.exists():
        return None

    with open(path, encoding="utf-8") as file:
        return json.load(file)


def save_cache(cache_key, result):
    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = get_cache_path(cache_key)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2,
        )


def normalize_entities(response):
    """Conserva personas, organizaciones y lugares."""
    allowed_types = {
        "PERSON",
        "ORGANIZATION",
        "LOCATION",
    }

    return [
        {
            "text": item["Text"],
            "type": item["Type"],
            "score": float(item["Score"]),
        }
        for item in response.get("Entities", [])
        if item["Type"] in allowed_types
    ]


def normalize_key_phrases(response):
    return [
        {
            "text": item["Text"],
            "score": float(item["Score"]),
        }
        for item in response.get("KeyPhrases", [])
    ]



def enrich_news(
    title,
    description,
    client=None,
    allow_api_calls=False,
    use_s3_cache=False,
    s3_client=None,
):
    """Enriquece noticias con caché local y opcionalmente S3."""
    text = build_text(title, description)

    if not text.strip():
        raise ValueError("No hay texto para analizar")

    cache_key = get_cache_key(text)

    # 1. Consultar caché local
    cached = load_cache(cache_key)

    if cached is not None:
        if use_s3_cache:
            remote = load_s3_cache(
                cache_key,
                s3_client=s3_client,
            )

            if remote is None:
                save_s3_cache(
                    cache_key,
                    cached,
                    s3_client=s3_client,
                )

        return {**cached, "cache_hit": True}

    # 2. Consultar caché persistente en S3
    if use_s3_cache:
        cached = load_s3_cache(
            cache_key,
            s3_client=s3_client,
        )

        if cached is not None:
            save_cache(cache_key, cached)
            return {**cached, "cache_hit": True}

    # 3. Modo seguro: no llamar a Comprehend
    if not allow_api_calls:
        return {
            "entities": [],
            "key_phrases": [],
            "cache_hit": False,
            "status": "not_processed",
        }

    # 4. Llamar a Comprehend únicamente si está autorizado
    if client is None:
        client = boto3.client(
            "comprehend",
            region_name=REGION,
        )

    entities_response = client.detect_entities(
        Text=text,
        LanguageCode=LANGUAGE_CODE,
    )

    phrases_response = client.detect_key_phrases(
        Text=text,
        LanguageCode=LANGUAGE_CODE,
    )

    result = {
        "entities": normalize_entities(entities_response),
        "key_phrases": normalize_key_phrases(phrases_response),
        "status": "processed",
    }

    # 5. Persistir primero en S3 cuando esté habilitado
    if use_s3_cache:
        save_s3_cache(
            cache_key,
            result,
            s3_client=s3_client,
        )

    # 6. Guardar también en caché local
    save_cache(cache_key, result)

    return {**result, "cache_hit": False}
