import asyncio
import logging

from elasticsearch import AsyncElasticsearch, NotFoundError

from src.core.config import settings

logger = logging.getLogger(__name__)

_es_client: AsyncElasticsearch | None = None

INDEX_TEMPLES      = "temples"
INDEX_HOTELS       = "hotels"
INDEX_PACKAGES     = "packages"
INDEX_DESTINATIONS = "destinations"


def get_es_client() -> AsyncElasticsearch:
    if _es_client is None:
        raise RuntimeError("Elasticsearch client not initialized. Is Elasticsearch running?")
    return _es_client


async def init_elasticsearch() -> None:
    global _es_client
    _es_client = AsyncElasticsearch(hosts=[settings.ELASTICSEARCH_URL])

    for attempt in range(1, settings.ELASTICSEARCH_MAX_RETRIES + 1):
        try:
            info = await _es_client.info()
            logger.info("Connected to Elasticsearch %s", info["version"]["number"])
            await _create_indices()
            return
        except Exception as exc:
            logger.warning("Elasticsearch connection attempt %d/%d failed: %s", attempt, settings.ELASTICSEARCH_MAX_RETRIES, exc)
            if attempt < settings.ELASTICSEARCH_MAX_RETRIES:
                await asyncio.sleep(settings.ELASTICSEARCH_RETRY_DELAY)
            else:
                logger.error("Could not connect to Elasticsearch after %d attempts", settings.ELASTICSEARCH_MAX_RETRIES)
                raise


async def close_elasticsearch() -> None:
    global _es_client
    if _es_client is not None:
        await _es_client.close()
        _es_client = None
        logger.info("Elasticsearch connection closed")


_INDEX_MAPPINGS: dict[str, dict] = {
    INDEX_TEMPLES: {
        "mappings": {
            "properties": {
                "name":         {"type": "text",    "fields": {"keyword": {"type": "keyword"}}, "copy_to": "search_all"},
                "deity":        {"type": "text",    "fields": {"keyword": {"type": "keyword"}}},
                "district":     {"type": "keyword"},
                "darshan_type": {"type": "keyword"},
                "description":  {"type": "text"},
                "location":     {"type": "geo_point"},
                "suggest":      {"type": "completion"},
                "search_all":   {"type": "text"},
                "type":         {"type": "keyword"},
            }
        }
    },
    INDEX_HOTELS: {
        "mappings": {
            "properties": {
                "name":            {"type": "text",    "fields": {"keyword": {"type": "keyword"}}, "copy_to": "search_all"},
                "city":            {"type": "keyword"},
                "amenities":       {"type": "keyword"},
                "price_per_night": {"type": "float"},
                "star_rating":     {"type": "integer"},
                "description":     {"type": "text"},
                "suggest":         {"type": "completion"},
                "search_all":      {"type": "text"},
                "type":            {"type": "keyword"},
            }
        }
    },
    INDEX_PACKAGES: {
        "mappings": {
            "properties": {
                "name":          {"type": "text",  "fields": {"keyword": {"type": "keyword"}}, "copy_to": "search_all"},
                "destination":   {"type": "text",  "fields": {"keyword": {"type": "keyword"}}},
                "duration_days": {"type": "integer"},
                "budget":        {"type": "float"},
                "package_type":  {"type": "keyword"},
                "description":   {"type": "text"},
                "suggest":       {"type": "completion"},
                "search_all":    {"type": "text"},
                "type":          {"type": "keyword"},
            }
        }
    },
    INDEX_DESTINATIONS: {
        "mappings": {
            "properties": {
                "name":             {"type": "text",  "fields": {"keyword": {"type": "keyword"}}, "copy_to": "search_all"},
                "destination_type": {"type": "keyword"},
                "district":         {"type": "keyword"},
                "description":      {"type": "text"},
                "suggest":          {"type": "completion"},
                "search_all":       {"type": "text"},
                "type":             {"type": "keyword"},
            }
        }
    },
}


async def _create_indices() -> None:
    es = get_es_client()
    for index_name, mapping in _INDEX_MAPPINGS.items():
        try:
            await es.indices.get(index=index_name)
            logger.info("Index already exists: %s", index_name)
        except NotFoundError:
            await es.indices.create(index=index_name, mappings=mapping["mappings"])
            logger.info("Created index: %s", index_name)
