import asyncio
import logging

from elasticsearch import AsyncElasticsearch, NotFoundError
from src.core.config import settings

logger = logging.getLogger(__name__)

# Global Elasticsearch client
_es_client: AsyncElasticsearch | None = None


# Index Names
INDEX_TEMPLES = "temples"
INDEX_HOTELS = "hotels"
INDEX_PACKAGES = "packages"
INDEX_DESTINATIONS = "destinations"


# ───────────────── Client Getter ─────────────────

def get_es_client() -> AsyncElasticsearch:
    """Return initialized Elasticsearch client."""
    if _es_client is None:
        raise RuntimeError("Elasticsearch client not initialized.")
    return _es_client


# ───────────────── Initialize Elasticsearch ─────────────────

async def init_elasticsearch() -> None:
    """Initialize Elasticsearch connection with retry."""
    global _es_client

    _es_client = AsyncElasticsearch(
        hosts=[settings.ELASTICSEARCH_URL],
        basic_auth=(
            settings.ELASTICSEARCH_USERNAME,
            settings.ELASTICSEARCH_PASSWORD
        ),
        verify_certs=False
    )

    for attempt in range(1, settings.ELASTICSEARCH_MAX_RETRIES + 1):
        try:
            info = await _es_client.info()

            logger.info(
                "Connected to Elasticsearch %s",
                info["version"]["number"]
            )

            await _create_indices()

            return

        except Exception as exc:

            logger.warning(
                "Elasticsearch connection attempt %d/%d failed: %s",
                attempt,
                settings.ELASTICSEARCH_MAX_RETRIES,
                exc,
            )

            if attempt < settings.ELASTICSEARCH_MAX_RETRIES:
                await asyncio.sleep(settings.ELASTICSEARCH_RETRY_DELAY)
            else:
                logger.error(
                    "Could not connect to Elasticsearch after %d attempts",
                    settings.ELASTICSEARCH_MAX_RETRIES,
                )
                raise


# ───────────────── Close Connection ─────────────────

async def close_elasticsearch() -> None:
    """Close Elasticsearch connection."""
    global _es_client

    if _es_client is not None:
        await _es_client.close()
        _es_client = None
        logger.info("Elasticsearch connection closed")


# ───────────────── Index Mappings ─────────────────

_INDEX_MAPPINGS: dict[str, dict] = {

    INDEX_TEMPLES: {
        "mappings": {
            "properties": {
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}, "copy_to": "search_all"},
                "deity": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "district": {"type": "keyword"},
                "darshan_type": {"type": "keyword"},
                "description": {"type": "text"},
                "location": {"type": "geo_point"},
                "suggest": {"type": "completion"},
                "search_all": {"type": "text"},
                "type": {"type": "keyword"},
            }
        }
    },

    INDEX_HOTELS: {
        "mappings": {
            "properties": {
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}, "copy_to": "search_all"},
                "city": {"type": "keyword"},
                "amenities": {"type": "keyword"},
                "price_per_night": {"type": "float"},
                "star_rating": {"type": "integer"},
                "description": {"type": "text"},
                "suggest": {"type": "completion"},
                "search_all": {"type": "text"},
                "type": {"type": "keyword"},
            }
        }
    },

    INDEX_PACKAGES: {
        "mappings": {
            "properties": {
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}, "copy_to": "search_all"},
                "destination": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "duration_days": {"type": "integer"},
                "budget": {"type": "float"},
                "package_type": {"type": "keyword"},
                "description": {"type": "text"},
                "suggest": {"type": "completion"},
                "search_all": {"type": "text"},
                "type": {"type": "keyword"},
            }
        }
    },

    INDEX_DESTINATIONS: {
        "mappings": {
            "properties": {
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}, "copy_to": "search_all"},
                "destination_type": {"type": "keyword"},
                "district": {"type": "keyword"},
                "description": {"type": "text"},
                "suggest": {"type": "completion"},
                "search_all": {"type": "text"},
                "type": {"type": "keyword"},
            }
        }
    },
}


# ───────────────── Create Indices ─────────────────

async def _create_indices() -> None:
    """Create Elasticsearch indices if they do not exist."""

    es = get_es_client()

    for index_name, mapping in _INDEX_MAPPINGS.items():

        try:
            exists = await es.indices.exists(index=index_name)

            if not exists:
                await es.indices.create(
                    index=index_name,
                    mappings=mapping["mappings"]
                )

                logger.info("Created index: %s", index_name)

            else:
                logger.info("Index already exists: %s", index_name)

        except Exception as exc:
            logger.error("Failed creating index %s: %s", index_name, exc)